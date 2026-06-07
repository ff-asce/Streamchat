# test_client.py
# A simple command-line chat client that connects to your WebSocket server.
# Run with: python test_client.py

import asyncio
import websockets   # pip install websockets

SERVER_URL = "ws://localhost:8000/chat"

async def chat():
    print(f"Connecting to {SERVER_URL}...")

    # websockets.connect opens a WebSocket connection to your server.
    # async with means it will automatically close the connection when done.
    async with websockets.connect(SERVER_URL, max_size=10_000_000, ping_interval=20, ping_timeout=60) as ws:
        print("Connected! Type a message and press Enter. Type 'quit' to exit.\n")

        while True:
            # Get input from the user
            user_input = input("You: ").strip()

            if user_input.lower() == "quit":
                print("Goodbye!")
                break

            if not user_input:
                continue

            # Send the message to the server
            await ws.send(user_input)

            # Receive tokens one by one until we get [DONE]
            print("Bot: ", end="", flush=True)
            while True:
                message = await ws.recv()

                if message == "[DONE]":
                    print()   # newline after the response
                    break
                elif message.startswith("[ERROR]"):
                    print(message)
                    break
                else:
                    # Print the token without a newline, immediately (flush=True)
                    print(message, end="", flush=True)

# asyncio.run() is the standard way to run an async function from normal (sync) code
asyncio.run(chat())