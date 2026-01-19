"""Terms approval endpoints - driving adapter."""
from flask import Blueprint, jsonify
from webargs import fields

from bootstrap.app_container import terms_approval_service
from global_utils.helpers.apiargs import from_query, from_body
from shared.logger import logger

terms_approval_bp = Blueprint("terms_approval", __name__)


@terms_approval_bp.route("/user.approval.status.get", methods=["GET"])
@from_query({"username": fields.Str(required=True)})
def check_user_approval(username):
    """
    Check whether the specified user has approved the AI transparency notice.
    
    Parameters:
        username (str): The username to check approval for.
    
    Returns:
        dict: JSON object containing the approval status on success; on failure, a JSON object with an "error" message.
    """
    try:
        result = terms_approval_service().check_approval_status(username)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Failed to check user approval for {username}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@terms_approval_bp.route("/user.approval.record.post", methods=["POST"])
@from_body({"username": fields.Str(required=True)})
def approve_user(username):
    """
    Record that a user has approved the AI transparency notice.
    
    Parameters:
        username (str): The username of the user who approved the notice.
    
    Returns:
        A JSON HTTP response: on success, a 200 response with a success envelope containing
        "status", "message", and any additional keys returned by the service; on failure,
        a 500 response with {"error": "<error message>"}.
    """
    try:
        result = terms_approval_service().record_approval(username)
        return jsonify({
            "status": "success",
            "message": "User approval recorded successfully",
            **result
        }), 200
    except Exception as e:
        logger.error(f"Failed to record user approval for {username}: {str(e)}")
        return jsonify({"error": str(e)}), 500