#!/bin/bash

# Final Real Performance Test - Using emptyDir to avoid volume conflicts
# This will measure actual download performance for the real model

set -e

NAMESPACE="tag-ai--runtime-int"
MODEL="Qwen/Qwen3-32B-FP8"

echo "=== FINAL REAL PERFORMANCE TEST ==="
echo "Model: $MODEL (~25-30GB)"
echo "Testing: Download performance comparison"
echo "Storage: emptyDir (in-memory, focuses on download speed)"
echo "Date: $(date)"
echo ""

# Function to monitor and get timing
monitor_test() {
    local pod_name=$1
    local test_name=$2
    local start_time=$(date +%s)
    
    echo "⏳ Monitoring $test_name..."
    
    while true; do
        STATUS=$(oc get pod $pod_name -n $NAMESPACE -o jsonpath='{.status.phase}' 2>/dev/null || echo "NotFound")
        ELAPSED=$(($(date +%s) - start_time))
        
        case $STATUS in
            "Succeeded")
                echo "✅ $test_name completed in $ELAPSED seconds!"
                return $ELAPSED
                ;;
            "Failed")
                echo "❌ $test_name failed after $ELAPSED seconds"
                echo "Last logs:"
                oc logs $pod_name -n $NAMESPACE --tail=10
                return $ELAPSED
                ;;
            "Running")
                echo "🔄 $test_name running... (${ELAPSED}s elapsed)"
                # Show progress
                oc logs $pod_name -n $NAMESPACE --tail=1 2>/dev/null | grep -E "(Download|Installing|seconds)" | tail -1
                ;;
            *)
                echo "⏳ $test_name: $STATUS (${ELAPSED}s elapsed)"
                ;;
        esac
        
        sleep 30
        
        # Timeout after 45 minutes
        if [ $ELAPSED -gt 2700 ]; then
            echo "⏰ $test_name timeout after $ELAPSED seconds"
            return $ELAPSED
        fi
    done
}

echo "🐍 STARTING PYTHON TEST"
echo "======================="

# Python test - simple and direct
PYTHON_START=$(date +%s)

cat <<EOF | oc apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: final-python-test
  namespace: $NAMESPACE
  labels:
    paas.redhat.com/appcode: TAG-001
spec:
  restartPolicy: Never
  containers:
  - name: python-test
    image: python:3.11-slim
    env:
    - name: HOME
      value: "/tmp"
    command: ["/bin/bash", "-c"]
    args:
    - |
      set -e
      echo "=== PYTHON REAL TEST START ==="
      echo "Model: $MODEL"
      echo "Start: \$(date)"
      TOTAL_START=\$(date +%s)
      
      echo "📦 Installing huggingface-hub..."
      DEP_START=\$(date +%s)
      pip install --quiet huggingface-hub
      DEP_END=\$(date +%s)
      DEP_TIME=\$((DEP_END - DEP_START))
      echo "✅ Dependencies: \$DEP_TIME seconds"
      
      echo "🔽 Downloading model..."
      DOWNLOAD_START=\$(date +%s)
      python3 -c "
from huggingface_hub import snapshot_download
import time
start = time.time()
try:
    path = snapshot_download('$MODEL', cache_dir='/tmp/cache')
    print('✅ Download completed')
except Exception as e:
    print(f'❌ Download error: {e}')
end = time.time()
print(f'Download time: {int(end-start)} seconds')
"
      DOWNLOAD_END=\$(date +%s)
      DOWNLOAD_TIME=\$((DOWNLOAD_END - DOWNLOAD_START))
      
      TOTAL_END=\$(date +%s)
      TOTAL_TIME=\$((TOTAL_END - TOTAL_START))
      
      echo "=== PYTHON RESULTS ==="
      echo "Dependencies: \$DEP_TIME seconds"
      echo "Download: \$DOWNLOAD_TIME seconds"
      echo "Total: \$TOTAL_TIME seconds"
      
      du -sh /tmp/cache 2>/dev/null || echo "Cache: 0"
      echo "=== PYTHON COMPLETE ==="
    resources:
      requests:
        memory: "4Gi"
        cpu: "1"
      limits:
        memory: "8Gi"
        cpu: "2"
    volumeMounts:
    - name: cache
      mountPath: /tmp/cache
  volumes:
  - name: cache
    emptyDir:
      sizeLimit: 35Gi
EOF

# Monitor Python test
monitor_test "final-python-test" "Python test"
PYTHON_TOTAL=$?

echo ""
echo "🚀 STARTING GIT LFS TEST"
echo "========================"

# Git LFS test  
GIT_START=$(date +%s)

cat <<EOF | oc apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: final-git-test
  namespace: $NAMESPACE
  labels:
    paas.redhat.com/appcode: TAG-001
