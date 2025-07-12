# File: services/service-template/app/main.py

from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
import os # Used to get the port for logging

# --- Boilerplate Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Enable CORS for all routes, allowing your frontend to communicate with this service.
CORS(app)

# --- API Endpoint Definition ---
@app.route("/api/template-route", methods=["GET"])
def handle_get_request():
    """A sample endpoint to show the service is running."""
    logger.info("Service template received a GET request.")
    return jsonify({
        "message": "Response from the service-template",
        "status": "ok"
    })
