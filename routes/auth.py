from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from google_auth_oauthlib.flow import InstalledAppFlow
import pyotp
import uuid
import requests
from config import Database, user_sessions, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, SCOPES, REDIRECT_URI
from utils.qr_code import generate_2fa_qr_code
from utils.logger import get_logger

auth_bp = Blueprint("auth", __name__)
logger = get_logger(__name__)

# Initialize the database instance
db = Database()
users_collection = db.users_collection
sessions_collection = db.sessions_collection

@auth_bp.route("/")
def home():
    if "user_id" in session and session["user_id"] in user_sessions:
        return redirect(url_for("whatsapp.dashboard"))
    return redirect(url_for("auth.signup"))

@auth_bp.route("/signup", methods=["GET"])
def signup():
    return render_template("signup.html")

@auth_bp.route("/signup/google", methods=["POST"])
def signup_with_google():
    user_id = str(uuid.uuid4())
    session["user_id"] = user_id
    session["auth_method"] = "signup"
    flow = InstalledAppFlow.from_client_config(
        {"web": {"client_id": GOOGLE_CLIENT_ID, "client_secret": GOOGLE_CLIENT_SECRET, "redirect_uris": [REDIRECT_URI], "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token"}},
        SCOPES
    )
    flow.redirect_uri = REDIRECT_URI
    authorization_url, state = flow.authorization_url(access_type="offline", include_granted_scopes="true")
    session["state"] = state
    return jsonify({"redirect": authorization_url})

@auth_bp.route("/signup/2fa", methods=["POST"])
def signup_with_2fa():
    if users_collection is None:
        logger.error("Database not initialized.")
        return jsonify({"error": "Database not initialized."}), 500

    data = request.get_json()
    identifier = data.get("identifier")
    if not identifier:
        return jsonify({"error": "Missing identifier"}), 400

    if users_collection.find_one({"identifier": identifier}):
        return jsonify({"error": "User already exists. Please log in."}), 400

    user_id = str(uuid.uuid4())
    session["user_id"] = user_id
    secret = pyotp.random_base32()
    session["2fa_secret"] = secret
    users_collection.insert_one({"user_id": user_id, "primary_auth": "2fa", "identifier": identifier, "2fa_secret": secret})
    qr_code = generate_2fa_qr_code(secret, identifier)
    logger.info(f"Generated 2FA QR code for user {user_id}")
    return jsonify({"message": "Scan this QR code in your 2FA app", "secret": secret, "qr_code": qr_code})

@auth_bp.route("/verify_2fa", methods=["POST"])
def verify_2fa():
    data = request.get_json()
    token = data.get("token")
    user_id = session.get("user_id")
    secret = session.get("2fa_secret")

    if not user_id or not secret:
        return jsonify({"error": "Session expired. Please restart signup."}), 400

    totp = pyotp.TOTP(secret)
    if totp.verify(token):
        session.pop("2fa_secret", None)
        logger.info(f"2FA verified for user {user_id}")
        return jsonify({"success": "2FA verified successfully"})
    return jsonify({"error": "Invalid 2FA token"}), 401

@auth_bp.route("/login", methods=["GET"])
def login():
    return render_template("login.html")

@auth_bp.route("/login/google", methods=["POST"])
def login_with_google():
    user_id = str(uuid.uuid4())
    session["user_id"] = user_id
    session["auth_method"] = "login"
    flow = InstalledAppFlow.from_client_config(
        {"web": {"client_id": GOOGLE_CLIENT_ID, "client_secret": GOOGLE_CLIENT_SECRET, "redirect_uris": [REDIRECT_URI], "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token"}},
        SCOPES
    )
    flow.redirect_uri = REDIRECT_URI
    authorization_url, state = flow.authorization_url(access_type="offline", include_granted_scopes="true")
    session["state"] = state
    return jsonify({"redirect": authorization_url})

@auth_bp.route("/login/2fa", methods=["POST"])
def login_with_2fa():
    if users_collection is None:
        logger.error("Database not initialized.")
        return jsonify({"error": "Database not initialized."}), 500

    data = request.get_json()
    identifier = data.get("identifier")
    token = data.get("token")
    if not identifier or not token:
        return jsonify({"error": "Missing identifier or token"}), 400

    user = users_collection.find_one({"identifier": identifier})
    if not user:
        return jsonify({"error": "User not found. Please sign up."}), 404

    totp = pyotp.TOTP(user["2fa_secret"])
    if totp.verify(token):
        session["user_id"] = user["user_id"]
        logger.info(f"User {user['user_id']} logged in with 2FA")
        return jsonify({"success": "Login successful"})
    return jsonify({"error": "Invalid 2FA token"}), 401

@auth_bp.route("/google/callback")
def google_callback():
    state = session.get("state")
    auth_method = session.get("auth_method")
    user_id = session.get("user_id")
    if not auth_method or not user_id:
        return "Session expired. Please try again.", 400

    flow = InstalledAppFlow.from_client_config(
        {"web": {"client_id": GOOGLE_CLIENT_ID, "client_secret": GOOGLE_CLIENT_SECRET, "redirect_uris": [REDIRECT_URI], "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token"}},
        SCOPES, state=state
    )
    flow.redirect_uri = REDIRECT_URI
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials

    userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
    headers = {"Authorization": f"Bearer {credentials.token}"}
    response = requests.get(userinfo_url, headers=headers)
    user_info = response.json()
    email = user_info.get("email")
    if not email:
        return "Failed to retrieve email from Google.", 400

    if users_collection is None:
        return "Database not initialized.", 500

    user = users_collection.find_one({"identifier": email})
    if auth_method == "signup":
        if user:
            return "User already exists. Please log in.", 400
        users_collection.insert_one({"user_id": user_id, "primary_auth": "google", "identifier": email})
        logger.info(f"User {user_id} signed up with Google")
    elif auth_method == "login":
        if not user:
            return "User not found. Please sign up.", 404
        session["user_id"] = user["user_id"]
        logger.info(f"User {user['user_id']} logged in with Google")

    return redirect(url_for("whatsapp.waiting"))

@auth_bp.route("/logout")
def logout():
    if "user_id" in session:
        user_id = session.pop("user_id", None)
        if user_id in user_sessions:
            user_sessions[user_id].quit()
            del user_sessions[user_id]
            sessions_collection.delete_one({"user_id": user_id})
        logger.info(f"User {user_id} logged out")
    return redirect(url_for("auth.home"))