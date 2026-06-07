# llm_client.py
# This file handles all communication with the vLLM server.
# It streams tokens back one by one and uses a circuit breaker for resilience.

import json
import time
import httpx

VLLM_URL = "http://localhost:8001/v1/chat/completions"
MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"

# ── Circuit Breaker State ─────────────────────────────────────────────────────
# This dictionary holds the current state of the circuit breaker.
# It lives in memory — if you restart the server, it resets to default (closed).

_circuit = {
    "failures": 0,           # consecutive failure count
    "open_until": 0.0,       # epoch timestamp; circuit is open while time.time() < this
    "failure_threshold": 3,  # open the circuit after this many failures
    "cooldown_seconds": 30,  # keep the circuit open for this long
}


class CircuitOpenError(Exception):
    """
    Raised when the circuit breaker is open.
    This is a custom exception so callers can handle it specifically.
    """
    pass

def _is_circuit_open() -> bool:
    """
    returne true if the circuit is currently open, i.e. rejecting requests
    """
    return time.time() < _circuit["open_until"]

def _record_failure():
    """
    called when llm request fails
    increments the failure counter and opnes the circuit if the threshold is reached
    """
    _circuit["failures"] += 1
    print(f"⚠️  LLM failure #{_circuit['failures']}")

    if _circuit["failures"] >= _circuit["failure_threshold"]:
        _circuit["open_until"] = time.time() + _circuit["cooldown_seconds"]
        print(f"⚡ Circuit OPENED. Will retry after {_circuit['cooldown_seconds']}s.")

def _record_success():
    """
    called when LLM request succeeds, resets the failure counter
    """
    if _circuit["failures"] > 0:
        print("C✅ Circuit reset — LLM is responding normally.")
    _circuit["failures"] = 0
    _circuit["open_until"] = 0.0


# ── Streaming LLM Call ────────────────────────────────────────────────────────

async def stream_llm_response(user_message: str):
    """
    Async generator that streams tokens from vLLM one at a time.

    Usage:
        async for token in stream_llm_response("Hello"):
            print(token, end="")

    Raises:
        CircuitOpenError: if the circuit breaker is open
        httpx.HTTPError: if vLLM fails and retries are exhausted
    """

    # Check circuit breaker before doing anything
    if _is_circuit_open():
        remaining = int(_circuit["open_until"] - time.time())
        raise CircuitOpenError(
            f"LLM service is temporarily unavailable. Retrying in {remaining}s."
        )
    
    # Build the request payload.
    # This is the same format as the OpenAI API — vLLM is compatible with it.
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": user_message}
        ],
        "max_tokens": 200,
        "stream": True,        # <- this tells vLLM to send tokens as they are generated
    }

    try:
        # httpx.AsyncClient is an async HTTP client.
        # We use it as a context manager (with statement) so it cleans up after itself.
        # client.stream() opens a long-lived HTTP connection and reads the response
        # line by line as it arrives, instead of waiting for the full response.
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", VLLM_URL, json=payload) as response:

                # Raise an exception if the HTTP status is an error (4xx, 5xx)
                response.raise_for_status()

                # Read the response line by line.
                # vLLM sends Server-Sent Events (SSE), which look like:
                #   data: {"choices": [{"delta": {"content": "Hello"}}]}
                #   data: {"choices": [{"delta": {"content": " world"}}]}
                #   data: [DONE]
                async for line in response.aiter_lines():

                    # Skip empty lines (SSE uses blank lines as separators)
                    if not line:
                        continue

                    # The last message is a special [DONE] marker — stop here
                    if line == "data: [DONE]":
                        break

                    # Each line starts with "data: " — strip that prefix
                    if not line.startswith("data: "):
                        continue

                    raw_json = line[len("data: "):]   # remove the "data: " prefix

                    try:
                        chunk = json.loads(raw_json)
                    except json.JSONDecodeError:
                        continue   # skip malformed lines

                    # Extract the token text from the nested JSON structure
                    token = chunk["choices"][0]["delta"].get("content", "")

                    if token:
                        yield token   # send this token to the caller

        # If we get here without an exception, the request succeeded
        _record_success()

    except CircuitOpenError:
        # Don't count circuit-open as a failure — just re-raise
        raise

    except Exception as e:
        # Any other exception counts as a failure
        _record_failure()
        raise   # re-raise so the caller knows something went wrong

