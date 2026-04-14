#!/bin/bash

# =============================================================================
# UnifAI Development Environment
#
# Two modes:
#   Full-stack (default)  — tmux session with all 7 services + workers
#   Single-service        — one service in the foreground (--service flag)
#
# Usage:
#   ./local-development/start-unifai-dev.sh                       # full-stack
#   ./local-development/start-unifai-dev.sh --service backend     # single service
#   ./local-development/start-unifai-dev.sh --service rag --setup-venv
#   ./local-development/start-unifai-dev.sh --setup-venv          # all venvs, then full-stack
#   ./local-development/start-unifai-dev.sh --destroy
# =============================================================================

SESSION_NAME="unifai-dev"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

LOG_FILE="/tmp/unifai-dev-$(date +%Y%m%d-%H%M%S).log"
echo "Logging errors to: $LOG_FILE"
: > "$LOG_FILE"

if [ ! -d "$ROOT_DIR/rag" ] || [ ! -d "$ROOT_DIR/ui" ] || [ ! -d "$ROOT_DIR/global_utils" ]; then
    echo "❌ Cannot find UnifAI repo structure. Expected to find rag/, ui/, global_utils/ in: $ROOT_DIR"
    echo "   Run this script from the repo root: ./local-development/start-unifai-dev.sh"
    exit 1
fi

# ── Parse flags ──────────────────────────────────────────────────────────────

SERVICE=""
SETUP_VENV=false
SKIP_PATCH=false
FORCE_ENV=false
DESTROY=false

while [ $# -gt 0 ]; do
    case "$1" in
        --destroy|--destory)
            DESTROY=true; shift ;;
        --service)
            shift
            if [ $# -eq 0 ]; then
                echo "❌ --service requires a service name."
                echo "   Services: backend | rag | multi-agent | sso | ui | celery-worker | temporal-worker"
                exit 1
            fi
            SERVICE="$1"; shift ;;
        --setup-venv)
            SETUP_VENV=true; shift ;;
        --no-patch)
            SKIP_PATCH=true; shift ;;
        --force-env)
            FORCE_ENV=true; shift ;;
        -h|--help)
            echo "Usage: start-unifai-dev.sh [flags]"
            echo ""
            echo "Modes:"
            echo "  (no flags)              Full-stack: all services in a tmux session"
            echo "  --service <name>        Single-service: run one service in the foreground"
            echo "  --destroy               Destroy the tmux session"
            echo ""
            echo "Services (for --service):"
            echo "  backend          Flask backend (port 8005)"
            echo "  rag              RAG service (port 13457)"
            echo "  multi-agent      Multi-Agent API (port 8002)"
            echo "  sso              SSO Backend (port 13456)"
            echo "  ui               Vite UI dev server (port 5000)"
            echo "  celery-worker    Celery worker for RAG pipelines"
            echo "  temporal-worker  Temporal worker for agent workflows"
            echo ""
            echo "Flags:"
            echo "  --setup-venv     Create virtual environment(s) before starting"
            echo "                   With --service: creates venv for that service only"
            echo "                   Without --service: creates venvs for all services"
            echo "  --force-env      Regenerate .env files even if they already exist"
            echo "  --no-patch       Skip apply-local-dev-changes.py entirely (env + source patches)"
            exit 0
            ;;
        -*)
            echo "❌ Unknown flag: $1"
            exit 1
            ;;
        *)
            echo "❌ Unknown argument: $1"
            echo "   Use --service <name> for single-service mode."
            exit 1
            ;;
    esac
done

# ── Python detection ─────────────────────────────────────────────────────────
# Override with: export UNIFAI_PYTHON=python3.XX

if [ -n "$UNIFAI_PYTHON" ]; then
    if ! command -v "$UNIFAI_PYTHON" &> /dev/null; then
        echo "❌ UNIFAI_PYTHON is set to '$UNIFAI_PYTHON' but that command was not found."
        exit 1
    fi
    PYTHON="$UNIFAI_PYTHON"
else
    PYTHON=""
    for candidate in python3.11 python3.12 python3.13 python3; do
        if command -v "$candidate" &> /dev/null; then
            PYTHON="$candidate"
            break
        fi
    done

    if [ -z "$PYTHON" ]; then
        echo "❌ No suitable Python (3.11–3.13) found. Install Python 3.11–3.13 or set UNIFAI_PYTHON."
        exit 1
    fi
fi

PYTHON_VERSION=$($PYTHON --version 2>&1 | awk '{print $2}')
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f1,2)

if awk "BEGIN{exit !($PYTHON_MINOR < 3.11)}"; then
    echo "❌ Python $PYTHON_VERSION is too old (3.11+ required). Found: $PYTHON"
    exit 1
