from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import pymongo
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
import pyotp
import os
import time
import uuid

app = Flask(__name__)

# Secret key for session management
app.secret_key = "your_secret_key"

# Configure Flask-Session
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True

# MongoDB setup
mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
db = mongo_client["whatsapp_app"]
users_collection = db["users"]
sessions_collection = db["sessions"]

# Google OAuth setup
GOOGLE_CLIENT_ID = "your_google_client_id"
GOOGLE_CLIENT_SECRET = "your_google_client_secret"
SCOPES = ["https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"]
REDIRECT_URI = "http://localhost:5000/google/callback"

# Store WhatsApp sessions for users (in-memory fallback)
user_sessions = {}

def create_driver(headless=False):
    """Creates a Selenium WebDriver."""
    options = Options()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--user-data-dir=/tmp/selenium_profile")
    return webdriver.Chrome(options=options)

def save_session_to_mongo(user_id, cookies):
    """Save WebDriver cookies to MongoDB."""
    sessions_collection.update_one(
        {"user_id": user_id},
        {"$set": {"cookies": cookies, "last_updated": time.time()}},
        upsert=True
    )

def load_session_from_mongo(user_id):
    """Load WebDriver cookies from MongoDB."""
    session_data = sessions_collection.find_one({"user_id": user_id})
    if session_data:
        return session_data["cookies"]
    return None

@app.route("/")
def home():
    """Redirect to login if authenticated, otherwise show signup."""
    if "user_id" in session and session["user_id"] in user_sessions:
        return redirect(url_for("dashboard"))
    return redirect(url_for("signup"))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    """Handle signup for new users."""
    if request.method == "GET":
        return render_template("signup.html")

    data = request.get_json()
    auth_method = data.get("auth_method")
    identifier = data.get("identifier")

    if not auth_method:
        return jsonify({"error": "Missing authentication method"}), 400

    # Check if user already exists
    if auth_method == "google" and identifier:
        user = users_collection.find_one({"identifier": identifier})
        if user:
            return jsonify({"error": "User already exists. Please log in instead."}), 400

    user_id = str(uuid.uuid4())
    session["user_id"] = user_id

    user_data = {"user_id": user_id, "primary_auth": auth_method, "identifier": identifier}

    if auth_method == "google":
        flow = InstalledAppFlow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uris": [REDIRECT_URI],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            },
            SCOPES
        )
        flow.redirect_uri = REDIRECT_URI
        authorization_url, state = flow.authorization_url(access_type="offline", include_granted_scopes="true")
        session["state"] = state
        return jsonify({"redirect": authorization_url})

    elif auth_method == "2fa":
        user = users_collection.find_one({"identifier": identifier})
        if user:
            return jsonify({"error": "User already exists. Please log in instead."}), 400

        # Generate a new 2FA secret for the user
        secret = pyotp.random_base32()
        users_collection.insert_one({**user_data, "2fa_secret": secret})
        return jsonify({"message": "Scan this secret in your 2FA app", "secret": secret})

    return jsonify({"error": "Invalid authentication method"}), 400

@app.route("/login", methods=["GET", "POST"])
def login():
    """Handle login for returning users."""
    if request.method == "GET":
        return render_template("login.html")

    data = request.get_json()
    auth_method = data.get("auth_method")
    identifier = data.get("identifier")

    if not auth_method:
        return jsonify({"error": "Missing authentication method"}), 400

    user = users_collection.find_one({"identifier": identifier})
    if not user:
        return jsonify({"error": "User not found. Please sign up first."}), 404

    session["user_id"] = user["user_id"]

    if auth_method == "google":
        flow = InstalledAppFlow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uris": [REDIRECT_URI],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            },
            SCOPES
        )
        flow.redirect_uri = REDIRECT_URI
        authorization_url, state = flow.authorization_url(access_type="offline", include_granted_scopes="true")
        session["state"] = state
        return jsonify({"redirect": authorization_url})

    elif auth_method == "2fa":
        if "2fa_secret" not in user:
            return jsonify({"error": "2FA not set up for this user."}), 400

        totp = pyotp.TOTP(user["2fa_secret"])
        if totp.verify(identifier):
            return jsonify({"success": "Login successful"})
        else:
            return jsonify({"error": "Invalid 2FA token"}), 401

    return jsonify({"error": "Invalid authentication method"}), 400

@app.route("/google/callback")
def google_callback():
    """Handle Google OAuth callback."""
    state = session.get("state")
    flow = InstalledAppFlow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uris": [REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        SCOPES,
        state=state
    )
    flow.redirect_uri = REDIRECT_URI
    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials
    user_id = session["user_id"]
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"google_credentials": credentials.to_json()}},
        upsert=True
    )
    return redirect(url_for("waiting"))

@app.route("/waiting")
def waiting():
    """Show QR code scanning page and restore session if available."""
    if "user_id" not in session:
        return redirect(url_for("home"))

    user_id = session["user_id"]
    cookies = load_session_from_mongo(user_id)

    if cookies:
        driver = create_driver(headless=True)
        driver.get("https://web.whatsapp.com/")
        for cookie in cookies:
            driver.add_cookie(cookie)
        driver.refresh()
        user_sessions[user_id] = driver
    else:
        driver = create_driver(headless=False)
        driver.get("https://web.whatsapp.com/")
        try:
            WebDriverWait(driver, 99999).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="app"]/div/div[3]/div/div[3]/header/header/div/div[1]/h1'))
            )
            cookies = driver.get_cookies()
            save_session_to_mongo(user_id, cookies)
            driver.quit()
            headless_driver = create_driver(headless=True)
            headless_driver.get("https://web.whatsapp.com/")
            for cookie in cookies:
                headless_driver.add_cookie(cookie)
            headless_driver.refresh()
            user_sessions[user_id] = headless_driver
        except:
            return "Login failed! Please try again."

    return render_template("waiting.html")

