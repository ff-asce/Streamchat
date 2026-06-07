# StreamChat

A production-ready WebSocket-based chat server with streaming LLM responses, built-in observability, and circuit breaker resilience.

## 🚀 Features

- **Real-time Streaming**: WebSocket-based chat with token-by-token streaming from LLM
- **Circuit Breaker**: Automatic failure detection and recovery for LLM service
- **Observability**: Built-in Prometheus metrics and Grafana dashboards
- **Production-Ready**: Async architecture with proper error handling and telemetry
- **OpenAI-Compatible**: Works with vLLM and other OpenAI-compatible endpoints

## 📋 Architecture

```
┌─────────────┐     WebSocket      ┌──────────────┐     HTTP/SSE     ┌─────────────┐
│   Client    │ ←─────────────────→ │   FastAPI    │ ←───────────────→ │    vLLM     │
│ (test_client)│                    │    Server    │                  │   Server    │
└─────────────┘                    └──────────────┘                  └─────────────┘
                                           │
                                           │ Metrics (port 9090)
                                           ↓
                                    ┌──────────────┐
                                    │  Prometheus  │
                                    │  (port 9091) │
                                    └──────────────┘
                                           │
                                           ↓
                                    ┌──────────────┐
                                    │   Grafana    │
                                    │  (port 3000) │
                                    └──────────────┘
```

## 🛠️ Tech Stack

- **FastAPI**: Modern async web framework
- **WebSockets**: Real-time bidirectional communication
- **httpx**: Async HTTP client for LLM streaming
- **OpenTelemetry**: Industry-standard observability
- **Prometheus**: Metrics collection and storage
- **Grafana**: Metrics visualization
- **Docker Compose**: Easy deployment of monitoring stack

## 📦 Installation

### Prerequisites

- Python 3.8+
- Docker & Docker Compose (for monitoring)
- vLLM server running on `localhost:8001` (or modify `VLLM_URL` in `llm_client.py`)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/ff-asce/Streamchat.git
   cd Streamchat
   ```

2. **Install Python dependencies**
   ```bash
   cd server
   pip install -r requirements.txt
   ```

3. **Start monitoring stack** (optional but recommended)
   ```bash
   cd ..
   docker-compose up -d
   ```

## 🚀 Quick Start

### 1. Start the FastAPI Server

```bash
cd server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The server will start on `http://localhost:8000` with:
- WebSocket endpoint: `ws://localhost:8000/chat`
- Health check: `http://localhost:8000/health`
- Metrics: `http://localhost:9090/metrics`

### 2. Run the Test Client

In a new terminal:

```bash
python test_client.py
```

Type your messages and see streaming responses in real-time!

### 3. Access Monitoring (if using Docker Compose)

- **Prometheus**: http://localhost:9091
- **Grafana**: http://localhost:3000 (login: admin/admin)

## 📊 Metrics

The server exposes three key metrics:

| Metric | Type | Description |
|--------|------|-------------|
| `llm_requests_total` | Counter | Total number of LLM requests received |
| `llm_request_latency_seconds` | Histogram | Time from receiving request to sending first token |
| `circuit_breaker_open_total` | Counter | Number of times circuit breaker opened |

## 🔧 Configuration

### Circuit Breaker Settings

Edit `server/llm_client.py`:

```python
_circuit = {
    "failure_threshold": 3,   # Open circuit after N failures
    "cooldown_seconds": 30,   # Keep circuit open for N seconds
}
```

### LLM Endpoint

Edit `server/llm_client.py`:

```python
VLLM_URL = "http://localhost:8001/v1/chat/completions"
MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
```

### Prometheus Scraping

Edit `prometheus.yml` to match your server's IP:

```yaml
scrape_configs:
  - job_name: "streamchat"
    static_configs:
      - targets: ["192.168.1.2:9090"]  # Change to your IP
```

## 📁 Project Structure

```
streamchat/
├── server/
│   ├── main.py           # FastAPI app and WebSocket endpoint
│   ├── llm_client.py     # LLM streaming client with circuit breaker
│   ├── telemetry.py      # OpenTelemetry metrics setup
│   └── requirements.txt  # Python dependencies
├── test_client.py        # Command-line chat client
├── docker-compose.yml    # Prometheus + Grafana stack
├── prometheus.yml        # Prometheus configuration
└── README.md            # This file
```

## 🔄 How It Works

### WebSocket Flow

1. Client connects to `ws://localhost:8000/chat`
2. Client sends a message
3. Server checks circuit breaker status
4. Server streams request to vLLM
5. Server forwards tokens to client as they arrive
6. Server sends `[DONE]` marker when complete
7. Connection stays open for next message

### Circuit Breaker

- Tracks consecutive failures to LLM service
- Opens after 3 failures (configurable)
- Rejects requests for 30 seconds (configurable)
- Automatically closes after cooldown
- Resets counter on successful request

### Streaming

- Uses Server-Sent Events (SSE) from vLLM
- Parses JSON chunks line-by-line
- Extracts tokens from nested structure
- Yields tokens immediately (no buffering)

## 🐛 Troubleshooting

### "Connection refused" error

- Ensure vLLM server is running on port 8001
- Check `VLLM_URL` in `llm_client.py`

### Circuit breaker keeps opening

- Check vLLM server logs for errors
- Verify model is loaded correctly
- Increase `failure_threshold` if needed

### Prometheus can't scrape metrics

- Verify server IP in `prometheus.yml`
- Check firewall allows port 9090
- Use `host.docker.internal` on Mac/Windows

### WebSocket disconnects

- Check `max_size` in `test_client.py`
- Increase `ping_interval` and `ping_timeout`
- Check server logs for errors

## 🧪 Testing

### Manual Testing

```bash
# Terminal 1: Start server
cd server
uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2: Run client
python test_client.py
```

### Health Check

```bash
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

### Metrics Check

```bash
curl http://localhost:9090/metrics
# Should see llm_requests_total, llm_request_latency_seconds, etc.
```

## 📈 Grafana Dashboard

1. Open http://localhost:3000
2. Login with admin/admin
3. Add Prometheus data source:
   - URL: `http://prometheus:9090`
4. Create dashboard with queries:
   - Request rate: `rate(llm_requests_total[1m])`
   - Latency p95: `histogram_quantile(0.95, llm_request_latency_seconds)`
   - Circuit opens: `circuit_breaker_open_total`

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Observability via [OpenTelemetry](https://opentelemetry.io/)
- Monitoring with [Prometheus](https://prometheus.io/) & [Grafana](https://grafana.com/)
- LLM serving via [vLLM](https://github.com/vllm-project/vllm)

## 📧 Contact

For questions or issues, please open a GitHub issue.

---

**Happy Streaming! 🚀**