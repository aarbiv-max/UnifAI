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
    echo "Waiting for $svc LoadBalancer IP..."
    sleep 10
  done
  echo "pending"
}

# wait_for_ext_ip() {
#   local svc=$1
#   local ip=""
#   for i in {1..60}; do
#     ip=$(kubectl get svc "$svc" -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
#     if [[ -n "$ip" ]]; then
#       echo "$ip"
#       return
#     fi
#     echo "Waiting for $svc LoadBalancer IP..."
#     sleep 10
#   done
#   echo "pending"
# }

# MONGODB_ADDR=$(wait_for_ext_ip mongodb)
# QDRANT_ADDR=$(wait_for_ext_ip qdrant)
# RABBITMQ_ADDR=$(wait_for_ext_ip rabbitmq)

MONGO_PORT=$(wait_for_port mongodb)
RMQ_PORT=$(wait_for_port rabbitmq)

MONGO_IP=$(wait_for_service_name mongodb)
RMQ_IP=$(wait_for_service_name rabbitmq)

#If adding ext ips, add them here and add this to the new configmap below.
  # --from-literal=MONGO_EXT_ADDR="$MONGODB_ADDR" \
  # --from-literal=RABBITMQ_EXT_ADDR="$RABBITMQ_ADDR" \
  # --from-literal=QDRANT_EXT_ADDR="$QDRANT_ADDR" \


kubectl delete configmap shared-config
kubectl create configmap shared-config \
  --from-literal=MONGODB_PORT="$MONGO_PORT" \
  --from-literal=RABBITMQ_PORT="$RMQ_PORT" \
  --from-literal=MONGODB_IP="$MONGO_IP" \
  --from-literal=RABBITMQ_IP="$RMQ_IP" \
  --dry-run=client -o yaml | kubectl apply -f -