"""Dev-only fake OAuth client that replaces Keycloak for local development."""

import uuid
from datetime import datetime, timedelta

from flask import redirect


class DevOAuthClient:
    """Drop-in replacement for the Authlib OAuth client in local auth mode.

    Returns hardcoded dev-user responses so the full auth flow
    (login -> redirect -> callback -> session) runs through real code paths.
    """

    def authorize_redirect(self, redirect_uri, **kwargs):
        state = kwargs.get("state", "")
        return redirect(f"{redirect_uri}?code=dev-code&state={state}")

    def authorize_access_token(self, **kwargs):
        return {
            "access_token": str(uuid.uuid4()),
            "refresh_token": "dev-refresh-token",
            "expires_at": (datetime.now() + timedelta(hours=10)).timestamp(),
        }

    def userinfo(self, **kwargs):
        return {
            "preferred_username": "dev-user",
            "email": "dev@local.dev",
            "name": "Dev User",
            "sub": "local:dev-user",
        }

    def fetch_access_token(self, **kwargs):
        return self.authorize_access_token()
