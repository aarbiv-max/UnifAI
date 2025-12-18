"""
Decorators for Flask endpoints.
"""
from functools import wraps
from flask import jsonify, request, current_app
from config.app_config import AppConfig


def require_admin_access(f):
    """
    Decorator to require admin access for an endpoint.
    
    Checks if the user_id (from query params) is in admin_allowed_users list.
    If admin_allowed_users is empty, denies all access (Analytics is disabled).
    
    The decorator extracts user_id from:
    - Query parameter: 'userId' or 'user_id'
    - Function kwargs: 'user_id' or 'userId' (if passed by @from_query)
    
    Returns:
        403 Forbidden if admin_allowed_users is empty (Analytics disabled).
        403 Forbidden if user is not in admin_allowed_users list.
        403 Forbidden if user_id is missing.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            config = AppConfig.get_instance()
            admin_allowed_users = config.get("admin_allowed_users", [])
            
            # If admin_allowed_users is empty, deny all access (Analytics is disabled)
            if not admin_allowed_users:
                return jsonify({
                    "error": "Access denied: Analytics is not enabled",
                    "error_type": "FEATURE_DISABLED"
                }), 403
            
            # Try to get user_id from function kwargs first (if passed by @from_query)
            user_id = kwargs.get("user_id") or kwargs.get("userId")
            
            # If not in kwargs, try to get from query parameters
            if not user_id:
                user_id = request.args.get("userId") or request.args.get("user_id")
            
            if not user_id:
                return jsonify({
                    "error": "Access denied: user_id is required",
                    "error_type": "AUTHENTICATION_REQUIRED"
                }), 403
            
            # Check if user is in admin list
            if user_id not in admin_allowed_users:
                return jsonify({
                    "error": "Access denied: insufficient permissions",
                    "error_type": "ACCESS_DENIED"
                }), 403
            
            # User is authorized, proceed with the request
            return f(*args, **kwargs)
            
        except Exception as e:
            return jsonify({
                "error": f"Access control error: {str(e)}",
                "error_type": "ACCESS_CONTROL_ERROR"
            }), 500
    
    return decorated_function

