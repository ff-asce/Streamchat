from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from prometheus_client import start_http_server

def setup_telemetry():
    """
    call this once when the server starts, returns three metrics objects you can use to records data.
    """

    start_http_server(port=9090, addr="0.0.0.0")

    reader = PrometheusMetricReader()
    provider = MeterProvider(metric_readers=[reader])
    metrics.set_meter_provider(provider)

    meter = metrics.get_meter("streamchat")

    request_counter = meter.create_counter(
        name="llm_requests_total",
        description="Total number of LLM requests recieved"
    )

    latency_histogram = meter.create_histogram(
        name="llm_request_latency_seconds",
        description="Time from recieving request to sending first token"
    )

    circuit_open_counter = meter.create_counter(
        name="circuit_breaker_open_total",
        description="Number of times the circuit breaker has been opened"
    )

    print("✅ Telemetry started. Metrics available at http://localhost:9090/metrics")

    return request_counter, latency_histogram, circuit_open_counter