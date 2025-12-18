from flask import Blueprint, jsonify, current_app
from global_utils.helpers.apiargs import from_query
from webargs import fields
from typing import Dict, Any, List
from ..decorators import require_admin_access

statistics_bp = Blueprint("statistics", __name__)


@statistics_bp.route("/stats.get", methods=["GET"])
@from_query({
    "user_id": fields.Str(data_key="userId", required=True),
})
def get_all(user_id):
    """
    Get aggregated statistics for all features.
    Returns all stats in a single response for optimal performance.
    """
    try:
        container = current_app.container
        statistics_service = container.statistics_service
        
        stats = statistics_service.get_all(user_id)
        
        return jsonify(stats.model_dump(mode="json")), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@statistics_bp.route("/overview", methods=["GET"])
@from_query({
    "time_range": fields.Str(
        data_key="time_range",
        load_default="all",
        validate=lambda x: x in ["today", "7days", "30days", "all"]
    ),
    "user_id": fields.Str(
        data_key="userId",
        required=False,
        load_default=None
    )
})
@require_admin_access
def get_overview(time_range, user_id=None):
    """
    Get comprehensive system-wide overview statistics.
    Returns all key metrics in a single response for the dashboard.
    
    Requires admin access if admin_allowed_users is configured in AppConfig.
    If admin_allowed_users is empty
    
    Query params:
        time_range (str): Time range filter - 'today', '7days', '30days', or 'all' (default: 'all')
        userId (str, optional): User ID for access control (required if admin_allowed_users is configured)
    """
    try:
        container = current_app.container
        statistics_service = container.statistics_service
        
        overview = statistics_service.get_overview(time_range=time_range)
        
        return jsonify(overview.model_dump(mode="json")), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

