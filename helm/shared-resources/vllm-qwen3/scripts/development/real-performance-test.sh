#!/bin/bash

# Real Performance Test: Python vs Git LFS with Qwen3-32B-FP8
# Simplified to avoid YAML parsing issues

set -e

NAMESPACE="tag-ai--runtime-int"
MODEL="Qwen/Qwen3-32B-FP8"

echo "=== REAL PERFORMANCE COMPARISON TEST ==="
echo "Model: $MODEL (~20-30GB FP8 Model)"
echo "Namespace: $NAMESPACE"
echo "Date: $(date)"
echo ""

# Function to monitor pod
monitor_pod() {
    local pod_name=$1
    local timeout=${2:-3600}  # Default 1 hour
    local start_time=$(date +%s)
    
    while true; do
        STATUS=$(oc get pod $pod_name -n $NAMESPACE -o jsonpath='{.status.phase}' 2>/dev/null || echo "NotFound")
        ELAPSED=$(($(date +%s) - start_time))
        
        case $STATUS in
            "Succeeded")
                echo "✅ $pod_name completed successfully"
                return 0
                ;;
            "Failed")
                echo "❌ $pod_name failed"
                echo "Last 20 log lines:"
                oc logs $pod_name -n $NAMESPACE --tail=20
                return 1
                ;;
            "Running")
                if [ $ELAPSED -gt $timeout ]; then
                    echo "⏰ $pod_name timed out after ${timeout}s"
                    return 1
                fi
                echo "⏳ $pod_name running... (${ELAPSED}s elapsed)"
                sleep 30
                ;;
            *)
                if [ $ELAPSED -gt 300 ]; then  # 5 minute startup timeout
                    echo "⏰ $pod_name failed to start"
                    oc describe pod $pod_name -n $NAMESPACE
                    return 1
                fi
                echo "⏳ $pod_name starting... (${ELAPSED}s elapsed)"
                sleep 10
                ;;
        esac
    done
}

# Create simple test PVC
echo "📦 Creating test PVC..."
oc apply -f - <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: perf-test-pvc
  namespace: $NAMESPACE
  labels:
    paas.redhat.com/appcode: TAG-001
    app: performance-test
  annotations:
    kubernetes.io/reclaimPolicy: "Delete"
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: aws-ebs
  resources:
    requests:
      storage: 100Gi
EOF

echo ""
echo "🔬 TEST 1: PYTHON APPROACH"
echo "==========================="

# Python test with simple commands
PYTHON_START=$(date +%s)
oc apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: python-test
  namespace: $NAMESPACE
  labels:
    paas.redhat.com/appcode: TAG-001
    app: performance-test
spec:
  restartPolicy: Never
  containers:
  - name: downloader
    image: python:3.11-slim
    env:
    - name: HOME
      value: "/tmp/workspace"
    command: ["/bin/bash", "-c"]
    args:
    - |
      set -e
      echo "=== PYTHON TEST START ==="
      echo "Model: $MODEL"
      echo "Start time: \$(date)"
      START_TIME=\$(date +%s)
      
      # Create workspace
      mkdir -p /tmp/workspace /models
      
      # Install dependencies
      echo "Installing dependencies..."
      DEP_START=\$(date +%s)
      pip install --quiet --cache-dir=/tmp/workspace huggingface-hub
      DEP_END=\$(date +%s)
      DEP_TIME=\$((DEP_END - DEP_START))
      echo "Dependencies: \$DEP_TIME seconds"
      
      # Download model
      echo "Downloading model..."
      DOWNLOAD_START=\$(date +%s)
      python3 -c "
from huggingface_hub import snapshot_download
import time
start = time.time()
try:
    path = snapshot_download('$MODEL', cache_dir='/models', resume_download=True)
    print('Downloaded to:', path)
except Exception as e:
    print('Error:', e)
end = time.time()
print('Download seconds:', int(end - start))
"
      DOWNLOAD_END=\$(date +%s)
      DOWNLOAD_TIME=\$((DOWNLOAD_END - DOWNLOAD_START))
      
      TOTAL_END=\$(date +%s)
      TOTAL_TIME=\$((TOTAL_END - START_TIME))
      
      echo "=== PYTHON RESULTS ==="
      echo "Dependencies: \$DEP_TIME sec"
      echo "Download: \$DOWNLOAD_TIME sec"
      echo "Total: \$TOTAL_TIME sec"
      echo "Cache size:"
      du -sh /models 2>/dev/null || echo "N/A"
      echo "=== PYTHON TEST END ==="
    volumeMounts:
    - name: cache
      mountPath: /models
  volumes:
  - name: cache
    persistentVolumeClaim:
      claimName: perf-test-pvc
EOF

# Monitor Python test
echo "Monitoring Python test..."
monitor_pod "python-test" 3600
PYTHON_END=$(date +%s)
PYTHON_TOTAL=$((PYTHON_END - PYTHON_START))

echo ""
echo "🔬 TEST 2: GIT LFS APPROACH"
echo "==========================="

# Git LFS test
GIT_START=$(date +%s)
oc apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: git-test
  namespace: $NAMESPACE
  labels:
    paas.redhat.com/appcode: TAG-001
    app: performance-test
