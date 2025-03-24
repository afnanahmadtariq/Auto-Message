from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import base64
from io import BytesIO
from config import user_sessions
from utils.driver import setup_driver, save_session_to_mongo
from utils.logger import get_logger

whatsapp_bp = Blueprint("whatsapp", __name__)
logger = get_logger(__name__)

@whatsapp_bp.route("/waiting")
def waiting():
    if "user_id" not in session:
        return redirect(url_for("auth.home"))

    user_id = session["user_id"]
    if user_id not in user_sessions:
        driver = setup_driver(user_id, headless=True)
        user_sessions[user_id] = driver
    else:
        driver = user_sessions[user_id]

    try:
        qr_code_element = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.XPATH, '//canvas[@aria-label="Scan this QR code to link a device!"]'))
        )
        try:
            # Try to capture the QR code element directly
            qr_code_screenshot = qr_code_element.screenshot_as_png
        except Exception as e:
            logger.warning(f"Failed to capture QR code element directly: {e}. Falling back to full page screenshot.")
            # Fallback: Take a full page screenshot and crop to the QR code area
            full_screenshot = driver.get_screenshot_as_png()
            # Get the location and size of the QR code element
            location = qr_code_element.location
            size = qr_code_element.size
            # Open the screenshot with PIL to crop it
            image = Image.open(BytesIO(full_screenshot))
            left = location['x']
            top = location['y']
            right = left + size['width']
            bottom = top + size['height']
            qr_code_image = image.crop((left, top, right, bottom))
            # Convert cropped image to PNG bytes
            buffered = BytesIO()
            qr_code_image.save(buffered, format="PNG")
            qr_code_screenshot = buffered.getvalue()

        qr_code_base64 = base64.b64encode(qr_code_screenshot).decode('utf-8')
        return render_template("waiting.html", qr_code_base64=qr_code_base64)
    except Exception as e:
        logger.error(f"Failed to capture WhatsApp QR code for user {user_id}: {e}")
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//div[@data-testid="chat-list"]'))
            )
            logger.info(f"User {user_id} already logged in. Redirecting to dashboard.")
            return redirect(url_for("whatsapp.dashboard"))
        except:
            driver.quit()
            del user_sessions[user_id]
            return "Failed to load WhatsApp QR code or login. Please try again.", 500
        
@whatsapp_bp.route("/check_login", methods=["GET"])
def check_login():
    user_id = session.get("user_id")
    if not user_id or user_id not in user_sessions:
        logger.error(f"User {user_id} not in session or user_sessions.")
        return jsonify({"logged_in": False})

    driver = user_sessions.get(user_id)
    if not driver:
        logger.error(f"No driver found for user {user_id}.")
        return jsonify({"logged_in": False})

    try:
        # Ensure the driver is on the WhatsApp page
        # driver.get("https://web.whatsapp.com/")
        # Wait for either the QR code or the chat list
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((
                By.XPATH,
                '//canvas[@aria-label="Scan this QR code to link a device!"] | //*[@id="app"]/div/div[3]/div/div[3]/header/header/div/div[1]/h1'
            ))
        )
        # Check for the QR code
        try:
            driver.find_element(By.XPATH, '//canvas[@aria-label="Scan this QR code to link a device!"]')
            logger.info(f"QR code still present for user {user_id}. Not logged in yet.")
            return jsonify({"logged_in": False})
        except:
            # QR code not found, check for chat list to confirm login
            try:
                driver.find_element(By.XPATH, '//*[@id="app"]/div/div[3]/div/div[3]/header/header/div/div[1]/h1')
                logger.info(f"Chat list found for user {user_id}. User is logged in.")
                # Save session cookies and reinitialize driver in headless mode
                cookies = driver.get_cookies()
                save_session_to_mongo(user_id, cookies)
                driver.quit()
                headless_driver = setup_driver(user_id, headless=True)
                user_sessions[user_id] = headless_driver
                return jsonify({"logged_in": True})
            except:
                logger.error(f"Neither QR code nor chat list found for user {user_id}.")
                return jsonify({"logged_in": False})
    except Exception as e:
        logger.error(f"Error checking login status for user {user_id}: {e}")
        return jsonify({"logged_in": False})

@whatsapp_bp.route("/dashboard")
def dashboard():
    if "user_id" not in session or session["user_id"] not in user_sessions:
        return redirect(url_for("auth.home"))

    driver = user_sessions[session["user_id"]]
    recent_contacts = get_recent_contacts(driver)
    return render_template("index.html", recent_contacts=recent_contacts)

def get_recent_contacts(driver):
    driver.get("https://web.whatsapp.com/")
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[@data-testid="cell-frame-container"]'))
        )
        contact_elements = driver.find_elements(By.XPATH, '//div[@data-testid="cell-frame-container"]')[:5]
        recent_contacts = []
        for contact in contact_elements:
            name = contact.find_element(By.XPATH, './/span[@title]').get_attribute("title")
            recent_contacts.append({"name": name, "phone": "unknown"})
        logger.info("Fetched recent contacts")
        return recent_contacts
    except Exception as e:
        logger.error(f"Error fetching recent contacts: {e}")
        return []

@whatsapp_bp.route("/search_contacts", methods=["POST"])
def search_contacts():
    if "user_id" not in session or session["user_id"] not in user_sessions:
        return jsonify({"error": "User not logged in"}), 403

    query = request.json.get("query")
    if not query:
        return jsonify({"error": "Query is required"}), 400

    driver = user_sessions[session["user_id"]]
    driver.get("https://web.whatsapp.com/")
    try:
        search_bar = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[@title="Search input textbox"]'))
        )
        search_bar.clear()
        search_bar.send_keys(query)
        search_bar.send_keys(Keys.ENTER)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[@data-testid="cell-frame-container"]'))
        )
        contact_elements = driver.find_elements(By.XPATH, '//div[@data-testid="cell-frame-container"]')
        contacts = []
        for contact in contact_elements:
            name = contact.find_element(By.XPATH, './/span[@title]').get_attribute("title")
            contacts.append({"name": name, "phone": "unknown"})
        logger.info(f"Searched contacts for query: {query}")
        return jsonify({"contacts": contacts})
    except Exception as e:
        logger.error(f"Error searching contacts: {e}")
        return jsonify({"error": "Failed to search contacts", "details": str(e)}), 500

@whatsapp_bp.route("/send", methods=["POST"])
def send_message():
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
        try:
            send_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//span[@data-icon="send"]'))
            )
            send_button.click()
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return jsonify({"error": "Failed to send message", "details": str(e)}), 500
    logger.info(f"Sent message {repeat} time(s) to {phone}")
    return jsonify({"status": f"Message sent {repeat} time(s) successfully!"})