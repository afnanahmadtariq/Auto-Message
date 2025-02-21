from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
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

# Store WhatsApp sessions for users
user_sessions = {}

def create_driver():
    """Creates a new Selenium WebDriver instance."""
    options = Options()
    options.add_argument("--headless")  # Run in headless mode (remove for debugging)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

@app.route("/")
def home():
    """Serve the login page or main interface."""
    if "user_id" in session and session["user_id"] in user_sessions:
        return render_template("index.html")  # User already logged in
    return render_template("login.html")  # Show login page

@app.route("/login", methods=["POST"])
def login():
    """Handle user login and start WhatsApp Web session."""
    user_id = str(uuid.uuid4())  # Generate unique session ID
    session["user_id"] = user_id  # Save session in cookie

    # Start a new WebDriver for this user
    driver = create_driver()
    driver.get("https://web.whatsapp.com/")
    
    user_sessions[user_id] = driver  # Store driver instance

    return jsonify({"status": "success", "message": "Scan the QR code to log in."})

@app.route("/send", methods=["POST"])
def send_message():
    """Send WhatsApp message using stored session."""
    if "user_id" not in session or session["user_id"] not in user_sessions:
        return jsonify({"error": "You must log in first!"}), 403

    data = request.json
    phone = data.get("phone")
    message = data.get("message")

    if not phone or not message:
        return jsonify({"error": "Phone number and message are required"}), 400

    driver = user_sessions[session["user_id"]]  # Retrieve user's driver session

    # Open WhatsApp chat and send message
    url = f"https://web.whatsapp.com/send?phone={phone}&text={message}"
    driver.get(url)
    time.sleep(10)  # Wait for page to load

    try:
        send_button = driver.find_element("xpath", '//span[@data-icon="send"]')
        send_button.click()
        time.sleep(2)
        return jsonify({"status": "Message sent successfully!"})
    except Exception as e:
        return jsonify({"error": "Failed to send message", "details": str(e)})

@app.route("/logout")
def logout():
    """Logout user and close their WhatsApp session."""
    if "user_id" in session:
        user_id = session.pop("user_id", None)
        if user_id in user_sessions:
            user_sessions[user_id].quit()  # Close browser session
            del user_sessions[user_id]

    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
