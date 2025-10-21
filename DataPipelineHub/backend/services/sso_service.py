"""
SSO Service
Handles communication between the regular backend and SSO backend
"""
import os
import requests
from flask import request, session
from shared.logger import logger
from config.app_config import AppConfig

config = AppConfig.get_instance()

class SSOService:
    def __init__(self):
        self.sso_backend_url = os.environ.get('SSO_BACKEND_HOST', 'http://127.0.0.1:13456')
        if not self.sso_backend_url.endswith('/'):
            self.sso_backend_url += '/'
    
    def _forward_request(self, method, endpoint, **kwargs):
        """Forward a request to the SSO backend"""
        try:
            # Construct the full URL
            url = f"{self.sso_backend_url}api{endpoint}"
            
            # Prepare headers - forward relevant headers from the original request
            headers = {}
            if 'headers' in kwargs:
                headers.update(kwargs['headers'])
            
            # Forward important headers from the original request
            important_headers = ['User-Agent', 'Accept', 'Accept-Language', 'Accept-Encoding']
            for header in important_headers:
                if header in request.headers:
                    headers[header] = request.headers[header]
            
            # Forward cookies from the original request
            cookie_header = request.headers.get('Cookie', '')
            if cookie_header:
                headers['Cookie'] = cookie_header
            
            # Forward credentials
            kwargs['headers'] = headers
            kwargs['cookies'] = request.cookies
            kwargs['timeout'] = 30  # Add timeout
            
            logger.info(f"Forwarding {method} request to SSO backend: {url}")
            
            # Make the request to SSO backend
            response = requests.request(
                method=method,
                url=url,
                **kwargs
            )
            
            logger.info(f"SSO backend response: {response.status_code}")
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error forwarding request to SSO backend: {str(e)}")
            raise Exception(f"Failed to communicate with SSO backend: {str(e)}")
    
    def forward_auth_request(self, endpoint, method='GET', **kwargs):
        """Forward authentication-related requests to SSO backend"""
        return self._forward_request(method, endpoint, **kwargs)
    
    def get_user_info(self):
        """Get current user information from SSO backend"""
        return self.forward_auth_request('/auth/user')
    
    def login_user(self):
        """Initiate login flow"""
        return self.forward_auth_request('/auth/login')
    
    def logout_user(self):
        """Logout user"""
        return self.forward_auth_request('/auth/logout', method='POST')
    
    def refresh_token(self):
        """Refresh user token"""
        return self.forward_auth_request('/auth/refresh', method='POST')
    
    def get_user_profile(self):
        """Get user profile from protected routes"""
        return self.forward_auth_request('/protected/user.profile')
