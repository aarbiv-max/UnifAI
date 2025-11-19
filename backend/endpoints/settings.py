from flask import Blueprint, jsonify
from shared.logger import logger
from providers.settings import get_umami_settings as _get_umami_settings

# we might want this as a "settings bp and not umami only"
settings_bp = Blueprint("settings", __name__)

@settings_bp.route("/get.umami.settings", methods=["GET"])
def get_umami_settings():
    """Return website ID from Umami website."""
    try:
        data = _get_umami_settings()
        return jsonify(data), 200
    except Exception as e:
        logger.error(f"Failed to get Umami settings: {e}")
        return jsonify({"error": str(e)}), 500