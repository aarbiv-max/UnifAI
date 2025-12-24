from flask import Blueprint, jsonify
from webargs import fields
from shared.logger import logger
from global_utils.helpers.apiargs import from_query, from_body
from providers.aia_approval import check_user_approval_status, approve_user_for_aia

aia_approval_bp = Blueprint("aia_approval", __name__)

@aia_approval_bp.route("/check", methods=["GET"])
@from_query({"username": fields.Str(required=True)})
def check_user_approval(username):
    """
    Check if a user has approved the AI transparency notice.
    
    Args:
        username: Username of the current user
        
    Returns:
        JSON response indicating if user is approved
    """
    try:
        result = check_user_approval_status(username)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Failed to check user approval for {username}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@aia_approval_bp.route("/approve", methods=["POST"])
@from_body({"username": fields.Str(required=True)})
def approve_user(username):
    """
    Approve a user for AI transparency notice (add to approved list).
    
    Args:
        username: Username of the current user
        
    Returns:
        JSON response indicating success
    """
    try:
        result = approve_user_for_aia(username)
        return jsonify({
            "status": "success",
            "message": "User approved successfully",
            **result
        }), 200
    except Exception as e:
        logger.error(f"Failed to approve user {username}: {str(e)}")
        return jsonify({"error": str(e)}), 500

