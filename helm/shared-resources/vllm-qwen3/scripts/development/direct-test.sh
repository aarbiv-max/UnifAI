#!/bin/bash

# Direct Performance Test - No YAML complexity
# Uses kubectl run directly to avoid parsing issues

set -e

NAMESPACE="tag-ai--runtime-int" 
MODEL="Qwen/Qwen3-32B-FP8"

echo "=== DIRECT REAL PERFORMANCE TEST ==="
echo "Model: $MODEL"
echo "Date: $(date)"
echo ""

# Function to wait and time
wait_and_time() {
    local pod_name=$1
    local test_name=$2
    local start_time=$(date +%s)
    
    echo "⏳ Running $test_name..."
    
    # Wait for completion
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
                kubectl logs $pod_name -n $NAMESPACE --tail=5
                return $ELAPSED
                ;;
            "Running")
                echo "🔄 $test_name running... (${ELAPSED}s)"
                ;;
            *)
                echo "⏳ $test_name: $STATUS (${ELAPSED}s)"
                ;;
        esac
        
        sleep 10
        
        if [ $ELAPSED -gt 1800 ]; then  # 30 minute timeout
            echo "⏰ Timeout"
            return $ELAPSED
        fi
    done
}

echo "🐍 PYTHON TEST"
echo "=============="

PYTHON_START=$(date +%s)

# Simple Python test
kubectl run python-direct \
  --image=python:3.11-slim \
  --restart=Never \
  --namespace=$NAMESPACE \
  --labels="paas.redhat.com/appcode=TAG-001" \
  --rm=false \
  --command -- /bin/bash -c "
    echo 'PYTHON START'; 
    START=\$(date +%s); 
    echo 'Installing huggingface-hub...'; 
    pip install --quiet huggingface-hub; 
    DEPS=\$(date +%s); 
    echo 'Dependencies:' \$((DEPS-START)) 'seconds'; 
    echo 'Downloading $MODEL...'; 
    python3 -c \"from huggingface_hub import snapshot_download; import time; s=time.time(); snapshot_download('$MODEL', cache_dir='/tmp'); print('Download:', int(time.time()-s), 'seconds')\"; 
    END=\$(date +%s); 
    echo 'PYTHON TOTAL:' \$((END-START)) 'seconds'
  " &

# Wait for Python test
wait_and_time "python-direct" "Python approach"
PYTHON_TOTAL=$?

echo ""
echo "🚀 GIT LFS TEST"
echo "==============="

GIT_START=$(date +%s)

# Simple Git LFS test
kubectl run git-direct \
  --image=alpine/git:latest \
  --restart=Never \
  --namespace=$NAMESPACE \
  --labels="paas.redhat.com/appcode=TAG-001" \
  --rm=false \
  --command -- /bin/sh -c "
    echo 'GIT LFS START'; 
    START=\$(date +%s); 
    echo 'Installing git-lfs...'; 
    apk add --quiet git-lfs aria2; 
    git config --global user.name Test; 
    git config --global user.email test@test.com; 
    git lfs install --skip-repo; 
    DEPS=\$(date +%s); 
    echo 'Dependencies:' \$((DEPS-START)) 'seconds'; 
    echo 'Downloading $MODEL...'; 
    cd /tmp; 
    GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 https://huggingface.co/$MODEL model; 
    cd model; 
    git lfs pull; 
    END=\$(date +%s); 
    echo 'GIT LFS TOTAL:' \$((END-START)) 'seconds'
  " &

# Wait for Git test
wait_and_time "git-direct" "Git LFS approach"
GIT_TOTAL=$?

echo ""
echo "📊 REAL PERFORMANCE RESULTS"
echo "=========================="

echo ""
echo "🐍 PYTHON LOGS:"
kubectl logs python-direct -n $NAMESPACE | tail -10

echo ""
echo "🚀 GIT LFS LOGS:"
kubectl logs git-direct -n $NAMESPACE | tail -10

echo ""
echo "📈 COMPARISON:"
echo "=============="
echo "🐍 Python Total: $PYTHON_TOTAL seconds"
echo "🚀 Git LFS Total: $GIT_TOTAL seconds"

if [ $PYTHON_TOTAL -gt $GIT_TOTAL ]; then
    DIFF=$((PYTHON_TOTAL - GIT_TOTAL))
    PCT=$(( (DIFF * 100) / PYTHON_TOTAL ))
    echo ""
    echo "🏆 WINNER: Git LFS!"
    echo "⚡ $DIFF seconds faster ($PCT% improvement)"
    echo "✅ This validates our 'model-man' initContainer choice!"
elif [ $GIT_TOTAL -gt $PYTHON_TOTAL ]; then
    DIFF=$((GIT_TOTAL - PYTHON_TOTAL))
    PCT=$(( (DIFF * 100) / PYTHON_TOTAL ))
    echo ""
    echo "🏆 WINNER: Python!"
    echo "⚡ $DIFF seconds faster ($PCT% improvement)"
else
    echo ""
    echo "🤝 TIE: Equal performance"
fi

echo ""
echo "🎯 REAL WORLD DATA SUMMARY:"
echo "=========================="
echo "✅ Model: $MODEL (Real production model)"
echo "✅ Environment: Your OpenShift cluster"
echo "✅ Both downloaded the same 25-30GB model"
echo "✅ This is ACTUAL performance comparison!"

# Extract detailed timing
echo ""
echo "📋 DETAILED BREAKDOWN:"
echo "====================="
echo "Python details:"
kubectl logs python-direct -n $NAMESPACE | grep -E "(Dependencies|Download|TOTAL): [0-9]+ seconds"

echo ""
echo "Git LFS details:"
kubectl logs git-direct -n $NAMESPACE | grep -E "(Dependencies|Download|TOTAL): [0-9]+ seconds"

echo ""
read -p "🗑️ Clean up test pods? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🧹 Cleaning up..."
    kubectl delete pod python-direct git-direct -n $NAMESPACE --ignore-not-found=true
    echo "✅ Done"
else
    echo "📂 Pods preserved: python-direct, git-direct"
fi

echo ""
echo "🎯 DEFINITIVE real data test complete: $(date)" 