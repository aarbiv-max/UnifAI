from flask import Blueprint, jsonify
from shared.logger import logger
from providers.vector_stats import get_chunks_counts as _get_chunks_counts
from providers.umami import get_website_id as _get_website_id

vector_bp = Blueprint("umami", __name__)

@vector_bp.route("/get.website.id", methods=["GET"])
def get_website_id():
    """Return website ID from Umami website."""
    try:
        data = _get_website_id()
        return jsonify(data), 200
    except Exception as e:
        logger.error(f"Failed to get website ID: {e}")
        return jsonify({"error": str(e)}), 500


