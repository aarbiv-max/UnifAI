#!/bin/bash

# Super Simple Performance Test using kubectl run
# Avoids all YAML parsing issues

set -e

NAMESPACE="tag-ai--runtime-int"
MODEL="Qwen/Qwen3-32B-FP8"

echo "=== SIMPLE REAL PERFORMANCE TEST ==="
echo "Model: $MODEL"
echo "Date: $(date)"
echo ""

# Create simple PVC first
cat > /tmp/pvc.yaml <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-pvc
  namespace: $NAMESPACE
  labels:
    paas.redhat.com/appcode: TAG-001
  annotations:
    kubernetes.io/reclaimPolicy: "Delete"
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: aws-ebs
  resources:
    requests:
      storage: 50Gi
EOF

echo "📦 Creating test PVC..."
oc apply -f /tmp/pvc.yaml

# Function to wait for pod completion
wait_for_completion() {
    local pod_name=$1
    local max_wait=${2:-1800}  # 30 minutes default
    local count=0
    
    echo "⏳ Waiting for $pod_name to complete..."
    while [ $count -lt $max_wait ]; do
        STATUS=$(oc get pod $pod_name -n $NAMESPACE -o jsonpath='{.status.phase}' 2>/dev/null || echo "NotFound")
        
        case $STATUS in
            "Succeeded")
                echo "✅ $pod_name completed successfully"
                return 0
                ;;
            "Failed")
                echo "❌ $pod_name failed"
                oc logs $pod_name -n $NAMESPACE --tail=10
                return 1
                ;;
            "Running")
                echo "🔄 $pod_name running... (${count}s elapsed)"
                ;;
            *)
                echo "⏳ $pod_name status: $STATUS (${count}s elapsed)"
                ;;
        esac
        
        sleep 30
        count=$((count + 30))
    done
    
    echo "⏰ Timeout waiting for $pod_name"
    return 1
}

echo ""
echo "🐍 TEST 1: PYTHON APPROACH"
echo "=========================="

PYTHON_START=$(date +%s)

# Use kubectl run for Python test
kubectl run python-perf \
  --image=python:3.11-slim \
  --restart=Never \
  --namespace=$NAMESPACE \
  --labels="paas.redhat.com/appcode=TAG-001" \
  --env="MODEL=$MODEL" \
  --command -- /bin/bash -c "
    echo 'PYTHON TEST START'; 
    echo 'Model: '\$MODEL; 
    START=\$(date +%s); 
    mkdir -p /cache; 
    echo 'Installing huggingface-hub...'; 
    pip install --quiet huggingface-hub; 
    echo 'Downloading model...'; 
    python3 -c \"from huggingface_hub import snapshot_download; snapshot_download('\$MODEL', cache_dir='/cache')\"; 
    END=\$(date +%s); 
    echo 'PYTHON TOTAL TIME:' \$((END-START)) 'seconds'; 
    echo 'Cache size:'; 
    du -sh /cache
  "

# Wait for Python test
wait_for_completion "python-perf" 1800
PYTHON_END=$(date +%s)
PYTHON_TOTAL=$((PYTHON_END - PYTHON_START))

echo ""
echo "🚀 TEST 2: GIT LFS APPROACH"
echo "=========================="

GIT_START=$(date +%s)

# Use kubectl run for Git test
kubectl run git-perf \
  --image=alpine/git:latest \
  --restart=Never \
  --namespace=$NAMESPACE \
  --labels="paas.redhat.com/appcode=TAG-001" \
  --env="MODEL=$MODEL" \
  --command -- /bin/sh -c "
    echo 'GIT LFS TEST START'; 
    echo 'Model: '\$MODEL; 
    START=\$(date +%s); 
    mkdir -p /cache; 
    echo 'Installing git-lfs...'; 
    apk add --quiet git-lfs aria2; 
    git config --global user.name Test; 
    git config --global user.email test@test.com; 
    git lfs install --skip-repo; 
    echo 'Downloading model...'; 
    cd /cache; 
    GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 https://huggingface.co/\$MODEL repo; 
    cd repo; 
    git lfs pull; 
    END=\$(date +%s); 
    echo 'GIT LFS TOTAL TIME:' \$((END-START)) 'seconds'; 
    echo 'Cache size:'; 
    du -sh /cache/repo
  "

# Wait for Git test
wait_for_completion "git-perf" 1800
GIT_END=$(date +%s)
GIT_TOTAL=$((GIT_END - GIT_START))

echo ""
echo "📊 RESULTS COMPARISON"
echo "===================="

echo ""
echo "🐍 PYTHON LOGS:"
oc logs python-perf -n $NAMESPACE | tail -10

echo ""
echo "🚀 GIT LFS LOGS:"
oc logs git-perf -n $NAMESPACE | tail -10

echo ""
echo "📈 FINAL COMPARISON:"
echo "===================="
echo "🐍 Python Total: $PYTHON_TOTAL seconds"
echo "🚀 Git LFS Total: $GIT_TOTAL seconds"

if [ $PYTHON_TOTAL -gt $GIT_TOTAL ]; then
    DIFF=$((PYTHON_TOTAL - GIT_TOTAL))
    PCT=$(( (DIFF * 100) / PYTHON_TOTAL ))
    echo ""
    echo "🏆 WINNER: Git LFS!"
    echo "⚡ $DIFF seconds faster ($PCT% improvement)"
elif [ $GIT_TOTAL -gt $PYTHON_TOTAL ]; then
    DIFF=$((GIT_TOTAL - PYTHON_TOTAL))
    PCT=$(( (DIFF * 100) / PYTHON_TOTAL ))
    echo ""
    echo "🏆 WINNER: Python!"
    echo "⚡ $DIFF seconds faster ($PCT% improvement)"
else
    echo ""
    echo "🤝 TIE: Equal performance!"
fi

echo ""
echo "🎯 REAL WORLD TEST COMPLETE!"
echo "============================"
echo "✅ Model: $MODEL (Real production model)"
echo "✅ Environment: Your OpenShift cluster" 
echo "✅ This is ACTUAL performance data!"

# Cleanup
read -p "🗑️ Clean up test resources? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🧹 Cleaning up..."
    oc delete pod python-perf git-perf -n $NAMESPACE --ignore-not-found=true
    oc delete pvc test-pvc -n $NAMESPACE --ignore-not-found=true
    rm -f /tmp/pvc.yaml
    echo "✅ Cleanup done"
fi

echo "🎯 Test completed: $(date)" 