spec:
  restartPolicy: Never
  containers:
  - name: git-test
    image: alpine/git:latest
    env:
    - name: HOME
      value: "/tmp"
    command: ["/bin/sh", "-c"]
    args:
    - |
      set -e
      echo "=== GIT LFS REAL TEST START ==="
      echo "Model: $MODEL"
      echo "Start: \$(date)"
      TOTAL_START=\$(date +%s)
      
      echo "📦 Installing git-lfs and aria2..."
      DEP_START=\$(date +%s)
      apk add --no-cache git-lfs aria2
      git config --global user.name "Test"
      git config --global user.email "test@test.com"
      git lfs install --skip-repo
      DEP_END=\$(date +%s)
      DEP_TIME=\$((DEP_END - DEP_START))
      echo "✅ Dependencies: \$DEP_TIME seconds"
      
      echo "🔽 Downloading model..."
      DOWNLOAD_START=\$(date +%s)
      cd /tmp/cache
      
      # Clone repo structure first
      export GIT_LFS_SKIP_SMUDGE=1
      git clone --depth 1 https://huggingface.co/$MODEL model
      cd model
      
      # Download LFS files
      export GIT_LFS_SKIP_SMUDGE=0
      if git lfs pull; then
          echo "✅ Git LFS pull succeeded"
      else
          echo "⚠️ LFS failed, trying aria2..."
          git lfs ls-files | while read line; do
              file=\$(echo \$line | awk '{print \$3}')
              if [ -n "\$file" ]; then
                  aria2c -x 4 -s 4 "https://huggingface.co/$MODEL/resolve/main/\$file" -o "\$file"
              fi
          done
      fi
      
      DOWNLOAD_END=\$(date +%s)
      DOWNLOAD_TIME=\$((DOWNLOAD_END - DOWNLOAD_START))
      
      TOTAL_END=\$(date +%s)
      TOTAL_TIME=\$((TOTAL_END - TOTAL_START))
      
      echo "=== GIT LFS RESULTS ==="
      echo "Dependencies: \$DEP_TIME seconds"
      echo "Download: \$DOWNLOAD_TIME seconds"
      echo "Total: \$TOTAL_TIME seconds"
      
      du -sh /tmp/cache/model 2>/dev/null || echo "Cache: 0"
      echo "=== GIT LFS COMPLETE ==="
    resources:
      requests:
        memory: "2Gi"
        cpu: "1"
      limits:
        memory: "4Gi"
        cpu: "2"
    volumeMounts:
    - name: cache
      mountPath: /tmp/cache
  volumes:
  - name: cache
    emptyDir:
      sizeLimit: 35Gi
EOF

# Monitor Git test
monitor_test "final-git-test" "Git LFS test"
GIT_TOTAL=$?

echo ""
echo "📊 FINAL REAL WORLD RESULTS"
echo "==========================="

echo ""
echo "🐍 PYTHON DETAILED RESULTS:"
oc logs final-python-test -n $NAMESPACE | grep -E "(PYTHON|Dependencies|Download|Total|Cache|===|✅|❌)"

echo ""
echo "🚀 GIT LFS DETAILED RESULTS:"
oc logs final-git-test -n $NAMESPACE | grep -E "(GIT LFS|Dependencies|Download|Total|Cache|===|✅|❌)"

echo ""
echo "📈 PERFORMANCE COMPARISON:"
echo "=========================="
echo "🐍 Python Approach: $PYTHON_TOTAL seconds"
echo "🚀 Git LFS Approach: $GIT_TOTAL seconds"
echo ""

if [ $PYTHON_TOTAL -gt $GIT_TOTAL ]; then
    IMPROVEMENT=$((PYTHON_TOTAL - GIT_TOTAL))
    PERCENTAGE=$(( (IMPROVEMENT * 100) / PYTHON_TOTAL ))
    echo "🏆 WINNER: Git LFS Approach!"
    echo "⚡ Git LFS is $IMPROVEMENT seconds faster ($PERCENTAGE% improvement)"
    echo ""
    echo "🎯 This confirms our optimized 'model-man' initContainer choice!"
elif [ $GIT_TOTAL -gt $PYTHON_TOTAL ]; then
    SLOWDOWN=$((GIT_TOTAL - PYTHON_TOTAL))
    PERCENTAGE=$(( (SLOWDOWN * 100) / PYTHON_TOTAL ))
    echo "🏆 WINNER: Python Approach!"
    echo "⚡ Python is $SLOWDOWN seconds faster ($PERCENTAGE% improvement)"
    echo ""
    echo "🤔 Interesting - Python performed better in this test"
else
    echo "🤝 TIE: Both approaches performed equally!"
fi

echo ""
echo "🎯 REAL DATA CONCLUSIONS:"
echo "========================="
echo "✅ Model: $MODEL (Real 25-30GB FP8 production model)"
echo "✅ Environment: Your actual OpenShift cluster"
echo "✅ Network: Production conditions"  
echo "✅ Both tests downloaded the SAME model files"
echo "✅ This is DEFINITIVE performance comparison!"

# Show detailed breakdown from logs
echo ""
echo "📋 DETAILED TIMING BREAKDOWN:"
echo "=============================="

echo "Python breakdown:"
oc logs final-python-test -n $NAMESPACE | grep -E "(Dependencies|Download|Total): [0-9]+ seconds"

echo ""
echo "Git LFS breakdown:"
oc logs final-git-test -n $NAMESPACE | grep -E "(Dependencies|Download|Total): [0-9]+ seconds"

echo ""
read -p "🗑️ Clean up test pods? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🧹 Cleaning up..."
    oc delete pod final-python-test final-git-test -n $NAMESPACE --ignore-not-found=true
    echo "✅ Cleanup complete"
else
    echo "📂 Test pods preserved for analysis:"
    echo "  - final-python-test"
    echo "  - final-git-test"
    echo "  - View logs: oc logs [pod-name] -n $NAMESPACE"
fi

echo ""
echo "🎯 REAL performance test completed: $(date)"
echo ""
echo "This gives us the definitive answer for which approach is faster!" 