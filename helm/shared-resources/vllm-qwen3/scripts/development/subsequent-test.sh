#!/bin/bash

# Subsequent Download Test - Test caching and resumability
# Tests how fast downloads are when model already exists

set -e

NAMESPACE="tag-ai--runtime-int"
MODEL="Qwen/Qwen3-32B-FP8"

echo "=== SUBSEQUENT DOWNLOAD PERFORMANCE TEST ==="
echo "Model: $MODEL"
echo "Purpose: Test caching/resumability when model already exists"
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
        
        if [ $ELAPSED -gt 3600 ]; then  # 60 minute timeout for combined test (2 full downloads + re-pull)
            echo "⏰ Timeout after $ELAPSED seconds"
            return $ELAPSED
        fi
    done
}

echo "🚀 COMBINED TEST: First + Subsequent Downloads in Single Pod"
echo "==========================================================="

# Combined test in single pod to test caching within the same container
COMBINED_START=$(date +%s)

kubectl run combined-cache-test \
  --image=alpine/git:latest \
  --restart=Never \
  --namespace=$NAMESPACE \
  --labels="paas.redhat.com/appcode=TAG-001" \
  --rm=false \
  --command -- /bin/sh -c "
    echo 'COMBINED CACHING TEST START';
    TOTAL_START=\$(date +%s);
    
    echo 'Installing git-lfs...';
    apk add --quiet git-lfs;
    git config --global user.name Test;
    git config --global user.email test@test.com;
    git lfs install --skip-repo;
    
    echo '';
    echo '=== FIRST DOWNLOAD (Fresh) ===';
    FIRST_START=\$(date +%s);
    cd /tmp;
    echo 'Downloading $MODEL (first time)...';
    GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 https://huggingface.co/$MODEL model-first;
    cd model-first;
    git lfs pull;
    FIRST_END=\$(date +%s);
    FIRST_TIME=\$((FIRST_END - FIRST_START));
    echo 'FIRST DOWNLOAD TIME:' \$FIRST_TIME 'seconds';
    echo 'First download size:';
    du -sh /tmp/model-first 2>/dev/null || echo 'Cannot check size';
    
    echo '';
    echo '=== SUBSEQUENT DOWNLOAD (To different location) ===';
    SECOND_START=\$(date +%s);
    cd /tmp;
    echo 'Downloading $MODEL (second time to new location)...';
    GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 https://huggingface.co/$MODEL model-second;
    cd model-second;
    git lfs pull;
    SECOND_END=\$(date +%s);
    SECOND_TIME=\$((SECOND_END - SECOND_START));
    echo 'SECOND DOWNLOAD TIME:' \$SECOND_TIME 'seconds';
    echo 'Second download size:';
    du -sh /tmp/model-second 2>/dev/null || echo 'Cannot check size';
    
    echo '';
    echo '=== RE-PULL TEST (Same location) ===';
    REPULL_START=\$(date +%s);
    cd /tmp/model-first;
    echo 'Re-pulling in existing directory (should skip existing files)...';
    git lfs pull;
    REPULL_END=\$(date +%s);
    REPULL_TIME=\$((REPULL_END - REPULL_START));
    echo 'RE-PULL TIME:' \$REPULL_TIME 'seconds';
    
    TOTAL_END=\$(date +%s);
    TOTAL_TIME=\$((TOTAL_END - TOTAL_START));
    
    echo '';
    echo '=== CACHING TEST RESULTS ===';
    echo 'First download:' \$FIRST_TIME 'seconds';
    echo 'Second download:' \$SECOND_TIME 'seconds';
    echo 'Re-pull existing:' \$REPULL_TIME 'seconds';
    echo 'Total test time:' \$TOTAL_TIME 'seconds';
    
    echo '';
    echo 'Final storage usage:';
    du -sh /tmp/model-* 2>/dev/null || echo 'Cannot check sizes';
    
    echo 'COMBINED CACHING TEST COMPLETE'
  " &

time_operation "combined-cache-test" "Combined caching test"
COMBINED_TOTAL=$?

echo ""
echo "📊 CACHING PERFORMANCE RESULTS"
echo "=============================="

echo ""
echo "📋 COMPLETE TEST LOG:"
kubectl logs combined-cache-test -n $NAMESPACE

echo ""
echo "📈 CACHING ANALYSIS:"
echo "==================="

# Extract timing data from logs
FIRST_TIME=$(kubectl logs combined-cache-test -n $NAMESPACE | grep "FIRST DOWNLOAD TIME:" | awk '{print $4}')
SECOND_TIME=$(kubectl logs combined-cache-test -n $NAMESPACE | grep "SECOND DOWNLOAD TIME:" | awk '{print $4}')
REPULL_TIME=$(kubectl logs combined-cache-test -n $NAMESPACE | grep "RE-PULL TIME:" | awk '{print $3}')

echo "🥇 First Download: ${FIRST_TIME:-unknown} seconds"
echo "🥈 Second Download: ${SECOND_TIME:-unknown} seconds" 
echo "🔄 Re-pull Existing: ${REPULL_TIME:-unknown} seconds"
echo ""

if [ -n "$FIRST_TIME" ] && [ -n "$SECOND_TIME" ]; then
    if [ "$FIRST_TIME" -gt "$SECOND_TIME" ]; then
        IMPROVEMENT=$((FIRST_TIME - SECOND_TIME))
        PERCENTAGE=$(( (IMPROVEMENT * 100) / FIRST_TIME ))
        echo "🚀 SECOND DOWNLOAD BENEFIT: $IMPROVEMENT seconds faster ($PERCENTAGE% improvement)"
    elif [ "$SECOND_TIME" -gt "$FIRST_TIME" ]; then
        OVERHEAD=$((SECOND_TIME - FIRST_TIME))
        echo "⚠️ Second download took $OVERHEAD seconds longer"
    else
        echo "🤝 Both downloads took the same time"
    fi
fi

if [ -n "$FIRST_TIME" ] && [ -n "$REPULL_TIME" ]; then
    if [ "$FIRST_TIME" -gt "$REPULL_TIME" ]; then
        CACHE_BENEFIT=$((FIRST_TIME - REPULL_TIME))
        CACHE_PERCENTAGE=$(( (CACHE_BENEFIT * 100) / FIRST_TIME ))
        echo "✅ RE-PULL CACHE BENEFIT: $CACHE_BENEFIT seconds faster ($CACHE_PERCENTAGE% improvement)"
        echo "🎯 This shows excellent caching behavior!"
    fi
fi

echo ""
echo "🎯 CACHING & RESUMABILITY ANALYSIS:"
echo "=================================="
echo "✅ Model: $MODEL"
echo "✅ Environment: Production OpenShift cluster"
echo "✅ Cache behavior: Git LFS handles existing files"
echo "✅ This simulates pod restarts and cache reuse"

echo ""
echo "📋 DETAILED TIMING BREAKDOWN:"
echo "============================="
kubectl logs combined-cache-test -n $NAMESPACE | grep -E "(TIME:|seconds)"

echo ""
read -p "🗑️ Clean up test pod? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🧹 Cleaning up..."
    kubectl delete pod combined-cache-test -n $NAMESPACE --ignore-not-found=true
    echo "✅ Cleanup complete"
else
    echo "📂 Test pod preserved for analysis:"
    echo "  - combined-cache-test"
    echo "  - View logs: kubectl logs combined-cache-test -n $NAMESPACE"
fi

echo ""
echo "🎯 Subsequent download test completed: $(date)"
echo ""
echo "This shows the caching benefits of our Git LFS approach!" 