fi

if awk "BEGIN{exit !($PYTHON_MINOR > 3.13)}"; then
    echo "❌ Python $PYTHON_VERSION is too new (max 3.13 — PyO3 does not support 3.14+). Found: $PYTHON"
    echo "   Install Python 3.11–3.13 or set UNIFAI_PYTHON to a supported version."
    exit 1
fi

echo "Using Python: $PYTHON ($PYTHON_VERSION)"

# ── Handle --destroy ─────────────────────────────────────────────────────────

if [ "$DESTROY" = true ]; then
    echo "Destroying tmux session '$SESSION_NAME'..."
    tmux kill-session -t $SESSION_NAME 2>>"$LOG_FILE"
    if [ $? -eq 0 ]; then
        echo "Session '$SESSION_NAME' destroyed successfully."
    else
        echo "No session named '$SESSION_NAME' found."
    fi
    exit 0
fi

# ── Handle --setup-venv ──────────────────────────────────────────────────────

if [ "$SETUP_VENV" = true ]; then
    if [ -n "$SERVICE" ]; then
        echo "📦 Setting up virtual environment for: $SERVICE"
        (cd "$ROOT_DIR" && $PYTHON "$SCRIPT_DIR/apply-local-dev-changes.py" --setup-venv-only --service "$SERVICE")
    else
        echo "📦 Setting up virtual environments for all services…"
        (cd "$ROOT_DIR" && $PYTHON "$SCRIPT_DIR/apply-local-dev-changes.py" --setup-venv-only)
    fi
    if [ $? -ne 0 ]; then
        echo "❌ Virtual environment setup failed."
        exit 1
    fi
fi

# ── Apply local dev changes (env + source patches for all services) ──────────────────────────

if [ "$SKIP_PATCH" = false ]; then
    echo "Applying local dev changes..."
    APPLY_ARGS=""
    if [ "$FORCE_ENV" = true ]; then
        APPLY_ARGS="--force-env"
    fi
    (cd "$ROOT_DIR" && $PYTHON "$SCRIPT_DIR/apply-local-dev-changes.py" $APPLY_ARGS)
    if [ $? -ne 0 ]; then
        echo "Warning: apply-local-dev-changes.py failed. Continuing anyway..."
    fi
fi

# =============================================================================
# Branch: single-service mode vs full-stack tmux mode
# =============================================================================

