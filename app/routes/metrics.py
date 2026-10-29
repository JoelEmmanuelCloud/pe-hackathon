import os
import time
import psutil
from flask import Blueprint, Response, g, request
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
CACHE_LOOKUPS = Counter(
    "cache_lookups_total",
    "Cache lookups by cache name and result",
    ["cache", "result"],
)


@metrics_bp.before_app_request
def start_timer():
    g.request_start = time.perf_counter()


@metrics_bp.after_app_request
def record_request(response):
    start = g.pop("request_start", None)
    if start is None:
        return response
    endpoint = request.url_rule.rule if request.url_rule else "unmatched"
    REQUEST_LATENCY.labels(request.method, endpoint).observe(time.perf_counter() - start)
    REQUEST_COUNT.labels(request.method, endpoint, str(response.status_code)).inc()
    return response


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
