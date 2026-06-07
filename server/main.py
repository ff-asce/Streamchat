# main.py
# The main FastAPI application.
# Run with: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from telemetry import setup_telemetry
from llm_client import stream_llm_response, CircuitOpenError

# Create the FastAPI application instance
app = FastAPI(title="StreamChat")

# Set up metrics when the module loads.
# These three objects are used throughout the request handler to record data.
request_counter, latency_histogram, circuit_open_counter = setup_telemetry()

@app.get("/health")
async def health_check():
    """
    A simple health check endpoint.
    Visit http://localhost:8000/health in your browser to confirm the server is running.
    """
    return {"status": "ok"}

@app.websocket("/chat")
async def chat_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint at ws://localhost:8000/chat

    Each client that connects gets their own instance of this function running.
    FastAPI handles multiple clients concurrently because this is async.
    """

    # Accept the WebSocket connection (complete the handshake)
    await websocket.accept()
    print("🔌 Client connected")

    try:
        # Keep this connection alive, handling multiple messages in a loop.
        # The loop exits when the client disconnects (WebSocketDisconnect).
        while True:

            # Wait for the client to send a message.
            # This pauses here (await) until a message arrives.
            # While waiting, the server can handle other clients.
            user_message = await websocket.receive_text()
            print(f"📨 Received: {user_message[:80]}")  # log first 80 chars

            # Record that a request happened
            request_counter.add(1)

            # Record when this request started (for latency calculation)
            start_time = time.time()

            try:
                # stream_llm_response is an async generator.
                # "async for token in ..." calls it and gets one token per iteration.
                async for token in stream_llm_response(user_message):
                    # Send each token to the client immediately as it arrives.
                    await websocket.send_text(token)

                # Send a special end-of-response marker.
                # The client uses this to know the full response has been sent.
                await websocket.send_text("[DONE]")

                # Record how long this request took
                latency = time.time() - start_time
                latency_histogram.record(latency)
                print(f"✅ Response complete in {latency:.2f}s")

            except CircuitOpenError as e:
                # Circuit is open — tell the client immediately
                circuit_open_counter.add(1)
                await websocket.send_text(f"[ERROR] {str(e)}")
                await websocket.send_text("[DONE]")
                print(f"⚡ Circuit open — rejected request")

            except Exception as e:
                # Something else went wrong (vLLM down, network error, etc.)
                await websocket.send_text(f"[ERROR] Request failed: {str(e)}")
                await websocket.send_text("[DONE]")
                print(f"❌ Error: {e}")

    except WebSocketDisconnect:
        # This exception is raised when the client closes the connection.
        # This is normal — just log it and exit the function.
        print("🔌 Client disconnected")