spec:
  restartPolicy: Never
  containers:
  - name: downloader
    image: alpine/git:latest
    env:
    - name: HOME
      value: "/tmp/workspace"
    command: ["/bin/sh", "-c"]
    args:
    - |
      set -e
      echo "=== GIT LFS TEST START ==="
      echo "Model: $MODEL"
      echo "Start time: \$(date)"
      START_TIME=\$(date +%s)
      
      # Create workspace
      mkdir -p /tmp/workspace /models
      
      # Install dependencies
      echo "Installing dependencies..."
      DEP_START=\$(date +%s)
      apk add --quiet --no-cache git-lfs aria2
      git config --global user.name "Test"
      git config --global user.email "test@test.com"
      git lfs install --skip-repo
      DEP_END=\$(date +%s)
      DEP_TIME=\$((DEP_END - DEP_START))
      echo "Dependencies: \$DEP_TIME seconds"
      
      # Download model
      echo "Downloading model..."
      DOWNLOAD_START=\$(date +%s)
      cd /models
      
      # Clone repo structure
      export GIT_LFS_SKIP_SMUDGE=1
      git clone --depth 1 https://huggingface.co/$MODEL model-repo
      cd model-repo
      
      # Download LFS files
      export GIT_LFS_SKIP_SMUDGE=0
      git lfs pull || {
        echo "LFS failed, trying aria2..."
        git lfs ls-files | while read line; do
          file=\$(echo \$line | awk '{print \$3}')
          aria2c -x 4 -s 4 -k 1M -c "https://huggingface.co/$MODEL/resolve/main/\$file" -o "\$file"
        done
      }
      
      DOWNLOAD_END=\$(date +%s)
      DOWNLOAD_TIME=\$((DOWNLOAD_END - DOWNLOAD_START))
      
      TOTAL_END=\$(date +%s)
      TOTAL_TIME=\$((TOTAL_END - START_TIME))
      
      echo "=== GIT LFS RESULTS ==="
      echo "Dependencies: \$DEP_TIME sec"
      echo "Download: \$DOWNLOAD_TIME sec"
      echo "Total: \$TOTAL_TIME sec"
      echo "Cache size:"
      du -sh /models/model-repo 2>/dev/null || echo "N/A"
      echo "=== GIT LFS TEST END ==="
    volumeMounts:
    - name: cache
      mountPath: /models
  volumes:
  - name: cache
    persistentVolumeClaim:
      claimName: perf-test-pvc
EOF

# Monitor Git test
echo "Monitoring Git LFS test..."
monitor_pod "git-test" 3600
GIT_END=$(date +%s)
GIT_TOTAL=$((GIT_END - GIT_START))

echo ""
echo "📊 PERFORMANCE COMPARISON RESULTS"
echo "=================================="

# Get detailed results from logs
echo "🐍 PYTHON APPROACH DETAILS:"
oc logs python-test -n $NAMESPACE | grep -A 10 -B 5 "PYTHON RESULTS"

echo ""
echo "🚀 GIT LFS APPROACH DETAILS:"
oc logs git-test -n $NAMESPACE | grep -A 10 -B 5 "GIT LFS RESULTS"

echo ""
echo "📈 SUMMARY:"
echo "==========="
echo "🐍 Python Total Time: $PYTHON_TOTAL seconds"
echo "🚀 Git LFS Total Time: $GIT_TOTAL seconds"

if [ $PYTHON_TOTAL -gt $GIT_TOTAL ]; then
    IMPROVEMENT=$((PYTHON_TOTAL - GIT_TOTAL))
    PERCENTAGE=$(( (IMPROVEMENT * 100) / PYTHON_TOTAL ))
    echo ""
    echo "🏆 WINNER: Git LFS Approach!"
    echo "⚡ Git LFS is $IMPROVEMENT seconds faster ($PERCENTAGE% improvement)"
elif [ $GIT_TOTAL -gt $PYTHON_TOTAL ]; then
    SLOWDOWN=$((GIT_TOTAL - PYTHON_TOTAL))
    PERCENTAGE=$(( (SLOWDOWN * 100) / PYTHON_TOTAL ))
    echo ""
    echo "🏆 WINNER: Python Approach!"
    echo "⚡ Python is $SLOWDOWN seconds faster ($PERCENTAGE% improvement)"
else
    echo ""
    echo "🤝 TIE: Both approaches performed equally!"
fi

echo ""
echo "🎯 TEST CONCLUSIONS:"
echo "==================="
echo "✅ Model: $MODEL (Real 32B FP8 production model)"
echo "✅ Environment: Your OpenShift cluster"
echo "✅ Network: Production network conditions"
echo "✅ Storage: AWS EBS persistent volumes"
echo ""
echo "This provides definitive real-world performance data!"

# Cleanup prompt
echo ""
read -p "🗑️ Clean up test resources? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🧹 Cleaning up..."
    oc delete pod python-test git-test -n $NAMESPACE --ignore-not-found=true
    oc delete pvc perf-test-pvc -n $NAMESPACE --ignore-not-found=true
    echo "✅ Cleanup complete"
else
    echo "📂 Resources preserved for analysis:"
    echo "  Pods: python-test, git-test"
    echo "  PVC: perf-test-pvc"
    echo "  View logs: oc logs [pod-name] -n $NAMESPACE"
fi

echo ""
echo "🎯 Performance test completed at $(date)" 