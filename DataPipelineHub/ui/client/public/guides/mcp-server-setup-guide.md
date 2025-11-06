# Google Workspace MCP Server

This guide explains how to set up and run the **Google Workspace MCP Server** locally with OAuth authentication using Docker.

---

## ✅ 1. Create a Google Cloud Project

1. Go to: https://console.cloud.google.com/
2. Click **Create Project**
3. Note your:
   - **Project Name**
   - **Project Location** (default is fine)

---

## 🔑 2. Configure OAuth Credentials

1. Go to: **APIs & Services → Credentials**
2. Click: **Create Credentials → OAuth Client ID**
3. Select **Web Application**
4. Set the following:

| Field | Value |
|--------|--------|
| Authorized JavaScript origins | `http://localhost:8000` |
| Authorized redirect URIs | `http://localhost:8000/oauth2callback` |

5. Click **Create**
6. **Download the OAuth JSON file**

---

### 📌 Enable Required Google APIs

Navigate to: **APIs & Services → Library**

Enable the following APIs:

- Google Calendar API
- Google Drive API
- Gmail API
- Google Docs API
- Google Sheets API
- Google Slides API
- Google Forms API
- Google Tasks API
- Google Chat API
- Google Search API

---

## 💻 3. Clone the Repository & Configure Environment

### Prerequisites

Ensure the following are installed:

- Docker
- Docker Compose

Clone the repository:

```bash
git clone https://github.com/taylorwilsdon/google_workspace_mcp.git
cd google_workspace_mcp
```

Create a `.env` file and add:

```env
GOOGLE_OAUTH_CLIENT_ID=your-client-id
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret
USER_GOOGLE_EMAIL="your-email@example.com"
```

> 🔐 **Do not commit `.env` or OAuth JSON files to Git.**

---

## 🚀 4. Build & Run the Server

Start the server:

```bash
docker-compose up
```

The MCP server will now be available locally.

---

## 🔗 5. Connect UniFAI to Your Local MCP Server

To integrate **UniFAI** with your running Google Workspace MCP:

1. Open **UniFAI**
2. Navigate to:  
   **Agentic Inventory → Providers → MCP Provider**
3. Click **Create New**
4. Fill in the following fields:

| Field | Value |
|--------|--------|
| Name | `google-workspace-mcp` |
| SSE Endpoint | `http://<laptop_public_ip_address>:8000/mcp` |

> 🌍 Replace `<laptop_public_ip_address>` with your machine's public IP  

5. Once validation completes, click **Save**

---

