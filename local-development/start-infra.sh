#!/bin/bash
# =============================================================================
# Start infrastructure containers selectively.
#
# Usage:
#   ./local-development/start-infra.sh                  # start ALL containers
#   ./local-development/start-infra.sh mongo qdrant     # start only these two
#   ./local-development/start-infra.sh --for backend    # start what backend needs
#   ./local-development/start-infra.sh --for rag        # start what rag needs
#   ./local-development/start-infra.sh --status         # show running containers
#   ./local-development/start-infra.sh --stop           # stop all infra containers
#
# Service → infrastructure mapping:
#   backend       → mongo
#   rag           → mongo  rabbitmq  qdrant
#   multi-agent   → mongo  redis     temporal
#   sso           → (none)
#   ui            → (none)
#   celery-worker → mongo  rabbitmq  qdrant
#   temporal-worker → mongo redis    temporal
# =============================================================================

set -euo pipefail

LOG_FILE="${TMPDIR:-/tmp}/start-infra.log"
: > "$LOG_FILE"

# ── Container definitions ────────────────────────────────────────────────────

declare -A CONTAINER_IMAGES
CONTAINER_IMAGES=(
    [mongo]="mongo:latest"
    [rabbitmq]="rabbitmq:3-management"
    [qdrant]="qdrant/qdrant:latest"
    [redis]="redis:latest"
    [temporal]="temporalio/temporal:latest"
)

declare -A CONTAINER_PORTS
CONTAINER_PORTS=(
    [mongo]="-p 27017:27017"
    [rabbitmq]="-p 5672:5672 -p 15672:15672"
    [qdrant]="-p 6333:6333 -p 6334:6334"
    [redis]="-p 6379:6379"
    [temporal]="-p 7233:7233 -p 8233:8233"
)

declare -A CONTAINER_EXTRA_ARGS
CONTAINER_EXTRA_ARGS=(
    [mongo]=""
    [rabbitmq]=""
    [qdrant]=""
    [redis]=""
    [temporal]="server start-dev --ip 0.0.0.0 --ui-port 8233"
)

declare -A CONTAINER_LABELS
CONTAINER_LABELS=(
    [mongo]="MongoDB"
    [rabbitmq]="RabbitMQ"
    [qdrant]="Qdrant"
    [redis]="Redis"
    [temporal]="Temporal"
)

ALL_CONTAINERS=(mongo rabbitmq qdrant redis temporal)

# ── Service → infra mapping ──────────────────────────────────────────────────

declare -A SERVICE_INFRA
SERVICE_INFRA=(
    [backend]="mongo"
    [rag]="mongo rabbitmq qdrant"
    [multi-agent]="mongo redis temporal"
    [sso]=""
    [ui]=""
    [celery-worker]="mongo rabbitmq qdrant"
    [temporal-worker]="mongo redis temporal"
)

# ── Detect container runtime ─────────────────────────────────────────────────

detect_runtime() {
    if command -v podman &> /dev/null; then
        if podman info &> /dev/null 2>&1; then
            echo "podman"
            return
        fi
        # Podman found but not responding — try to start the machine
        echo "Podman is not connected. Attempting to start Podman machine..." >&2
        if podman machine list --format '{{.Name}}' 2>/dev/null | grep -q "."; then
            podman machine start 2>/dev/null && podman info &> /dev/null 2>&1 && {
                echo "podman"
                return
            }
            echo "Warning: Could not start Podman machine automatically." >&2
        else
            echo "Warning: No Podman machine found." >&2
        fi
    fi
    if command -v docker &> /dev/null && docker info &> /dev/null 2>&1; then
        echo "docker"
        return
    fi
    echo ""
}

CONTAINER_CMD="$(detect_runtime)"

if [ -z "$CONTAINER_CMD" ]; then
    echo "❌ No working container runtime found. Install Podman or Docker."
    exit 1
fi

echo "Using container runtime: $CONTAINER_CMD"

# ── Helpers ──────────────────────────────────────────────────────────────────

