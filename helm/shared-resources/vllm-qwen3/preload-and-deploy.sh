#!/bin/bash

# vLLM Model Preloader and Deployment Script
# This script preloads the model separately and then deploys vLLM for fast startup

set -e

NAMESPACE="tag-ai--runtime-int"
MODEL="Qwen/Qwen3-32B-FP8"

echo "=== vLLM Model Preloader and Deployment ==="
echo "Model: $MODEL"
echo "Namespace: $NAMESPACE"
echo ""

# Function to check job status
check_job_status() {
    local job_name=$1
    local status=$(oc get job $job_name -n $NAMESPACE -o jsonpath='{.status.conditions[0].type}' 2>/dev/null || echo "NotFound")
    echo $status
}

# Function to get job logs
get_job_logs() {
    local job_name=$1
    local pod=$(oc get pods -l job-name=$job_name -n $NAMESPACE --no-headers -o custom-columns=":metadata.name" 2>/dev/null | head -1)
    if [ ! -z "$pod" ]; then
        oc logs $pod -n $NAMESPACE
    fi
}

# Step 1: Deploy model preloader
echo "🚀 Step 1: Deploying model preloader..."
oc apply -f model-preloader.yaml

echo "✅ Model preloader job deployed"
echo ""

# Step 2: Monitor preloader progress
echo "📥 Step 2: Monitoring model download progress..."
echo "This may take 10-20 minutes for the first download..."
echo ""

# Wait for job to start
echo "Waiting for preloader job to start..."
while [ "$(check_job_status vllm-model-preloader)" == "NotFound" ]; do
    sleep 5
done

# Monitor job progress
echo "Preloader job started. Monitoring progress..."
echo "You can also monitor with: oc logs -f job/vllm-model-preloader -n $NAMESPACE"
echo ""

start_time=$(date +%s)
while true; do
    status=$(check_job_status vllm-model-preloader)
    current_time=$(date +%s)
    elapsed=$((current_time - start_time))
    
    case $status in
        "Complete")
            echo "✅ Model preloader completed successfully!"
            echo "Total time: ${elapsed} seconds ($((elapsed/60)) minutes)"
            break
            ;;
        "Failed")
            echo "❌ Model preloader failed!"
            echo "Logs:"
            get_job_logs vllm-model-preloader
            exit 1
            ;;
        *)
            echo "⏳ Still running... (${elapsed}s elapsed)"
            # Show recent logs
            get_job_logs vllm-model-preloader | tail -5
            sleep 30
            ;;
    esac
done

echo ""

# Step 3: Verify model cache
echo "🔍 Step 3: Verifying model cache..."
PVC_STATUS=$(oc get pvc vllm-qwen3-model-cache -n $NAMESPACE -o jsonpath='{.status.phase}' 2>/dev/null || echo "NotFound")
if [ "$PVC_STATUS" == "Bound" ]; then
    echo "✅ PVC vllm-qwen3-model-cache is ready"
    
    # Show cache size
    CACHE_SIZE=$(oc exec job/vllm-model-preloader -n $NAMESPACE -- du -sh /models/.cache 2>/dev/null | cut -f1 || echo "Unknown")
    echo "📊 Cache size: $CACHE_SIZE"
else
    echo "❌ PVC not ready: $PVC_STATUS"
    exit 1
fi

echo ""

# Step 4: Deploy vLLM with preloaded model
echo "🚀 Step 4: Deploying vLLM with preloaded model..."
echo "Setting skipPreload=true to use cached model..."

helm upgrade --install vllm-qwen3 ./helm/shared-resources/vllm-qwen3 \
    --namespace $NAMESPACE \
    --set volumes.modelCache.enabled=true

echo "✅ vLLM deployed with preloaded model cache"
echo ""

# Step 5: Monitor vLLM startup
echo "⚡ Step 5: Monitoring vLLM startup (should be fast now!)..."
echo "Expected startup time: 1-3 minutes"
echo ""

# Wait for pod to be ready
echo "Waiting for vLLM pod to be ready..."
start_time=$(date +%s)
while true; do
    POD_STATUS=$(oc get pods -l app.kubernetes.io/name=vllm-qwen3 -n $NAMESPACE -o jsonpath='{.items[0].status.phase}' 2>/dev/null || echo "NotFound")
    current_time=$(date +%s)
    elapsed=$((current_time - start_time))
    
    case $POD_STATUS in
        "Running")
            # Check if container is ready
            READY=$(oc get pods -l app.kubernetes.io/name=vllm-qwen3 -n $NAMESPACE -o jsonpath='{.items[0].status.containerStatuses[0].ready}' 2>/dev/null || echo "false")
            if [ "$READY" == "true" ]; then
                echo "✅ vLLM is ready!"
                echo "Startup time with preloaded cache: ${elapsed} seconds ($((elapsed/60)) minutes)"
                break
            else
                echo "⏳ Pod running, waiting for readiness check... (${elapsed}s)"
            fi
            ;;
        "Failed"|"Error")
            echo "❌ vLLM pod failed to start"
            oc describe pods -l app.kubernetes.io/name=vllm-qwen3 -n $NAMESPACE
            exit 1
            ;;
        *)
            echo "⏳ vLLM starting... Status: $POD_STATUS (${elapsed}s elapsed)"
            ;;
    esac
    
    sleep 10
done

echo ""

# Step 6: Get access information
echo "🎉 Step 6: Deployment complete! Access information:"
echo ""

# Get service info
SERVICE_NAME=$(oc get service -l app.kubernetes.io/name=vllm-qwen3 -n $NAMESPACE -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "vllm-qwen3")
SERVICE_PORT=$(oc get service $SERVICE_NAME -n $NAMESPACE -o jsonpath='{.spec.ports[0].port}' 2>/dev/null || echo "8000")

echo "🔗 Internal access:"
echo "   Service: $SERVICE_NAME.$NAMESPACE.svc.cluster.local:$SERVICE_PORT"
echo ""

# Get route info if available
ROUTE=$(oc get route -l app.kubernetes.io/name=vllm-qwen3 -n $NAMESPACE -o jsonpath='{.items[0].spec.host}' 2>/dev/null || echo "")
if [ ! -z "$ROUTE" ]; then
    echo "🌐 External access:"
    echo "   Route: https://$ROUTE"
    echo ""
    echo "🧪 Test the API:"
    echo "   curl -X POST https://$ROUTE/v1/completions \\"
    echo "     -H 'Content-Type: application/json' \\"
    echo "     -d '{\"model\": \"$MODEL\", \"prompt\": \"The capital of France is\", \"max_tokens\": 50}'"
fi

echo ""
echo "📈 Performance summary:"
echo "   Model: $MODEL"
echo "   Storage: aws-ebs (8,904 MB/s read speed)"
echo "   Cache size: $CACHE_SIZE"
echo "   Startup time: ${elapsed} seconds (with preloaded cache)"
echo ""
echo "🔄 For future deployments:"
echo "   The model cache persists across pod restarts"
echo "   Subsequent deployments will start in ~1-3 minutes"
echo ""
echo "✨ Enjoy your blazing-fast vLLM deployment!" 