# SSO Backend Integration Guide

## Overview

This document describes the integration between the Regular Backend and the SSO Backend for user authentication and data retrieval. The system allows the Regular Backend to retrieve logged-in user data from the SSO Backend while maintaining a direct connection between the UI and SSO Backend for login/logout operations.

## Architecture

The system consists of three main components:
1. **UI/Frontend** - User interface that communicates with both backends
2. **Regular Backend** - Main application backend (runs on port `13457`)
3. **SSO Backend** - Authentication backend that handles SSO integration (runs on port `13456`)

## Port Configuration

### Local Development Ports

| Service | Port | Configuration File | Notes |
|---------|------|-------------------|-------|
| SSO Backend | 13456 | `shared-resources/sso-backend/config/app_config.py` | Authentication server |
| Regular Backend | 13457 | `DataPipelineHub/backend/config/app_config.py` | Main application server |
| UI/Frontend | 5000 | `AuthContext.tsx`, `config/app_config.py` | Client application |

### Production Configuration

Ports are configured in Helm values:
- SSO Backend port: See `helm/values/sso-values.yaml` (line 13)
- Regular Backend port: Configured in deployment values
- SSO Backend URL: Set via `SSO_BACKEND_HOST` environment variable in `helm/values/global-config.yaml`

## Communication Flow

### Login Flow (Direct to SSO Backend)
```
UI → SSO Backend (port 13456)
```
The UI directly connects to the SSO backend for login and logout operations.

### User Data Retrieval (Via Regular Backend)
```
UI → Regular Backend (port 13457) → SSO Backend (port 13456)
```
The UI queries the Regular Backend, which forwards the request to the SSO Backend to retrieve user information.

## API Endpoints

### SSO Backend Endpoints

Base URL: `http://127.0.0.1:13456` (local) or configured via `SSO_BACKEND_HOST`

| Endpoint | Method | Description | Called By |
|----------|--------|-------------|-----------|
| `/api/auth/login` | GET | Initiates SSO login flow | UI (direct) |
| `/api/auth/logout` | POST | Logs out user session | UI (direct) |
| `/api/auth/callback` | GET | Handles OAuth callback from Keycloak | SSO Provider |
| `/api/auth/user` | GET | Returns current user information | Regular Backend → SSO Backend |
| `/api/auth/refresh` | POST | Refreshes user token | Regular Backend → SSO Backend |
| `/api/protected/user.profile` | GET | Gets user profile information | Regular Backend → SSO Backend |

### Regular Backend Endpoints

Base URL: `http://127.0.0.1:13457` (local)

| Endpoint | Method | Description | Notes |
|----------|--------|-------------|-------|
| `/api/sso/auth/user` | GET | Gets user info (forwards to SSO Backend) | Proxies to SSO Backend |
| `/api/sso/auth/refresh` | POST | Refreshes token (forwards to SSO Backend) | Proxies to SSO Backend |
| `/api/sso/protected/user.profile` | GET | Gets user profile (forwards to SSO Backend) | Proxies to SSO Backend |

## Environment Variables

### SSO Backend Configuration

Located in: `shared-resources/sso-backend/config/app_config.py`

```python
keycloak_base_url: str = "https://auth.stage.redhat.com/auth"
client_id: str = "TAG-001"
client_secret: str = "a0a82b17-e7e7-49c6-ad1c-3d03c79ff4fd"
keycloak_realm: str = "EmployeeIDP"
frontend_url: str = "http://localhost:5000"
port: str = "13456"
```

### Regular Backend Configuration

Located in: `DataPipelineHub/backend/config/app_config.py`

```python
port: str = "13457"
frontend_url: str = "http://localhost:5000"
redirect_url: str = "http://127.0.0.1:13456/api/auth/callback"
```

**SSO Service Configuration** (`DataPipelineHub/backend/services/sso_service.py`):
- `SSO_BACKEND_HOST`: Defaults to `http://127.0.0.1:13456` if not set
- `SSO_SSL_VERIFY`: Set to 'false' to disable SSL verification (default: 'true')

## Key Files and Their Roles

### SSO Backend
- `shared-resources/sso-backend/app.py` - Flask application initialization
- `shared-resources/sso-backend/utils/auth_manager.py` - Authentication manager for Keycloak integration
- `shared-resources/sso-backend/config/app_config.py` - Configuration for SSO backend
- `shared-resources/sso-backend/endpoints/` - API endpoints

### Regular Backend
- `DataPipelineHub/backend/services/sso_service.py` - Service to communicate with SSO backend
- `DataPipelineHub/backend/endpoints/sso.py` - SSO endpoints in regular backend
- `DataPipelineHub/backend/config/app_config.py` - Configuration for regular backend

### UI/Frontend
- `DataPipelineHub/ui/client/src/contexts/AuthContext.tsx` - Authentication context
- `DataPipelineHub/ui/client/src/http/authClient.ts` - HTTP client for SSO backend (port 13456)
- `DataPipelineHub/ui/client/src/http/queryClient.ts` - HTTP client for regular backend (port 13457)

## Nginx Configuration

When deploying, you may need to configure Nginx to route:
- `/api3/*` → SSO Backend (for auth operations)
- `/api1/*` → Regular Backend (for data operations)

Example nginx configuration:
```
location /api3 {
    proxy_pass http://sso-backend:13456;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header Cookie $http_cookie;
}

location /api1 {
    proxy_pass http://regular-backend:13457;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header Cookie $http_cookie;
}
```

## Testing Locally

1. **Start SSO Backend**:
   ```bash
   cd shared-resources/sso-backend
   python app.py
   # Runs on http://127.0.0.1:13456
   ```

2. **Start Regular Backend**:
   ```bash
   cd DataPipelineHub/backend
   python app.py
   # Runs on http://127.0.0.1:13457
   ```

3. **Set Environment Variables** (if needed):
   ```bash
   export SSO_BACKEND_HOST=http://127.0.0.1:13456
   export SSO_SSL_VERIFY=false  # For local development
   ```

4. **Start UI**:
   ```bash
   cd DataPipelineHub/ui
   npm run dev
   # Runs on http://localhost:5000
   ```

## How It Works

1. **Login**: User clicks login → UI redirects to SSO backend `/api/auth/login` → SSO backend redirects to Keycloak → User authenticates → Keycloak redirects to SSO backend callback → SSO backend creates session → Redirects to UI with `?auth=success`

2. **Getting User Data**: UI calls Regular backend `/api/sso/auth/user` → Regular backend SSO service forwards request to SSO backend with cookies → SSO backend returns user info → Regular backend returns to UI

3. **Token Refresh**: UI calls Regular backend `/api/sso/auth/refresh` → Regular backend forwards to SSO backend → SSO backend refreshes token → Returns to UI

## Notes

- Login and logout operations happen **directly** between UI and SSO Backend (not through Regular Backend)
- User data retrieval happens **through** the Regular Backend, which acts as a proxy to the SSO Backend
- The SSO service in the Regular Backend forwards cookies to maintain the session
- Token expiration is checked every 10 minutes and refreshed if needed