if [ -n "$SERVICE" ]; then

    # ─────────────────────────────────────────────────────────────────────────
    # SINGLE-SERVICE MODE
    # Starts only the containers the service needs, then runs it in foreground.
    # ─────────────────────────────────────────────────────────────────────────

    # Start only the needed infrastructure containers
    "$SCRIPT_DIR/start-infra.sh" --for "$SERVICE"

    sleep 1

    # Kill any existing process on the service port
    kill_port() {
        local port="$1"
        local pids
        pids=$(lsof -ti ":$port" 2>>"$LOG_FILE" || true)
        if [ -n "$pids" ]; then
            echo "⚠  Killing existing process on port $port (PIDs: $pids)"
            echo "$pids" | xargs kill -9 2>>"$LOG_FILE" || true
        fi
    }

    # Verify venv exists before launching
    check_venv() {
        local venv_path="$1"
        if [ ! -f "$venv_path/bin/activate" ]; then
            echo "❌ No venv found at $venv_path/"
            echo "   Run: $0 --service $SERVICE --setup-venv"
            echo "   Or create it manually — see LOCAL_DEV_GUIDE.md Section 3."
            exit 1
        fi
    }

    # Verify the venv's Python matches the detected version
    check_venv_python() {
        local venv_path="$1"
        local venv_ver
        venv_ver=$("$venv_path/bin/python" --version 2>&1 | awk '{print $2}')
        local venv_minor
        venv_minor=$(echo "$venv_ver" | cut -d. -f1,2)

        if [ "$venv_minor" != "$PYTHON_MINOR" ]; then
            echo "❌ Python version mismatch!"
            echo "   Detected interpreter: $PYTHON ($PYTHON_VERSION)"
            echo "   Venv Python:          $venv_path/bin/python ($venv_ver)"
            echo ""
            echo "   Recreate the venv: $0 --service $SERVICE --setup-venv"
            echo "   Or set UNIFAI_PYTHON to match: export UNIFAI_PYTHON=python$venv_minor"
            exit 1
        fi

        if awk "BEGIN{exit !($venv_minor > 3.13)}"; then
            echo "❌ Venv Python $venv_ver is too new (max 3.13 — PyO3 does not support 3.14+)."
            echo "   Recreate the venv: $0 --service $SERVICE --setup-venv"
            exit 1
        fi
    }

    echo ""
    echo "🚀 Starting $SERVICE …"
    echo "   Press Ctrl+C to stop."
    echo ""

    case "$SERVICE" in
        backend)
            kill_port 8005
            check_venv "$ROOT_DIR/backend/venv"
            check_venv_python "$ROOT_DIR/backend/venv"
            cd "$ROOT_DIR/backend"
            source venv/bin/activate
            set -a && source .env 2>>"$LOG_FILE"; set +a
            exec $PYTHON -m run.dev
            ;;

        rag)
            kill_port 13457
            check_venv "$ROOT_DIR/rag/venv"
            check_venv_python "$ROOT_DIR/rag/venv"
            cd "$ROOT_DIR/rag"
            source venv/bin/activate
            set -a && source .env 2>>"$LOG_FILE"; set +a
            exec $PYTHON -m bootstrap.flask_app
            ;;

        multi-agent)
            kill_port 8002
            check_venv "$ROOT_DIR/multi-agent/venv"
            check_venv_python "$ROOT_DIR/multi-agent/venv"
            cd "$ROOT_DIR/multi-agent"
            source venv/bin/activate
            export HOSTNAME=0.0.0.0
            exec mas api dev
            ;;

        sso)
            kill_port 13456
            check_venv "$ROOT_DIR/shared-resources/sso-backend/venv"
            check_venv_python "$ROOT_DIR/shared-resources/sso-backend/venv"
            cd "$ROOT_DIR/shared-resources/sso-backend"
            source venv/bin/activate
            set -a && source .env 2>>"$LOG_FILE"; set +a
            exec $PYTHON app.py
            ;;

        ui)
            kill_port 5000
            cd "$ROOT_DIR/ui"
            set -a
            source .env.local 2>>"$LOG_FILE" || true
            set +a
            exec npm start
            ;;

        celery-worker)
            check_venv "$ROOT_DIR/rag/venv"
            check_venv_python "$ROOT_DIR/rag/venv"
            cd "$ROOT_DIR/rag"
            source venv/bin/activate
            set -a && source .env 2>>"$LOG_FILE"; set +a
            exec celery -A infrastructure.celery.app worker \
                -Q document_queue,slack_queue \
                -l info
            ;;

        temporal-worker)
            check_venv "$ROOT_DIR/multi-agent/venv"
            check_venv_python "$ROOT_DIR/multi-agent/venv"
            cd "$ROOT_DIR/multi-agent"
            source venv/bin/activate
            exec mas temporal-worker --threads 20
            ;;

        *)
            echo "❌ Unknown service: $SERVICE"
            echo "   Services: backend | rag | multi-agent | sso | ui | celery-worker | temporal-worker"
            exit 1
            ;;
    esac

