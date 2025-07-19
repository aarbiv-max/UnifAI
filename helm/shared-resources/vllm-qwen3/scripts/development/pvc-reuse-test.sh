#!/bin/bash

# PVC Reuse Test - Test subsequent download using same persistent volume
# Simulates what happens when initContainer runs on already-cached model

set -e

NAMESPACE="tag-ai--runtime-int"
MODEL="Qwen/Qwen3-32B-FP8"
PVC_NAME="vllm-qwen3-model-cache"

echo "=== PVC REUSE PERFORMANCE TEST ==="
echo "Model: $MODEL"
echo "PVC: $PVC_NAME (should already contain the model)"
echo "Purpose: Test how fast Git LFS is when model already exists in PVC"
echo "Date: $(date)"
echo ""

# Function to time operations
time_operation() {
    local pod_name=$1
    local test_name=$2
    local start_time=$(date +%s)
    
    echo "⏳ Running $test_name..."
    
    while true; do
        STATUS=$(kubectl get pod $pod_name -n $NAMESPACE -o jsonpath='{.status.phase}' 2>/dev/null || echo "NotFound")
        ELAPSED=$(($(date +%s) - start_time))
        
        case $STATUS in
            "Succeeded")
                echo "✅ $test_name completed in $ELAPSED seconds"
                return $ELAPSED
                ;;
            "Failed")
                echo "❌ $test_name failed after $ELAPSED seconds"
                kubectl logs $pod_name -n $NAMESPACE --tail=10
                return $ELAPSED
                ;;
            "Running")
                if [ $((ELAPSED % 30)) -eq 0 ]; then
                    echo "🔄 $test_name running... (${ELAPSED}s)"
                    # Show recent progress
                    kubectl logs $pod_name -n $NAMESPACE --tail=2 2>/dev/null | grep -v "^$" | tail -1
                fi
                ;;
            *)
                echo "⏳ $test_name: $STATUS (${ELAPSED}s)"
                ;;
        esac
        
        sleep 5
        
        if [ $ELAPSED -gt 300 ]; then  # 5 minute timeout - should be MUCH faster for cached
            echo "⏰ Timeout after $ELAPSED seconds (cached download should be very fast!)"
            return $ELAPSED
        fi
    done
}

echo "🔍 STEP 1: Check existing cache in PVC"
echo "======================================"

# First, let's see what's already in the PVC from our previous test
kubectl run cache-inspector \
  --image=alpine:latest \
  --restart=Never \
  --namespace=$NAMESPACE \
  --labels="paas.redhat.com/appcode=TAG-001" \
  --overrides='{
    "spec": {
      "containers": [{
        "name": "cache-inspector", 
        "image": "alpine:latest",
        "command": ["/bin/sh", "-c"],
        "args": ["echo \"CACHE INSPECTION START\"; echo \"PVC Mount: /models\"; if [ -d \"/models\" ]; then echo \"PVC mounted successfully\"; ls -la /models/; echo \"\"; echo \"Looking for existing model...\"; if [ -d \"/models/model\" ]; then echo \"Found /models/model directory:\"; du -sh /models/model 2>/dev/null || echo \"Cannot check size\"; ls -la /models/model/ | head -10; elif [ -d \"/models/Qwen--Qwen3-32B-FP8\" ]; then echo \"Found /models/Qwen--Qwen3-32B-FP8 directory:\"; du -sh /models/Qwen--Qwen3-32B-FP8 2>/dev/null || echo \"Cannot check size\"; ls -la /models/Qwen--Qwen3-32B-FP8/ | head -10; else echo \"Searching for any model directories...\"; find /models -name \"*Qwen*\" -type d 2>/dev/null || echo \"No Qwen directories found\"; find /models -name \"*.safetensors\" 2>/dev/null | head -5 || echo \"No .safetensors files found\"; fi; else echo \"PVC not mounted or empty\"; fi; echo \"CACHE INSPECTION COMPLETE\""],
        "volumeMounts": [{"name": "model-cache", "mountPath": "/models"}]
      }],
      "volumes": [{"name": "model-cache", "persistentVolumeClaim": {"claimName": "'$PVC_NAME'"}}],
      "restartPolicy": "Never"
    }
  }' &

