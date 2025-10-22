"""
SSO Service
Handles communication between the regular backend and SSO backend
"""
import os
import requests
from flask import request
from shared.logger import logger

class SSOService:
    def __init__(self):
        self.sso_backend_url = os.environ.get('SSO_BACKEND_HOST', 'http://127.0.0.1:13456')
    
    def _forward_request(self, method, endpoint):
        """Forward a request to the SSO backend"""
        try:
            url = f"{self.sso_backend_url}/api{endpoint}"
            headers = {
                'Cookie': request.headers.get('Cookie', ''),
                'User-Agent': request.headers.get('User-Agent', ''),
                'Accept': request.headers.get('Accept', 'application/json'),
            }
            response = requests.request(method=method, url=url, headers=headers, cookies=request.cookies, timeout=30)
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Error forwarding request to SSO backend: {str(e)}")
            raise Exception(f"Failed to communicate with SSO backend: {str(e)}")
    
    def forward_auth_request(self, endpoint, method='GET'):
        """Forward authentication-related requests to SSO backend"""
        return self._forward_request(method, endpoint)
    
    def get_user_info(self):
        """Get current user information from SSO backend"""
        return self.forward_auth_request('/auth/user')
    
    def refresh_token(self):
        """Refresh user token"""
        return self.forward_auth_request('/auth/refresh', method='POST')
    
    def get_user_profile(self):
        """Get user profile from protected routes"""
        return self.forward_auth_request('/protected/user.profile')
    
    def get_current_username(self) -> str:
        """
        Get current username from SSO backend.
        
        Returns:
            Username of the current user from SSO backend
        """
        try:
            response = self.get_user_info()
            
            if response.status_code == 200:
                user_data = response.json()
                if user_data.get('authenticated') and user_data.get('user'):
                    username = user_data['user'].get('username', 'default')
                    logger.info(f"Successfully retrieved username from SSO: {username}")
                    return username
                else:
                    raise ValueError("User not authenticated in SSO backend")
            else:
                raise ValueError(f"SSO backend returned status {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to get username from SSO backend: {str(e)}")
            raise e