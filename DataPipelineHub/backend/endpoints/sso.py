from flask import Blueprint, jsonify
from shared.logger import logger
from services.sso_service import SSOService

sso_bp = Blueprint('sso', __name__)
sso_service = SSOService()

@sso_bp.route('/auth/user')
def get_current_user():
    """Get current user information"""
    try:
        response = sso_service.get_user_info()
        return response.json(), response.status_code
    except Exception as e:
        logger.error(f"Error getting user from SSO backend: {str(e)}")
        return jsonify({"error": "Failed to get user information"}), 500

@sso_bp.route('/auth/refresh', methods=['POST'])
def refresh_token():
    """Refresh access token"""
    try:
        response = sso_service.refresh_token()
        return response.json(), response.status_code
    except Exception as e:
        logger.error(f"Error refreshing token from SSO backend: {str(e)}")
        return jsonify({"error": "Token refresh failed"}), 500

@sso_bp.route('/protected/user.profile')
def get_user_profile():
    """Get user profile"""
    try:
        response = sso_service.get_user_profile()
        return response.json(), response.status_code
    except Exception as e:
        logger.error(f"Error getting user profile from SSO backend: {str(e)}")
        return jsonify({"error": "Failed to get user profile"}), 500