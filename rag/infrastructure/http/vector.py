"""Vector stats endpoints - driving adapter."""
from flask import Blueprint, jsonify

from bootstrap.app_container import vector_stats_service
from shared.logger import logger

vector_bp = Blueprint("vector", __name__)


@vector_bp.route("/chunks.counts", methods=["GET"])
def get_chunks_counts():
    """
    Retrieve exact chunk (point) counts for Slack and Document collections.
    
    On success returns a JSON object with keys "slack", "document", and "total". On failure returns a JSON object with "slack", "document", and "total" set to 0 and an "error" string, and responds with HTTP status 500.
    
    Returns:
        tuple: (response, status_code) where `response` is a JSON-serializable mapping:
            - success: {"slack": int, "document": int, "total": int}
            - failure: {"slack": 0, "document": 0, "total": 0, "error": str}
    """
    try:
        stats = vector_stats_service().get_chunk_counts()
        return jsonify(stats.to_dict()), 200
    except Exception as e:
        logger.error(f"Failed to get chunks counts: {e}")
        return jsonify({"slack": 0, "document": 0, "total": 0, "error": str(e)}), 500