@app.route("/check_login", methods=["GET"])
def check_login():
    """Check if WhatsApp Web session is active."""
    user_id = session.get("user_id")
    if not user_id or user_id not in user_sessions:
        return jsonify({"logged_in": False})

    driver = user_sessions[user_id]
    try:
        driver.find_element("xpath", '//canvas[@aria-label="Scan me!"]')
        return jsonify({"logged_in": False})
    except:
        return jsonify({"logged_in": True})

@app.route("/dashboard")
def dashboard():
    """Main UI for sending messages."""
    if "user_id" not in session or session["user_id"] not in user_sessions:
        return redirect(url_for("home"))

    driver = user_sessions[session["user_id"]]
    recent_contacts = get_recent_contacts(driver)
    return render_template("index.html", recent_contacts=recent_contacts)

def get_recent_contacts(driver):
    """Fetch the 5 most recent contacts using Selenium."""
    driver.get("https://web.whatsapp.com/")
    time.sleep(5)
    recent_contacts = []
    try:
        contact_elements = driver.find_elements("xpath", '//div[@role="listitem"][@data-testid="cell-frame-container"]')[:5]
        for contact in contact_elements:
            name = contact.find_element("xpath", './/span[@title]').get_attribute("title")
            recent_contacts.append({"name": name, "phone": "unknown"})
    except Exception as e:
        print(f"Error fetching recent contacts: {e}")
    return recent_contacts

@app.route("/search_contacts", methods=["POST"])
def search_contacts():
    """Search WhatsApp contacts using Selenium."""
    if "user_id" not in session or session["user_id"] not in user_sessions:
        return jsonify({"error": "User not logged in"}), 403

    query = request.json.get("query")
    driver = user_sessions[session["user_id"]]
    driver.get("https://web.whatsapp.com/")
    time.sleep(2)

    try:
        search_bar = driver.find_element("xpath", '//div[@title="Search input textbox"]')
        search_bar.clear()
        search_bar.send_keys(query)
        search_bar.send_keys(Keys.ENTER)
        time.sleep(2)

        contact_elements = driver.find_elements("xpath", '//div[@role="listitem"][@data-testid="cell-frame-container"]')
        contacts = []
        for contact in contact_elements:
            name = contact.find_element("xpath", './/span[@title]').get_attribute("title")
            contacts.append({"name": name, "phone": "unknown"})
        return jsonify({"contacts": contacts})
    except Exception as e:
        return jsonify({"error": "Failed to search contacts", "details": str(e)}), 500

@app.route("/send", methods=["POST"])
def send_message():
    """Send WhatsApp message with repeat functionality."""
    if "user_id" not in session or session["user_id"] not in user_sessions:
        return jsonify({"error": "You must log in first!"}), 403

    data = request.json
    phone = data.get("phone")
    message = data.get("message")
    repeat = int(data.get("repeat", 1))

    if not phone or not message:
        return jsonify({"error": "Phone number and message are required"}), 400

    driver = user_sessions[session["user_id"]]
    url = f"https://web.whatsapp.com/send?phone={phone}&text={message}"

    for _ in range(repeat):
        driver.get(url)
        time.sleep(5)
        try:
            send_button = driver.find_element("xpath", '//span[@data-icon="send"]')
            send_button.click()
            time.sleep(0.2)
        except Exception as e:
            return jsonify({"error": "Failed to send message", "details": str(e)})

    return jsonify({"status": f"Message sent {repeat} time(s) successfully!"})

@app.route("/add_secondary_auth", methods=["POST"])
def add_secondary_auth():
    """Add a secondary authentication method."""
    if "user_id" not in session:
        return jsonify({"error": "User not logged in"}), 403

    user_id = session["user_id"]
    auth_method = request.form.get("secondary_auth")
    user = users_collection.find_one({"user_id": user_id})

    if user["primary_auth"] == auth_method:
        return jsonify({"error": "Secondary method cannot be the same as primary"}), 400

    if auth_method == "2fa":
        secret = pyotp.random_base32()
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"secondary_auth": auth_method, "2fa_secret": secret}}
        )
        return jsonify({"message": "Scan this secret in your 2FA app", "secret": secret})

    elif auth_method == "google":
        flow = InstalledAppFlow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uris": [REDIRECT_URI],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            },
            SCOPES
        )
        flow.redirect_uri = REDIRECT_URI
        authorization_url, state = flow.authorization_url(access_type="offline", include_granted_scopes="true")
        session["state"] = state
        return redirect(authorization_url)

@app.route("/logout")
def logout():
    """Logout user and close their WhatsApp session."""
    if "user_id" in session:
        user_id = session.pop("user_id", None)
        if user_id in user_sessions:
            user_sessions[user_id].quit()
            del user_sessions[user_id]
            sessions_collection.delete_one({"user_id": user_id})

    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)