else

    # ─────────────────────────────────────────────────────────────────────────
    # FULL-STACK TMUX MODE (original behavior)
    # Starts all containers and all services in a tmux session.
    # ─────────────────────────────────────────────────────────────────────────

    # Determine container runtime (podman or docker)
    CONTAINER_CMD=""
    if command -v podman &> /dev/null; then
        if ! podman info &>> "$LOG_FILE"; then
            echo "Podman is not connected. Attempting to start Podman machine..."
            if podman machine list --format '{{.Name}}\t{{.Running}}' | grep -q "true"; then
                echo "Podman machine is listed but not connected. Trying to reconnect..."
            else
                if podman machine list --format '{{.Name}}' | grep -q "."; then
                    echo "Starting Podman machine..."
                    podman machine start 2>>"$LOG_FILE" || {
                        echo "Warning: Could not start Podman machine automatically."
                        echo "Please run 'podman machine start' manually, or use Docker instead."
                        echo "Skipping container checks..."
                        CONTAINER_CMD=""
                    }
                else
                    echo "Warning: No Podman machine found. Please run 'podman machine init' and 'podman machine start'"
                    echo "Or install Docker as an alternative."
                    echo "Skipping container checks..."
                    CONTAINER_CMD=""
                fi
            fi
        fi

        if podman info &>> "$LOG_FILE"; then
            CONTAINER_CMD="podman"
        fi
    fi

    if [ -z "$CONTAINER_CMD" ] && command -v docker &> /dev/null; then
        if docker info &>> "$LOG_FILE"; then
            CONTAINER_CMD="docker"
            echo "Using Docker instead of Podman."
        fi
    fi

    ensure_container() {
        local name="$1"
        local label="$2"
        shift 2
        local run_args=("$@")

        echo "Checking $label container..."
        if $CONTAINER_CMD ps --format '{{.Names}}' 2>>"$LOG_FILE" | grep -qx "$name"; then
            echo "$label is already running."
            return
        fi

        echo "$label not running. Starting..."
        if $CONTAINER_CMD ps -a --format '{{.Names}}' 2>>"$LOG_FILE" | grep -qx "$name"; then
            $CONTAINER_CMD start "$name" 2>>"$LOG_FILE" || echo "Warning: Failed to start $label container."
        else
            echo "$label container doesn't exist. Creating and starting..."
            $CONTAINER_CMD run -d --name "$name" "${run_args[@]}" 2>>"$LOG_FILE" || echo "Warning: Failed to create $label container."
        fi
    }

    # Pre-flight: verify all venvs exist and match the detected Python version
    verify_venv() {
        local label="$1" venv_path="$2"
        if [ ! -f "$venv_path/bin/python" ]; then
            echo "❌ No venv found for $label at $venv_path/"
            echo "   Run: $0 --setup-venv"
            exit 1
        fi
        local venv_ver
        venv_ver=$("$venv_path/bin/python" --version 2>&1 | awk '{print $2}')
        local venv_minor
        venv_minor=$(echo "$venv_ver" | cut -d. -f1,2)
        if [ "$venv_minor" != "$PYTHON_MINOR" ]; then
            echo "❌ Python version mismatch for $label!"
            echo "   Script detected: $PYTHON ($PYTHON_VERSION)"
            echo "   Venv has:        $venv_path/bin/python ($venv_ver)"
            echo ""
            echo "   Recreate all venvs: $0 --setup-venv"
            echo "   Or set UNIFAI_PYTHON to match: export UNIFAI_PYTHON=python$venv_minor"
            exit 1
        fi
    }

    verify_venv "RAG"         "$ROOT_DIR/rag/venv"
    verify_venv "Backend"     "$ROOT_DIR/backend/venv"
    verify_venv "Multi-Agent" "$ROOT_DIR/multi-agent/venv"
    verify_venv "SSO Backend" "$ROOT_DIR/shared-resources/sso-backend/venv"

    if [ -n "$CONTAINER_CMD" ]; then
        ensure_container "mongo"    "MongoDB"   -p 27017:27017 mongo:latest
        ensure_container "rabbitmq" "RabbitMQ"  -p 5672:5672 -p 15672:15672 rabbitmq:3-management
        ensure_container "qdrant"   "Qdrant"    -p 6333:6333 -p 6334:6334 qdrant/qdrant:latest
        ensure_container "redis"    "Redis"     -p 6379:6379 redis:latest
        ensure_container "temporal" "Temporal"  -p 7233:7233 -p 8233:8233 temporalio/temporal:latest server start-dev --ip 0.0.0.0 --ui-port 8233
    else
        echo "Warning: No container runtime available (Podman or Docker). Skipping container startup."
    fi

    sleep 2

    echo "Killing any processes on required ports..."
    PORTS="13457 5000 13456 8002 8005"
    for port in $PORTS; do
        pids=$(lsof -ti :$port 2>>"$LOG_FILE")
        if [ -n "$pids" ]; then
            echo "  Killing processes on port $port (PIDs: $pids)"
            echo "$pids" | xargs kill -9 2>>"$LOG_FILE"
        fi
    done

    tmux kill-session -t $SESSION_NAME 2>>"$LOG_FILE"

    # =========================================================================
    # Window 0: "services" — main app services (5 panes)
    #
    #   ┌─────────────────┬─────────────────┐
    #   │  RAG Service     │  SSO Backend    │
    #   ├─────────────────┼─────────────────┤
    #   │  Multi-Agent API │  UI (Vite)      │
    #   ├─────────────────┴─────────────────┤
    #   │  Backend Service                   │
    #   └───────────────────────────────────┘
    # =========================================================================
    tmux new-session -d -s $SESSION_NAME -c "$ROOT_DIR"
    tmux rename-window -t $SESSION_NAME:0 'services'

    # Capture the initial pane ID
    RAG_PANE=$(tmux display-message -t $SESSION_NAME:0 -p '#{pane_id}')

    # RAG Service (top-left)
    tmux send-keys -t "$RAG_PANE" "cd $ROOT_DIR/rag && source venv/bin/activate && set -a && source .env 2>/dev/null; set +a && $PYTHON -m bootstrap.flask_app" C-m

    # SSO Backend (top-right — split RAG horizontally)
    tmux split-window -h -t "$RAG_PANE" -c "$ROOT_DIR"
    SSO_PANE=$(tmux display-message -t $SESSION_NAME:0 -p '#{pane_id}')
    tmux send-keys -t "$SSO_PANE" "cd $ROOT_DIR/shared-resources/sso-backend && source venv/bin/activate && set -a && source .env 2>/dev/null; set +a && $PYTHON app.py" C-m

    # Multi-Agent API (bottom-left — split RAG vertically)
    tmux split-window -v -t "$RAG_PANE" -c "$ROOT_DIR"
    MAS_PANE=$(tmux display-message -t $SESSION_NAME:0 -p '#{pane_id}')
    tmux send-keys -t "$MAS_PANE" "cd $ROOT_DIR/multi-agent && source venv/bin/activate && HOSTNAME=0.0.0.0 mas api dev" C-m

    # UI (bottom-right — split SSO vertically)
    tmux split-window -v -t "$SSO_PANE" -c "$ROOT_DIR"
    UI_PANE=$(tmux display-message -t $SESSION_NAME:0 -p '#{pane_id}')
    tmux send-keys -t "$UI_PANE" "cd $ROOT_DIR/ui && set -a && source .env.local 2>/dev/null; set +a && npm start" C-m

    # Backend Service (bottom full-width — split MAS vertically)
    tmux split-window -v -t "$MAS_PANE" -c "$ROOT_DIR"
    BACKEND_PANE=$(tmux display-message -t $SESSION_NAME:0 -p '#{pane_id}')
    tmux send-keys -t "$BACKEND_PANE" "cd $ROOT_DIR/backend && source venv/bin/activate && set -a && source .env 2>/dev/null; set +a && $PYTHON -m run.dev" C-m

    # =========================================================================
    # Window 1: "workers" — background workers (2 panes side by side)
    # =========================================================================
    tmux new-window -t $SESSION_NAME -n 'workers' -c "$ROOT_DIR"

    # Celery Worker (left)
    CELERY_PANE=$(tmux display-message -t $SESSION_NAME:1 -p '#{pane_id}')
    tmux send-keys -t "$CELERY_PANE" "cd $ROOT_DIR/rag && source venv/bin/activate && celery -A infrastructure.celery.app worker -Q document_queue,slack_queue -l info" C-m

    # Temporal Worker (right — split Celery horizontally)
    tmux split-window -h -t "$CELERY_PANE" -c "$ROOT_DIR"
    TEMPORAL_PANE=$(tmux display-message -t $SESSION_NAME:1 -p '#{pane_id}')
    tmux send-keys -t "$TEMPORAL_PANE" "cd $ROOT_DIR/multi-agent && source venv/bin/activate && mas temporal-worker --threads 20" C-m

    # Focus on first window, first pane
    tmux select-window -t $SESSION_NAME:0
    tmux select-pane -t "$RAG_PANE"

    echo ""
    echo "╔══════════════════════════════════════════════════════════════════════╗"
    echo "║                    UnifAI Development Environment                    ║"
    echo "╠══════════════════════════════════════════════════════════════════════╣"
    echo "║                                                                      ║"
    echo "║  Services starting in tmux session: $SESSION_NAME                   ║"
    echo "║                                                                      ║"
    echo "║  Containers:                                                         ║"
    echo "║    MongoDB    (port 27017)    Temporal  (port 7233, UI: 8233)       ║"
    echo "║    RabbitMQ   (port 5672)     Redis     (port 6379)                 ║"
    echo "║    Qdrant     (port 6333)                                            ║"
    echo "║                                                                      ║"
    echo "║  Window 0 - services:                                                ║"
    echo "║    [0] RAG Service       (port 13457)                               ║"
    echo "║    [1] SSO Backend       (port 13456)                               ║"
    echo "║    [2] Multi-Agent API   (port 8002)                                ║"
    echo "║    [3] UI                (port 5000)                                ║"
    echo "║    [4] Backend Service   (port 8005)                                ║"
    echo "║                                                                      ║"
    echo "║  Window 1 - workers:                                                 ║"
    echo "║    [0] Celery Worker     (RabbitMQ queues)                          ║"
    echo "║    [1] Temporal Worker   (task queue: graph-engine)                 ║"
    echo "║                                                                      ║"
    echo "║  Commands:                                                           ║"
    echo "║    Attach:   tmux attach -t $SESSION_NAME                           ║"
    echo "║    Switch:   Ctrl-b n (next window) / Ctrl-b p (prev window)       ║"
    echo "║    Destroy:  $0 --destroy                                           ║"
    echo "║    Logs:     $LOG_FILE"
    echo "║                                                                      ║"
    echo "╚══════════════════════════════════════════════════════════════════════╝"
    echo ""

    tmux attach-session -t $SESSION_NAME

fi
