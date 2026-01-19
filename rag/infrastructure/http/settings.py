"""Settings endpoints - driving adapter."""
from flask import Blueprint, jsonify

from bootstrap.app_container import umami_client
from config.app_config import AppConfig
from shared.logger import logger

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/get.umami.settings", methods=["GET"])
def get_umami_settings():
    """
    Fetches Umami analytics website settings for frontend use.
    
    Reads the configured `umami_website_name` (defaults to "unifai") and retrieves the corresponding website data from the Umami client.
    
    Returns:
        A tuple (payload, status_code) where `payload` is a JSON-serializable dict containing the Umami website data on success, or an error message dict on failure; `status_code` is 200 on success, 500 for configuration errors, or 503 when the Umami service is unavailable.
    """
    try:
        config = AppConfig.get_instance()
        website_name = config.get("umami_website_name", "unifai")
        data = umami_client().get_website_id(website_name)
        return jsonify(data), 200
    except ValueError as e:
        logger.error(f"Umami configuration error: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error(f"Umami service unavailable: {e}")
        return jsonify({"error": "Umami service unavailable"}), 503
