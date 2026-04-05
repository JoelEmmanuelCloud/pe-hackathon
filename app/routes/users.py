import csv
import io
import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from app.models.user import User

logger = logging.getLogger(__name__)
users_bp = Blueprint("users", __name__)


def _user_to_dict(u):
    return {
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


@users_bp.route("/users", methods=["GET"])
def list_users():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 100, type=int), 100)

    if page < 1 or per_page < 1:
        return jsonify({"error": "page and per_page must be positive"}), 400

    query = User.select().order_by(User.id)
    users = list(query.paginate(page, per_page))
    return jsonify([_user_to_dict(u) for u in users])


@users_bp.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    try:
        user = User.get_by_id(user_id)
    except User.DoesNotExist:
        return jsonify({"error": "User not found"}), 404
    return jsonify(_user_to_dict(user))


@users_bp.route("/users", methods=["POST"])
def create_user():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    username = data.get("username", "").strip()
    email = data.get("email", "").strip()

    if not username:
        return jsonify({"error": "username is required"}), 400
    if not email:
        return jsonify({"error": "email is required"}), 400

    if User.select().where(User.username == username).exists():
        return jsonify({"error": "username already exists"}), 409
    if User.select().where(User.email == email).exists():
        return jsonify({"error": "email already exists"}), 409

    user = User.create(username=username, email=email, created_at=datetime.now())
    logger.info("User created", extra={"user_id": user.id})
    return jsonify(_user_to_dict(user)), 201


@users_bp.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    try:
        user = User.get_by_id(user_id)
    except User.DoesNotExist:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    if "username" in data:
        user.username = data["username"].strip()
    if "email" in data:
        user.email = data["email"].strip()

    user.save()
    logger.info("User updated", extra={"user_id": user_id})
    return jsonify(_user_to_dict(user))


@users_bp.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    try:
        user = User.get_by_id(user_id)
    except User.DoesNotExist:
        return jsonify({"error": "User not found"}), 404

    user.delete_instance()
    logger.info("User deleted", extra={"user_id": user_id})
    return jsonify({"message": "User deleted"}), 200


@users_bp.route("/users/bulk", methods=["POST"])
def bulk_load_users():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    rows = data.get("rows") or data.get("users") or []
    if not rows:
        return jsonify({"error": "rows or users field required"}), 400

    created = 0
    for row in rows:
        username = str(row.get("username", "")).strip()
        email = str(row.get("email", "")).strip()
        if not username or not email:
            continue
        if not User.select().where(User.username == username).exists():
            User.create(username=username, email=email, created_at=datetime.now())
            created += 1

    return jsonify({"created": created}), 201