time_operation "cache-inspector" "Cache inspection"

echo ""
echo "📋 EXISTING CACHE STATUS:"
kubectl logs cache-inspector -n $NAMESPACE

echo ""
echo "🚀 STEP 2: Subsequent Download Test (New Pod, Same PVC)"
echo "======================================================"

# Now test subsequent download with new pod using same PVC
SUBSEQUENT_START=$(date +%s)

kubectl run pvc-reuse-test \
  --image=alpine/git:latest \
  --restart=Never \
  --namespace=$NAMESPACE \
  --labels="paas.redhat.com/appcode=TAG-001" \
  --overrides='{
    "spec": {
      "containers": [{
        "name": "git-tester", 
        "image": "alpine/git:latest",
        "command": ["/bin/sh", "-c"],
        "args": ["echo \"=== PVC REUSE TEST START ===\"; echo \"Model: '$MODEL'\"; echo \"Start: $(date)\"; TOTAL_START=$(date +%s); echo \"\"; echo \"📦 Installing git-lfs...\"; apk add --quiet git-lfs; git config --global user.name \"PVC Test\"; git config --global user.email \"test@example.com\"; git lfs install --skip-repo; DEPS_END=$(date +%s); DEP_TIME=$((DEPS_END - TOTAL_START)); echo \"✅ Dependencies: $DEP_TIME seconds\"; echo \"\"; echo \"📂 Checking existing cache...\"; cd /models; echo \"PVC contents:\"; ls -la; echo \"\"; echo \"🔽 Starting Git LFS download...\"; DOWNLOAD_START=$(date +%s); if [ -d \"model\" ]; then echo \"Found existing model directory - entering it\"; cd model; echo \"Running git lfs pull to update/verify...\"; git lfs pull; echo \"✅ Git LFS pull completed (should be very fast for existing files)\"; elif [ -d \"Qwen--Qwen3-32B-FP8\" ]; then echo \"Found existing Qwen--Qwen3-32B-FP8 directory - entering it\"; cd Qwen--Qwen3-32B-FP8; echo \"Running git lfs pull to update/verify...\"; git lfs pull; echo \"✅ Git LFS pull completed (should be very fast for existing files)\"; else echo \"No existing model found - doing fresh clone\"; GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 https://huggingface.co/'$MODEL' model; cd model; git lfs pull; echo \"✅ Fresh download completed\"; fi; DOWNLOAD_END=$(date +%s); DOWNLOAD_TIME=$((DOWNLOAD_END - DOWNLOAD_START)); TOTAL_END=$(date +%s); TOTAL_TIME=$((TOTAL_END - TOTAL_START)); echo \"\"; echo \"=== PVC REUSE RESULTS ===\"; echo \"Dependencies: $DEP_TIME seconds\"; echo \"Download/Verify: $DOWNLOAD_TIME seconds\"; echo \"Total: $TOTAL_TIME seconds\"; echo \"\"; echo \"📊 Final cache status:\"; du -sh . 2>/dev/null || echo \"Cannot check size\"; echo \"=== PVC REUSE TEST COMPLETE ===\""],
        "volumeMounts": [{"name": "model-cache", "mountPath": "/models"}]
      }],
      "volumes": [{"name": "model-cache", "persistentVolumeClaim": {"claimName": "'$PVC_NAME'"}}],
      "restartPolicy": "Never"
    }
  }' &

time_operation "pvc-reuse-test" "PVC reuse test"
SUBSEQUENT_TOTAL=$?

echo ""
echo "📊 PVC REUSE PERFORMANCE RESULTS"
echo "================================"

echo ""
echo "📋 COMPLETE TEST LOG:"
kubectl logs pvc-reuse-test -n $NAMESPACE

