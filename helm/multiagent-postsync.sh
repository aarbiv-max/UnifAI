#!/bin/bash
set -x  # Print each command
set +e  # Disable immediate exit on error
echo "Starting postsync hook..."

wait_for_port() {
  local svc=$1
  local ip=""
  for i in {1..60}; do
    port=$(kubectl get svc "$svc" -o jsonpath='{.spec.ports[0].port}' 2>/dev/null)
    if [[ -n "$port" ]]; then
      echo "$port"
      return
    fi
    echo "Waiting for $svc Port..."
    sleep 10
  done
  echo "pending"
}

wait_for_service_name() {
  local svc=$1
  local ip=""
  for i in {1..60}; do
    ip=$(kubectl get svc "$svc" -o jsonpath='{.metadata.name}' 2>/dev/null)
    if [[ -n "$ip" ]]; then
      echo "$ip"
      return
    fi
    echo "Waiting for $svc ClusterIP IP..."
    sleep 10
  done
  echo "pending"
}

wait_for_ip() {
  local svc=$1
  local ip=""
  for i in {1..60}; do
    ip=$(kubectl get svc "$svc" -o jsonpath='{.spec.clusterIPs[0]}' 2>/dev/null)
    if [[ -n "$ip" ]]; then
      echo "$ip"
      return
    fi
    echo "Waiting for $svc ClusterIP IP..."
    sleep 10
  done
  echo "pending"
}

MULTIAGENT_ADDR=$(wait_for_ip unifai-multiagent-be)              
MULTIAGENT_PORT=$(wait_for_port unifai-multiagent-be)
MULTIAGENT_IP=$(wait_for_service_name unifai-multiagent-be)

kubectl delete configmap multiagent-config
kubectl create configmap multiagent-config \
  --from-literal=MULTIAGENT_ADDR="$MULTIAGENT_ADDR" \
  --from-literal=MULTIAGENT_PORT="$MULTIAGENT_PORT" \
  --from-literal=MULTIAGENT_IP="$MULTIAGENT_IP" \
  --dry-run=client -o yaml | kubectl apply -f -
