import logging
from flask import Blueprint, jsonify
from app.database import database_proxy

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

    status = "ok" if db_status == "ok" else "degraded"
    code = 200 if status == "ok" else 503

    logger.info("Health check", extra={"status": status, "db": db_status})
    return jsonify({"status": status, "db": db_status}), code