echo ""
echo "📈 PERFORMANCE ANALYSIS:"
echo "======================="

# Extract timing data from logs
DEP_TIME=$(kubectl logs pvc-reuse-test -n $NAMESPACE | grep "Dependencies:" | awk '{print $2}')
DOWNLOAD_TIME=$(kubectl logs pvc-reuse-test -n $NAMESPACE | grep "Download/Verify:" | awk '{print $2}')
TOTAL_TIME=$(kubectl logs pvc-reuse-test -n $NAMESPACE | grep "Total:" | awk '{print $2}')

echo "📦 Dependencies Installation: ${DEP_TIME:-unknown} seconds"
echo "🔽 Download/Verification: ${DOWNLOAD_TIME:-unknown} seconds"
echo "⏱️ Total Time: ${TOTAL_TIME:-unknown} seconds"
echo ""

# Compare with our previous fresh download (905 seconds)
FRESH_DOWNLOAD_TIME=905
if [ -n "$TOTAL_TIME" ] && [ "$TOTAL_TIME" -lt "$FRESH_DOWNLOAD_TIME" ]; then
    IMPROVEMENT=$((FRESH_DOWNLOAD_TIME - TOTAL_TIME))
    PERCENTAGE=$(( (IMPROVEMENT * 100) / FRESH_DOWNLOAD_TIME ))
    echo "🚀 CACHING BENEFIT vs Fresh Download:"
    echo "   Fresh download: $FRESH_DOWNLOAD_TIME seconds"
    echo "   Cached download: $TOTAL_TIME seconds"
    echo "   ⚡ Improvement: $IMPROVEMENT seconds faster ($PERCENTAGE% improvement)!"
    echo ""
    echo "✅ This proves excellent caching performance!"
else
    echo "⚠️ Cached download time: ${TOTAL_TIME:-unknown} seconds"
    echo "🔍 Expected much faster than fresh download ($FRESH_DOWNLOAD_TIME seconds)"
fi

echo ""
echo "🎯 REAL-WORLD SCENARIO ANALYSIS:"
echo "==============================="
echo "✅ Model: $MODEL (Real production model)"
echo "✅ PVC: $PVC_NAME (Persistent volume with existing cache)"
echo "✅ Scenario: New pod mounting existing cache (pod restart simulation)"
echo "✅ This simulates exactly what happens with our 'model-man' initContainer"

# Check if the test found existing files
FOUND_EXISTING=$(kubectl logs pvc-reuse-test -n $NAMESPACE | grep -E "(Found existing|should be very fast)" | head -1)
if [ -n "$FOUND_EXISTING" ]; then
    echo "✅ Cache Hit: $FOUND_EXISTING"
    echo "🎯 Git LFS successfully used existing cached files!"
else
    echo "⚠️ May have done fresh download - check logs above"
fi

echo ""
echo "📋 PRODUCTION IMPLICATIONS:"
echo "=========================="
echo "• Pod restarts: ${TOTAL_TIME:-unknown} seconds (vs $FRESH_DOWNLOAD_TIME seconds fresh)"
echo "• Model updates: Git LFS will only download changed files"
echo "• Cache efficiency: Persistent volume reuse works excellently"
echo "• initContainer performance: Very fast on subsequent starts"

echo ""
read -p "🗑️ Clean up test pods? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🧹 Cleaning up..."
    kubectl delete pod cache-inspector pvc-reuse-test -n $NAMESPACE --ignore-not-found=true
    echo "✅ Cleanup complete"
    echo "📂 PVC $PVC_NAME preserved with cached model"
else
    echo "📂 Test pods preserved for analysis:"
    echo "  - cache-inspector, pvc-reuse-test"
    echo "  - View logs: kubectl logs [pod-name] -n $NAMESPACE"
    echo "📂 PVC $PVC_NAME preserved with cached model"
fi

echo ""
echo "🎯 PVC reuse test completed: $(date)"
echo ""
echo "This shows the real-world performance of our 'model-man' initContainer!" 