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

DATAFLOW_ADDR=$(wait_for_ip unifai-dataflow-server)              
DATAFLOW_PORT=$(wait_for_port unifai-dataflow-server)
DATAFLOW_IP=$(wait_for_service_name unifai-dataflow-server)
              
kubectl delete configmap unifai-dataflow-config
kubectl create configmap unifai-dataflow-config \
  --from-literal=DATAFLOW_ADDR="$DATAFLOW_ADDR" \
  --from-literal=DATAFLOW_PORT="$DATAFLOW_PORT" \
  --from-literal=DATAFLOW_IP="$DATAFLOW_IP" \
  --dry-run=client -o yaml | kubectl apply -f -
