import json
import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from app.models.event import Event
from app.models.url import Url
from app.models.user import User

logger = logging.getLogger(__name__)
events_bp = Blueprint("events", __name__)


def _event_to_dict(e):
    return {
        "id": e.id,
        "url_id": e.url_id,
        "user_id": e.user_id,
        "event_type": e.event_type,
        "timestamp": e.timestamp.isoformat() if e.timestamp else None,
        "details": e.details,
    }


@events_bp.route("/events", methods=["GET"])
def list_events():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    url_id = request.args.get("url_id", type=int)
    user_id = request.args.get("user_id", type=int)
    event_type = request.args.get("event_type")

    if page < 1 or per_page < 1:
        return jsonify({"error": "page and per_page must be positive"}), 400

    query = Event.select().order_by(Event.timestamp.desc())

    if url_id is not None:
        query = query.where(Event.url == url_id)
    if user_id is not None:
        query = query.where(Event.user == user_id)
    if event_type:
        query = query.where(Event.event_type == event_type)

    events = list(query.paginate(page, per_page))
    return jsonify([_event_to_dict(e) for e in events])


@events_bp.route("/events", methods=["POST"])
def create_event():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    url_id = data.get("url_id")
    event_type = data.get("event_type", "").strip()

    if not url_id:
        return jsonify({"error": "url_id is required"}), 400
    if not event_type:
        return jsonify({"error": "event_type is required"}), 400

    try:
        url = Url.get_by_id(int(url_id))
    except (Url.DoesNotExist, ValueError):
        return jsonify({"error": "url not found"}), 404

    user_id = data.get("user_id")
    user = None
    if user_id:
        try:
            user = User.get_by_id(int(user_id))
        except (User.DoesNotExist, ValueError):
            pass

    details = data.get("details")
    if isinstance(details, dict):
        details = json.dumps(details)

    event = Event.create(
        url=url,
        user=user,
        event_type=event_type,
        timestamp=datetime.now(),
        details=details,
    )

    logger.info("Event created", extra={"event_id": event.id, "event_type": event_type})
    return jsonify(_event_to_dict(event)), 201
