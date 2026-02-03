from flask import Blueprint, jsonify, current_app
from global_utils.helpers.apiargs import from_query
from webargs import fields, validate
from typing import Dict, Any, List
from ..decorators import require_admin_access

statistics_bp = Blueprint("statistics", __name__)

# Valid time range values for analytics endpoint
VALID_TIME_RANGES = ["today", "7days", "30days", "all"]


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


@statistics_bp.route("/analytics.overview.get", methods=["GET"])
@from_query({
    "time_range": fields.Str(
        data_key="time_range",
        load_default="all",
        validate=validate.OneOf(VALID_TIME_RANGES, error="Time range must be one of {choices}")
    ),
    "user_id": fields.Str(data_key="userId", required=True)
})
@require_admin_access
def get_analytics(time_range, user_id):
    """
    Get comprehensive system-wide analytics statistics for workflows, users, and blueprints.
    Returns all key metrics in a single response for the Analytics dashboard.
    
    Requires admin access (user must be in admin_allowed_users list).
    If admin_allowed_users is empty, Analytics is disabled and access is denied.
    
    Query params:
        time_range (str): Time range filter - 'today', '7days', '30days', or 'all' (default: 'all')
        userId (str, required): User ID for access control (must be in admin_allowed_users list)
    """
    try:
        container = current_app.container
        analytics_service = container.analytics_service
        
        analytics = analytics_service.get_analytics(time_range=time_range)
        
        return jsonify(analytics.model_dump(mode="json")), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

