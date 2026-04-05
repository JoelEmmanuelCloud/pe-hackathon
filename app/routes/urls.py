import csv
import json
import logging
import os
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
    data = request.get_json(force=True, silent=True)
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

    data = request.get_json(force=True, silent=True)
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


@urls_bp.route("/urls/bulk", methods=["POST"])
def bulk_load_urls():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    file_name = data.get("file")
    if file_name:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        csv_path = os.path.join(base_dir, "data", file_name)
        if not os.path.exists(csv_path):
            return jsonify({"error": f"File not found: {file_name}"}), 404
        created = 0
        valid_user_ids = set(u.id for u in User.select(User.id))
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                short_code = str(row.get("short_code", "")).strip()
                original_url = str(row.get("original_url", "")).strip()
                if not short_code or not original_url:
                    continue
                if Url.select().where(Url.short_code == short_code).exists():
                    continue
                raw_user_id = row.get("user_id")
                try:
                    user_id = int(raw_user_id) if raw_user_id else None
                except (ValueError, TypeError):
                    user_id = None
                if user_id not in valid_user_ids:
                    user_id = None
                is_active_raw = str(row.get("is_active", "True")).strip().lower()
                is_active = is_active_raw in ("true", "1", "yes")
                created_at_raw = row.get("created_at")
                updated_at_raw = row.get("updated_at")
                try:
                    created_at = datetime.fromisoformat(created_at_raw) if created_at_raw else datetime.now()
                except ValueError:
                    created_at = datetime.now()
                try:
                    updated_at = datetime.fromisoformat(updated_at_raw) if updated_at_raw else datetime.now()
                except ValueError:
                    updated_at = datetime.now()
                Url.create(
                    user=user_id,
                    short_code=short_code,
                    original_url=original_url,
                    title=str(row.get("title", "")).strip(),
                    is_active=is_active,
                    created_at=created_at,
                    updated_at=updated_at,
                )
                created += 1
        return jsonify({"created": created}), 201

    rows = data.get("rows") or data.get("urls") or []
    if not rows:
        return jsonify({"error": "rows or urls field required"}), 400

    created = 0
    for row in rows:
        short_code = str(row.get("short_code", "")).strip()
        original_url = str(row.get("original_url", "")).strip()
        if not short_code or not original_url:
            continue
        if not Url.select().where(Url.short_code == short_code).exists():
            Url.create(
                short_code=short_code,
                original_url=original_url,
                title=row.get("title", ""),
                is_active=bool(row.get("is_active", True)),
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            created += 1

    return jsonify({"created": created}), 201
