"""
SSO Endpoints
Only handles user data retrieval from SSO backend - authentication flow remains the same
"""
import os
import requests
from flask import Blueprint, jsonify, request
from shared.logger import logger

sso_bp = Blueprint('sso', __name__)

# Get SSO backend URL from environment
SSO_BACKEND_URL = os.environ.get('SSO_BACKEND_HOST', 'http://127.0.0.1:13456')

@sso_bp.route('/auth/user')
def get_current_user():
    """Get current user information - proxy to SSO backend"""
    try:
        # Forward the request to SSO backend
        url = f"{SSO_BACKEND_URL}/api/auth/user"
        
        # Forward cookies and headers from the original request
        headers = {
            'Cookie': request.headers.get('Cookie', ''),
            'User-Agent': request.headers.get('User-Agent', ''),
            'Accept': request.headers.get('Accept', 'application/json'),
        }
        
        logger.info(f"Forwarding user request to SSO backend: {url}")
        
        response = requests.get(
            url,
            headers=headers,
            cookies=request.cookies,
            timeout=10
        )
        
        logger.info(f"SSO backend response: {response.status_code}")
        
        # Return the response from SSO backend
        return response.json(), response.status_code
        
    except Exception as e:
        logger.error(f"Error getting user from SSO backend: {str(e)}")
        return jsonify({"error": "Failed to get user information"}), 500

@sso_bp.route('/auth/refresh', methods=['POST'])
def refresh_token():
    """Refresh access token - proxy to SSO backend"""
    try:
        url = f"{SSO_BACKEND_URL}/api/auth/refresh"
        
        # Forward cookies and headers
        headers = {
            'Cookie': request.headers.get('Cookie', ''),
            'User-Agent': request.headers.get('User-Agent', ''),
            'Accept': request.headers.get('Accept', 'application/json'),
            'Content-Type': request.headers.get('Content-Type', 'application/json'),
        }
        
        logger.info(f"Forwarding refresh request to SSO backend: {url}")
        
        response = requests.post(
            url,
            headers=headers,
            cookies=request.cookies,
            timeout=10
        )
        
        logger.info(f"SSO backend refresh response: {response.status_code}")
        
        return response.json(), response.status_code
        
    except Exception as e:
        logger.error(f"Error refreshing token from SSO backend: {str(e)}")
        return jsonify({"error": "Token refresh failed"}), 500

@sso_bp.route('/protected/user.profile')
def get_user_profile():
    """Get user profile - proxy to SSO backend"""
    try:
        url = f"{SSO_BACKEND_URL}/api/protected/user.profile"
        
        # Forward cookies and headers
        headers = {
            'Cookie': request.headers.get('Cookie', ''),
            'User-Agent': request.headers.get('User-Agent', ''),
            'Accept': request.headers.get('Accept', 'application/json'),
        }
        
        logger.info(f"Forwarding profile request to SSO backend: {url}")
        
        response = requests.get(
            url,
            headers=headers,
            cookies=request.cookies,
            timeout=10
        )
        
        logger.info(f"SSO backend profile response: {response.status_code}")
        
        return response.json(), response.status_code
        
    except Exception as e:
        logger.error(f"Error getting user profile from SSO backend: {str(e)}")
        return jsonify({"error": "Failed to get user profile"}), 500