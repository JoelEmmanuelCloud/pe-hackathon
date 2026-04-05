import os
import psutil
from flask import Blueprint, Response
from prometheus_client import (
    Counter, Histogram, Gauge,
    generate_latest, CONTENT_TYPE_LATEST,
)
from prometheus_client import REGISTRY

metrics_bp = Blueprint("metrics", __name__)

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
)

ACTIVE_URLS = Gauge("active_urls_total", "Total active short URLs")
TOTAL_REDIRECTS = Counter("url_redirects_total", "Total URL redirects")
CPU_USAGE = Gauge("process_cpu_percent", "Process CPU usage percent")
MEMORY_USAGE = Gauge("process_memory_bytes", "Process memory usage in bytes")


@metrics_bp.route("/metrics")
def metrics():
    proc = psutil.Process(os.getpid())
    CPU_USAGE.set(proc.cpu_percent(interval=0.1))
    MEMORY_USAGE.set(proc.memory_info().rss)

    try:
        from app.models.url import Url
        ACTIVE_URLS.set(Url.select().where(Url.is_active == True).count())
    except Exception:
        pass

    return Response(generate_latest(REGISTRY), mimetype=CONTENT_TYPE_LATEST)
