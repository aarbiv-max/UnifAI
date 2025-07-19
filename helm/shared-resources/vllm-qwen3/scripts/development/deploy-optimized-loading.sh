#!/bin/bash

# vLLM Optimized Loading Deployment Script
# This script deploys vLLM with configuration optimized for fast model loading

set -e

NAMESPACE="tag-ai--runtime-int"
HELM_CHART="."
VALUES_FILE="values-optimized-loading.yaml"

echo "=== vLLM Optimized Loading Deployment ==="
echo "Namespace: $NAMESPACE"
echo "Values file: $VALUES_FILE"
echo ""

# Check if optimized values file exists
if [ ! -f "$VALUES_FILE" ]; then
    echo "❌ Optimized values file not found: $VALUES_FILE"
    exit 1
fi

echo "🔧 Deploying vLLM with optimized loading configuration..."
echo "Key optimizations:"
echo "  - Higher GPU memory utilization (0.90)"
echo "  - Reduced batch sizes for faster loading"
echo "  - Increased shared memory (32Gi)"
echo "  - CUDA memory pool optimization"
echo "  - Parallel processing optimizations"
echo ""

# Deploy with optimized configuration
helm upgrade --install vllm-qwen3-optimized $HELM_CHART \
    --namespace $NAMESPACE \
    --values $VALUES_FILE \
    --set volumes.modelCache.enabled=true

echo "✅ vLLM deployed with optimized loading configuration"
echo ""

# Monitor deployment
echo "📊 Monitoring optimized deployment..."
echo "Expected improvements:"
echo "  - 20-30% faster model loading"
echo "  - Better GPU memory utilization"
echo "  - Reduced startup time"
echo ""

# Wait for pod to be ready
echo "⏳ Waiting for pod to be ready..."
start_time=$(date +%s)

while true; do
    POD_STATUS=$(oc get pods -n $NAMESPACE -l app.kubernetes.io/name=vllm-qwen3-optimized --no-headers -o custom-columns=":status.phase" 2>/dev/null | head -1)
    current_time=$(date +%s)
    elapsed=$((current_time - start_time))
    
    case $POD_STATUS in
        "Running")
            echo "✅ Pod is running! (${elapsed}s elapsed)"
            break
            ;;
        "Pending")
            echo "⏳ Pod is pending... (${elapsed}s elapsed)"
            sleep 10
            ;;
        "Failed")
            echo "❌ Pod failed to start!"
            oc get pods -n $NAMESPACE -l app.kubernetes.io/name=vllm-qwen3-optimized
            exit 1
            ;;
        *)
            echo "⏳ Pod status: $POD_STATUS (${elapsed}s elapsed)"
            sleep 10
            ;;
    esac
done

echo ""

# Monitor model loading
echo "🚀 Monitoring model loading progress..."
echo "You can monitor with: oc logs -f deployment/vllm-qwen3-optimized -n $NAMESPACE"
echo ""

# Wait for readiness
echo "⏳ Waiting for model to be ready..."
start_time=$(date +%s)

while true; do
    READY=$(oc get pods -n $NAMESPACE -l app.kubernetes.io/name=vllm-qwen3-optimized --no-headers -o custom-columns=":status.containerStatuses[0].ready" 2>/dev/null | head -1)
    current_time=$(date +%s)
    elapsed=$((current_time - start_time))
    
    if [ "$READY" == "true" ]; then
        echo "✅ Model is ready! Total time: ${elapsed}s ($((elapsed/60)) minutes)"
        break
    else
        echo "⏳ Model still loading... (${elapsed}s elapsed)"
        sleep 30
    fi
done

echo ""
echo "🎉 Optimized vLLM deployment complete!"
echo ""
echo "📊 Performance Summary:"
echo "  - Total deployment time: ${elapsed}s"
echo "  - Expected improvement: 20-30% faster loading"
echo "  - GPU memory utilization: 90%"
echo "  - Shared memory: 32Gi"
echo ""
echo "🔗 Access your optimized vLLM:"
ROUTE_URL=$(oc get route vllm-qwen3-optimized -n $NAMESPACE -o jsonpath='{.spec.host}' 2>/dev/null || echo "Route not ready")
if [ ! -z "$ROUTE_URL" ]; then
    echo "  URL: http://$ROUTE_URL"
    echo "  Health check: http://$ROUTE_URL/health"
else
    echo "  Route not ready yet. Check with: oc get routes -n $NAMESPACE"
fi
echo ""
echo "🧪 Test the optimized deployment:"
echo "  curl -X POST http://$ROUTE_URL/v1/completions \\"
echo "    -H \"Content-Type: application/json\" \\"
echo "    -d '{\"model\": \"Qwen/Qwen3-32B-FP8\", \"prompt\": \"Hello world\", \"max_tokens\": 10}'" 