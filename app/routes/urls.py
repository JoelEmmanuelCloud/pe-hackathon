import json
import logging
import secrets
import string
from datetime import datetime

from flask import Blueprint, jsonify, redirect, request

from app.models.event import Event
from app.models.url import Url
from app.models.user import User
from app.routes.metrics import TOTAL_REDIRECTS

logger = logging.getLogger(__name__)
urls_bp = Blueprint("urls", __name__)

ALPHABET = string.ascii_letters + string.digits


def _generate_short_code(length=6):
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def _url_to_dict(url):
    return {
        "id": url.id,
        "short_code": url.short_code,
        "original_url": url.original_url,
        "title": url.title,
        "is_active": url.is_active,
        "user_id": url.user_id,
        "created_at": url.created_at.isoformat() if url.created_at else None,
        "updated_at": url.updated_at.isoformat() if url.updated_at else None,
    }


@urls_bp.route("/shorten", methods=["POST"])
def shorten():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    original_url = data.get("original_url", "").strip()
    if not original_url:
        return jsonify({"error": "original_url is required"}), 400
    if not original_url.startswith(("http://", "https://")):
        return jsonify({"error": "original_url must start with http:// or https://"}), 400

    user_id = data.get("user_id")
    if user_id is not None:
        try:
            user = User.get_by_id(int(user_id))
        except (User.DoesNotExist, ValueError):
            return jsonify({"error": "user not found"}), 404
    else:
        user = None

    for _ in range(10):
        short_code = _generate_short_code()
        if not Url.select().where(Url.short_code == short_code).exists():
            break
    else:
        return jsonify({"error": "Could not generate unique short code"}), 500

    url = Url.create(
        user=user,
        short_code=short_code,
        original_url=original_url,
        title=data.get("title", ""),
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    Event.create(
        url=url,
        user=user,
        event_type="created",
        timestamp=datetime.now(),
        details=json.dumps({"short_code": short_code, "original_url": original_url}),
    )

    logger.info("URL shortened", extra={"short_code": short_code, "original_url": original_url})
    return jsonify(_url_to_dict(url)), 201


@urls_bp.route("/<short_code>")
def redirect_url(short_code):
    if not short_code or len(short_code) > 20:
        return jsonify({"error": "Invalid short code"}), 400

    try:
        url = Url.get(Url.short_code == short_code)
    except Url.DoesNotExist:
        logger.warning("Short code not found", extra={"short_code": short_code})
        return jsonify({"error": "URL not found"}), 404

    if not url.is_active:
        return jsonify({"error": "URL is no longer active"}), 410

    Event.create(
        url=url,
        user=None,
        event_type="clicked",
        timestamp=datetime.now(),
        details=json.dumps({"short_code": short_code}),
    )

    TOTAL_REDIRECTS.inc()
    logger.info("URL redirected", extra={"short_code": short_code, "destination": url.original_url})
    return redirect(url.original_url, code=302)


@urls_bp.route("/urls", methods=["POST"])
def create_url():
    return shorten()


@urls_bp.route("/urls/<int:url_id>", methods=["PUT"])
def update_url(url_id):
    try:
        url = Url.get_by_id(url_id)
    except Url.DoesNotExist:
        return jsonify({"error": "URL not found"}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    if "title" in data:
        url.title = data["title"]
    if "is_active" in data:
        url.is_active = bool(data["is_active"])
    if "original_url" in data:
        url.original_url = data["original_url"]

    url.updated_at = datetime.now()
    url.save()

    logger.info("URL updated", extra={"url_id": url_id})
    return jsonify(_url_to_dict(url))


@urls_bp.route("/urls")
def list_urls():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    user_id = request.args.get("user_id", type=int)
    is_active = request.args.get("is_active")

    if page < 1 or per_page < 1:
        return jsonify({"error": "page and per_page must be positive integers"}), 400

    query = Url.select().order_by(Url.created_at.desc())

    if user_id is not None:
        query = query.where(Url.user == user_id)
    if is_active is not None:
        query = query.where(Url.is_active == (is_active.lower() in ("true", "1", "yes")))

    total = query.count()
    urls = list(query.paginate(page, per_page))

    return jsonify({
        "total": total,
        "page": page,
        "per_page": per_page,
        "urls": [_url_to_dict(u) for u in urls],
    })


@urls_bp.route("/urls/<int:url_id>")
def get_url(url_id):
    try:
        url = Url.get_by_id(url_id)
    except Url.DoesNotExist:
        return jsonify({"error": "URL not found"}), 404
    return jsonify(_url_to_dict(url))


@urls_bp.route("/urls/<int:url_id>", methods=["DELETE"])
def deactivate_url(url_id):
    try:
        url = Url.get_by_id(url_id)
    except Url.DoesNotExist:
        return jsonify({"error": "URL not found"}), 404

    url.is_active = False
    url.updated_at = datetime.now()
    url.save()

    Event.create(
        url=url,
        user=None,
        event_type="deactivated",
        timestamp=datetime.now(),
        details=json.dumps({"short_code": url.short_code}),
    )

    logger.info("URL deactivated", extra={"url_id": url_id, "short_code": url.short_code})
    return jsonify({"message": "URL deactivated"}), 200


@urls_bp.route("/stats/<short_code>")
def url_stats(short_code):
    if not short_code or len(short_code) > 20:
        return jsonify({"error": "Invalid short code"}), 400

    try:
        url = Url.get(Url.short_code == short_code)
    except Url.DoesNotExist:
        return jsonify({"error": "URL not found"}), 404

    click_count = Event.select().where(
        Event.url == url, Event.event_type == "clicked"
    ).count()

    return jsonify({
        "short_code": short_code,
        "original_url": url.original_url,
        "title": url.title,
        "is_active": url.is_active,
        "click_count": click_count,
        "created_at": url.created_at.isoformat() if url.created_at else None,
    })


@urls_bp.route("/users")
def list_users():
    users = list(User.select().order_by(User.created_at.desc()).limit(100))
    return jsonify([
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ])
