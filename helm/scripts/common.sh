#!/bin/bash
# Shared functions for postsync hooks

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}


wait_for_port() {
  local svc=$1
  for i in {1..60}; do
    port=$(kubectl get svc "$svc" -o jsonpath='{.spec.ports[0].port}' 2>/dev/null)
    if [[ -n "$port" ]]; then
      log_info "$port"
      return
    fi
    log_info "Waiting for $svc Port..."
    sleep 10
  done
  log_error "Timed out waiting for $svc"
  exit 1
}

wait_for_service_name() {
  local svc=$1
  local ip=""
  for i in {1..60}; do
    ip=$(kubectl get svc "$svc" -o jsonpath='{.metadata.name}' 2>/dev/null)
    if [[ -n "$ip" ]]; then
      log_info "$ip"
      return
    fi
    log_info "Waiting for $svc ClusterIP IP..."
    sleep 10
  done
  log_error "Timed out waiting for $svc"
  exit 1
}

wait_for_ip() {
  local svc=$1
  local ip=""
  for i in {1..60}; do
    ip=$(kubectl get svc "$svc" -o jsonpath='{.spec.clusterIPs[0]}' 2>/dev/null)
    if [[ -n "$ip" ]]; then
      log_info "$ip"
      return
    fi
    log_info "Waiting for $svc ClusterIP IP..."
    sleep 10
  done
  log_error "Timed out waiting for $svc"
  exit 1
}

# Optional: Helper to reduce configmap boilerplate
create_or_update_configmap() {
  local cm_name=$1
  shift
  kubectl delete configmap "$cm_name" 2>/dev/null
  kubectl create configmap "$cm_name" "$@" \
    --dry-run=client -o yaml | kubectl apply -f -
}