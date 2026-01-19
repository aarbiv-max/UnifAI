"""Health check endpoints - driving adapter."""
from flask import Blueprint, jsonify

from config.app_config import AppConfig

health_bp = Blueprint("health", __name__)


@health_bp.route("/", methods=["GET"])
def health_check():
    """
    Return a basic service health payload.
    
    Returns:
        tuple: A Flask JSON response with {"status": "ok", "message": "Server is healthy"} and the HTTP status code 200.
    """
    return jsonify({"status": "ok", "message": "Server is healthy"}), 200


@health_bp.route("/version", methods=["GET"])
def get_version():
    """
    Return the application's version from configuration.
    
    Returns:
        response (tuple): A Flask JSON response (payload {"version": "<version>"}) and HTTP status code 200. The version is read from the configuration key "version", defaulting to "1.0.0" if absent.
    """
    config = AppConfig.get_instance()
    return jsonify({"version": config.get("version", "1.0.0")}), 200
