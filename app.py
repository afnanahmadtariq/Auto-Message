from flask import Flask, redirect, url_for
from routes.auth import auth_bp
from routes.whatsapp import whatsapp_bp
from config import init_app
import logging

app = Flask(__name__)

# Initialize configuration (load env variables, set up database, etc.)
init_app(app)

# Register blueprints with URL prefixes
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(whatsapp_bp, url_prefix='/whatsapp')

# Add root route
@app.route("/")
def index():
    return redirect(url_for("auth.home"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)