ensure_container() {
    local name="$1"
    local label="${CONTAINER_LABELS[$name]}"
    local image="${CONTAINER_IMAGES[$name]}"
    local ports="${CONTAINER_PORTS[$name]}"
    local extra="${CONTAINER_EXTRA_ARGS[$name]}"

    if $CONTAINER_CMD ps --format '{{.Names}}' 2>>"$LOG_FILE" | grep -qx "$name"; then
        echo "  ✔ $label is already running."
        return
    fi

    if $CONTAINER_CMD ps -a --format '{{.Names}}' 2>>"$LOG_FILE" | grep -qx "$name"; then
        echo "  ↻ Starting stopped $label container…"
        $CONTAINER_CMD start "$name" 2>>"$LOG_FILE" || {
            echo "  ⚠ Failed to start $label. Check $LOG_FILE for details."
            return 1
        }
    else
        echo "  ⊕ Creating $label container…"
        # shellcheck disable=SC2086
        $CONTAINER_CMD run -d --name "$name" $ports $image $extra 2>>"$LOG_FILE" || {
            echo "  ⚠ Failed to create $label. Check $LOG_FILE for details."
            return 1
        }
    fi
    echo "  ✔ $label started."
}

show_status() {
    echo "Infrastructure container status:"
    for name in "${ALL_CONTAINERS[@]}"; do
        local label="${CONTAINER_LABELS[$name]}"
        if $CONTAINER_CMD ps --format '{{.Names}}' 2>>"$LOG_FILE" | grep -qx "$name"; then
            echo "  ✔ $label ($name) — running"
        elif $CONTAINER_CMD ps -a --format '{{.Names}}' 2>>"$LOG_FILE" | grep -qx "$name"; then
            echo "  ⏹ $label ($name) — stopped"
        else
            echo "  ✖ $label ($name) — not created"
        fi
    done
}

stop_all() {
    echo "Stopping infrastructure containers…"
    for name in "${ALL_CONTAINERS[@]}"; do
        if $CONTAINER_CMD ps --format '{{.Names}}' 2>>"$LOG_FILE" | grep -qx "$name"; then
            $CONTAINER_CMD stop "$name" 2>>"$LOG_FILE"
            echo "  ⏹ ${CONTAINER_LABELS[$name]} stopped."
        fi
    done
}

# ── Parse arguments ──────────────────────────────────────────────────────────

TARGETS=()

if [ $# -eq 0 ]; then
    TARGETS=("${ALL_CONTAINERS[@]}")
else
    while [ $# -gt 0 ]; do
        case "$1" in
            --status)
                show_status
                exit 0
                ;;
            --stop)
                stop_all
                exit 0
                ;;
            --for)
                shift
                if [ $# -eq 0 ]; then
                    echo "❌ --for requires a service name."
                    echo "   Services: ${!SERVICE_INFRA[*]}"
                    exit 1
                fi
                svc="$1"
                if [ -z "${SERVICE_INFRA[$svc]+x}" ]; then
                    echo "❌ Unknown service: $svc"
                    echo "   Services: ${!SERVICE_INFRA[*]}"
                    exit 1
                fi
                infra="${SERVICE_INFRA[$svc]}"
                if [ -z "$infra" ]; then
                    echo "ℹ  Service '$svc' does not need any infrastructure containers."
                    exit 0
                fi
                # shellcheck disable=SC2206
                TARGETS+=($infra)
                shift
                ;;
            -h|--help)
                echo "Usage: start-infra.sh [options] [container …]"
                echo ""
                echo "Options:"
                echo "  --for <service>   Start only containers needed by <service>"
                echo "  --status          Show status of all infra containers"
                echo "  --stop            Stop all infra containers"
                echo ""
                echo "Containers: ${ALL_CONTAINERS[*]}"
                echo "Services:   ${!SERVICE_INFRA[*]}"
                exit 0
                ;;
            *)
                if [ -n "${CONTAINER_IMAGES[$1]+x}" ]; then
                    TARGETS+=("$1")
                else
                    echo "❌ Unknown container: $1"
                    echo "   Containers: ${ALL_CONTAINERS[*]}"
                    exit 1
                fi
                shift
                ;;
        esac
    done
fi

# Deduplicate
UNIQUE_TARGETS=($(echo "${TARGETS[@]}" | tr ' ' '\n' | sort -u))

if [ ${#UNIQUE_TARGETS[@]} -eq 0 ]; then
    echo "Nothing to start."
    exit 0
fi

echo ""
echo "Starting infrastructure: ${UNIQUE_TARGETS[*]}"
echo ""

for name in "${UNIQUE_TARGETS[@]}"; do
    ensure_container "$name"
done

echo ""
echo "✅ Infrastructure ready."
echo "   Logs: $LOG_FILE"
