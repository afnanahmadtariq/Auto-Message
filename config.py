import os
from dotenv import load_dotenv
import pymongo
from utils.logger import get_logger

# Load environment variables
load_dotenv()

logger = get_logger(__name__)

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
SCOPES = ["https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"]
REDIRECT_URI = "https://127.0.0.1:5000/auth/google/callback"

# Database connection (singleton pattern)
class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            logger.error("MONGO_URI is not set.")
            raise ValueError("MONGO_URI must be set in the environment variables.")

        logger.info(f"Connecting to MongoDB with URI: {mongo_uri}")
        try:
            self.mongo_client = pymongo.MongoClient(mongo_uri)
            server_info = self.mongo_client.server_info()
            logger.info(f"Connected to MongoDB: {server_info.get('version')}")
            self.db = self.mongo_client["autometa_app"]
            self.users_collection = self.db["users"]
            self.sessions_collection = self.db["sessions"]
            self.users_collection.create_index("identifier", unique=True)
        except pymongo.errors.ConnectionError as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise ValueError(f"Failed to connect to MongoDB: {e}")

# Global variables for user sessions
user_sessions = {}

def init_app(app):
    """Initialize the Flask app with configuration."""
    app_secret_key = os.getenv("FLASK_SECRET_KEY")
    if not app_secret_key:
        logger.error("FLASK_SECRET_KEY is not set.")
        raise ValueError("FLASK_SECRET_KEY must be set in the environment variables.")

    app.secret_key = app_secret_key
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_PERMANENT"] = False
    app.config["SESSION_USE_SIGNER"] = True

    # Initialize the database
    Database()  # Ensure the database is initialized when the app starts