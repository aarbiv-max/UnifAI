#!/bin/bash

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_error() {
    echo -e "${RED}❌ ERROR: $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# Function to display usage
usage() {
    cat << EOF
Usage: $0 --client_id <CLIENT_ID> --client_secret <CLIENT_SECRET> --user_email <EMAIL>

Required arguments:
  --client_id         Google OAuth Client ID
  --client_secret     Google OAuth Client Secret
  --user_email        User's Google email address

Example:
  $0 --client_id "123456.apps.googleusercontent.com" \\
     --client_secret "GOCSPX-abcdef123456" \\
     --user_email "user@example.com"

EOF
    exit 1
}

# Initialize variables
CLIENT_ID=""
CLIENT_SECRET=""
USER_EMAIL=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --client_id)
            CLIENT_ID="$2"
            shift 2
            ;;
        --client_secret)
            CLIENT_SECRET="$2"
            shift 2
            ;;
        --user_email)
            USER_EMAIL="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            print_error "Unknown argument: $1"
            usage
            ;;
    esac
done

# Validate that all required arguments are provided
MISSING_ARGS=()

if [ -z "$CLIENT_ID" ]; then
    MISSING_ARGS+=("--client_id")
fi

if [ -z "$CLIENT_SECRET" ]; then
    MISSING_ARGS+=("--client_secret")
fi

if [ -z "$USER_EMAIL" ]; then
    MISSING_ARGS+=("--user_email")
fi

if [ ${#MISSING_ARGS[@]} -gt 0 ]; then
    print_error "Missing required arguments: ${MISSING_ARGS[*]}"
    echo ""
    usage
fi

print_success "All required arguments provided"

# Check if Docker or Podman is installed
CONTAINER_CMD=""

if command -v docker &> /dev/null; then
    CONTAINER_CMD="docker"
    print_success "Docker is installed"
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker Desktop or the Docker service."
        echo ""
        echo "On macOS: Start Docker Desktop application"
        echo "On Linux: Run 'sudo systemctl start docker'"
        exit 1
    fi
    print_success "Docker daemon is running"
    
elif command -v podman &> /dev/null; then
    CONTAINER_CMD="podman"
    print_success "Podman is installed"
    
    # Check if Podman service is accessible
    if ! podman info &> /dev/null; then
        print_error "Podman is not accessible. Please check your Podman installation."
        exit 1
    fi
    print_success "Podman is accessible"
    
else
    print_error "Neither Docker nor Podman is installed. Please install one of them to continue."
    echo ""
    echo "Install Docker: https://docs.docker.com/get-docker/"
    echo "Install Podman: https://podman.io/getting-started/installation"
    exit 1
fi

# Check if docker-compose or podman-compose is installed
COMPOSE_CMD=""

if [ "$CONTAINER_CMD" = "docker" ]; then
    if command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
        print_success "docker-compose is installed"
    elif docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
        print_success "docker compose (plugin) is installed"
    else
        print_error "docker-compose is not installed. Please install it to continue."
        exit 1
    fi
else
    if command -v podman-compose &> /dev/null; then
        COMPOSE_CMD="podman-compose"
        print_success "podman-compose is installed"
    else
        print_error "podman-compose is not installed. Please install it to continue."
        exit 1
    fi
fi

# Define repository details
REPO_URL="https://github.com/taylorwilsdon/google_workspace_mcp.git"
REPO_DIR="google_workspace_mcp"

print_info "Cloning repository from $REPO_URL..."

# Check if directory already exists
if [ -d "$REPO_DIR" ]; then
    print_info "Directory '$REPO_DIR' already exists. Removing it..."
    rm -rf "$REPO_DIR"
fi

# Clone the repository
if git clone "$REPO_URL"; then
    print_success "Repository cloned successfully"
else
    print_error "Failed to clone repository from $REPO_URL"
    exit 1
fi

# Validate that the repository directory exists
if [ ! -d "$REPO_DIR" ]; then
    print_error "Repository directory '$REPO_DIR' does not exist after cloning"
    exit 1
fi

print_success "Repository directory validated"

# Change to repository directory
cd "$REPO_DIR"
print_info "Changed to directory: $(pwd)"

# Create .env file
print_info "Creating .env file..."

cat > .env << EOF
GOOGLE_OAUTH_CLIENT_ID=$CLIENT_ID
GOOGLE_OAUTH_CLIENT_SECRET=$CLIENT_SECRET
USER_GOOGLE_EMAIL="$USER_EMAIL"
EOF

if [ $? -eq 0 ]; then
    print_success ".env file created successfully"
else
    print_error "Failed to create .env file"
    exit 1
fi

# Display .env contents (masked for security)
print_info ".env file contents:"
echo "----------------------------------------"
echo "GOOGLE_OAUTH_CLIENT_ID=${CLIENT_ID:0:10}..."
echo "GOOGLE_OAUTH_CLIENT_SECRET=${CLIENT_SECRET:0:10}..."
echo "USER_GOOGLE_EMAIL=\"$USER_EMAIL\""
echo "----------------------------------------"

# Detect local IP address
print_info "Detecting local IP address..."
LOCAL_IP=""

# Try different methods to get the local IP
if command -v ipconfig &> /dev/null; then
    # macOS method
    LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "")
elif command -v hostname &> /dev/null; then
    # Linux/Unix method
    LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "")
fi

# Fallback: try to get IP from network interfaces
if [ -z "$LOCAL_IP" ]; then
    LOCAL_IP=$(ip route get 1 2>/dev/null | awk '{print $7; exit}' || echo "")
fi

# If still no IP found, use localhost
if [ -z "$LOCAL_IP" ]; then
    LOCAL_IP="localhost"
    print_info "Could not detect local IP, using localhost"
else
    print_success "Detected local IP: $LOCAL_IP"
fi

# Run docker-compose up in detached mode
print_info "Starting Google Workspace MCP Server..."
echo ""

if $COMPOSE_CMD up -d; then
    echo ""
    print_success "🚀 Google Workspace MCP Server is now running in the background!"
    echo ""
    print_info "Server Details:"
    echo "  • SSE Endpoint: http://$LOCAL_IP:8000/mcp"
    echo "  • OAuth Callback: http://$LOCAL_IP:8000/oauth2callback"
    echo ""
    print_info "Useful Commands:"
    echo "  • View logs:        $COMPOSE_CMD logs -f"
    echo "  • Stop server:      $COMPOSE_CMD down"
    echo "  • Restart server:   $COMPOSE_CMD restart"
    echo "  • View status:      $COMPOSE_CMD ps"
    echo ""
else
    print_error "Failed to start the server with $COMPOSE_CMD"
    exit 1
fi


