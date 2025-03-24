from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from config import Database
from utils.logger import get_logger

logger = get_logger(__name__)

# Get the database instance
db = Database()
sessions_collection = db.sessions_collection

def setup_driver(user_id, headless=False):
    options = Options()
    # if headless:
    #     options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")  # Disable GPU acceleration
    options.add_argument("--window-size=1920,1080")  # Set a fixed window size
    driver = webdriver.Chrome(options=options)
    driver.get("https://web.whatsapp.com/")
    session_data = sessions_collection.find_one({"user_id": user_id})
    if session_data and "cookies" in session_data:
        for cookie in session_data["cookies"]:
            driver.add_cookie(cookie)
        driver.refresh()
    return driver

def save_session_to_mongo(user_id, cookies):
    sessions_collection.update_one(
        {"user_id": user_id},
        {"$set": {"cookies": cookies}},
        upsert=True
    )
    logger.info(f"Session saved for user {user_id}")