from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from extensions import db
from models.user import User

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

def _serialize_user(user):
    return {
        "id": user.id,
        "email": user.email,
        "role": getattr(user, "role", "candidate"),
        "is_verified": bool(getattr(user, "is_verified", True)),
    }

# REGISTER
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "User already exists"}), 409

    user = User(email=email)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    access_token = create_access_token(identity=str(user.id))

    return jsonify({"message": "User registered successfully",
                    "access_token": access_token,
                    "user": _serialize_user(user)}), 201


# LOGIN
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401

    access_token = create_access_token(identity=str(user.id))


    return jsonify({
        "access_token": access_token,
        "user": _serialize_user(user)
    })


# TEST PROTECTED ROUTE
@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    identity = get_jwt_identity()

    user = None

    # Support both current tokens (user id) and older tokens (email identity).
    try:
        user = User.query.get(int(identity))
    except (TypeError, ValueError):
        user = User.query.filter_by(email=str(identity).strip()).first()

    if not user:
        return jsonify({"error": "User not found for current token"}), 401

    return jsonify(_serialize_user(user))
