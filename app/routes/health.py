import logging
from flask import Blueprint, jsonify
from app.database import database_proxy
from app.cache import get_cache

logger = logging.getLogger(__name__)
health_bp = Blueprint("health", __name__)


@health_bp.route("/health")
def health():
    try:
        database_proxy.execute_sql("SELECT 1")
        db_status = "ok"
    except Exception as e:
        logger.error("DB health check failed", extra={"error": str(e)})
        db_status = "error"

    try:
        cache = get_cache()
        cache_status = "ok" if cache is not None else "unavailable"
    except Exception as e:
        logger.error("Cache health check failed", extra={"error": str(e)})
        cache_status = "error"

    status = "ok" if db_status == "ok" else "degraded"
    code = 200 if status == "ok" else 503

    logger.info("Health check", extra={"status": status, "db": db_status, "cache": cache_status})
    return jsonify({"status": status, "db": db_status, "cache": cache_status}), code
