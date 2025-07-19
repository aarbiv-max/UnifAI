#!/bin/bash

# Performance Comparison Test: Old Python vs New Git LFS Approach
# This script tests both approaches and provides real performance data

set -e

NAMESPACE="tag-ai--runtime-int"
MODEL="microsoft/DialoGPT-small"  # Use smaller model for faster testing
TEST_PVC="performance-test-cache"

echo "=== Model Download Performance Comparison Test ==="
echo "Model: $MODEL (small model for faster testing)"
echo "Namespace: $NAMESPACE"
echo "$(date)"
echo ""

# Function to cleanup test resources
cleanup() {
    echo "🧹 Cleaning up test resources..."
    oc delete pvc $TEST_PVC -n $NAMESPACE --ignore-not-found=true
    oc delete job test-python-approach -n $NAMESPACE --ignore-not-found=true
    oc delete job test-git-lfs-approach -n $NAMESPACE --ignore-not-found=true
}

# Function to wait for job completion and get results
wait_for_job() {
    local job_name=$1
    local start_time=$(date +%s)
    
    echo "⏳ Waiting for job $job_name to complete..."
    
    while true; do
        local status=$(oc get job $job_name -n $NAMESPACE -o jsonpath='{.status.conditions[0].type}' 2>/dev/null || echo "NotFound")
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        case $status in
            "Complete")
                echo "✅ Job $job_name completed in ${elapsed} seconds"
                return $elapsed
                ;;
            "Failed")
                echo "❌ Job $job_name failed"
                oc logs job/$job_name -n $NAMESPACE
                return -1
                ;;
            *)
                if [ $elapsed -gt 1800 ]; then  # 30 minute timeout
                    echo "⏰ Job $job_name timed out after 30 minutes"
                    return -1
                fi
                echo "⏳ Job $job_name still running... (${elapsed}s elapsed)"
                sleep 30
                ;;
        esac
    done
}

# Setup test PVC
echo "📦 Setting up test PVC..."
cat <<EOF | oc apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: $TEST_PVC
  namespace: $NAMESPACE
  labels:
    paas.redhat.com/appcode: TAG-001
    app: performance-test
  annotations:
    kubernetes.io/reclaimPolicy: "Delete"
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: aws-ebs
  resources:
    requests:
      storage: 20Gi
EOF

echo ""
echo "🔬 TEST 1: OLD PYTHON APPROACH"
echo "==============================="

# Test 1: Old Python Approach
cat <<EOF | oc apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: test-python-approach
  namespace: $NAMESPACE
  labels:
    paas.redhat.com/appcode: TAG-001
    app: performance-test
spec:
  ttlSecondsAfterFinished: 3600
  template:
    metadata:
      labels:
        paas.redhat.com/appcode: TAG-001
        app: performance-test
    spec:
      restartPolicy: Never
      containers:
      - name: python-downloader
        image: python:3.11-slim
        command: ["/bin/bash", "-c"]
        args:
        - |
          set -e
          
          echo "=== OLD PYTHON APPROACH TEST ==="
          echo "Start time: \$(date)"
          echo "Model: $MODEL"
          START_TIME=\$(date +%s)
          
          # Track memory usage
          echo "Initial memory usage:"
          free -h
          
          echo "📦 Installing Python dependencies..."
          DEP_START=\$(date +%s)
          pip install --no-cache-dir huggingface-hub transformers torch
          DEP_END=\$(date +%s)
          DEP_TIME=\$((DEP_END - DEP_START))
          echo "✅ Dependencies installed in \$DEP_TIME seconds"
          
          echo "Memory after dependencies:"
          free -h
          
          echo "📥 Downloading model with Python..."
          DOWNLOAD_START=\$(date +%s)
          
          python3 << 'PYEOF'
import os
import time
from huggingface_hub import snapshot_download
from transformers import AutoTokenizer

model_name = "$MODEL"
cache_dir = "/models/.cache"

print(f"Downloading {model_name}...")
start_time = time.time()

try:
    # Download model
    snapshot_download(
        repo_id=model_name,
        cache_dir=cache_dir,
        resume_download=True
    )
    
    # Download tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        cache_dir=cache_dir
    )
    
    end_time = time.time()
    duration = end_time - start_time
    print(f"✅ Download completed in {duration:.1f} seconds")
    
except Exception as e:
    print(f"❌ Download failed: {e}")
    exit(1)
PYEOF
          
          DOWNLOAD_END=\$(date +%s)
          DOWNLOAD_TIME=\$((DOWNLOAD_END - DOWNLOAD_START))
          
          TOTAL_END=\$(date +%s)
          TOTAL_TIME=\$((TOTAL_END - START_TIME))
          
          echo ""
          echo "=== PYTHON APPROACH RESULTS ==="
          echo "Dependencies time: \$DEP_TIME seconds"
          echo "Download time: \$DOWNLOAD_TIME seconds" 
          echo "Total time: \$TOTAL_TIME seconds"
          echo "Final memory usage:"
          free -h
          echo "Cache size:"
          du -sh /models/.cache
        resources:
          requests:
            cpu: "1"
            memory: "2Gi"
          limits:
            cpu: "4"
            memory: "8Gi"
        volumeMounts:
        - name: test-cache
          mountPath: /models
      volumes:
      - name: test-cache
        persistentVolumeClaim:
          claimName: $TEST_PVC
EOF

# Wait for Python test to complete
python_time=$(wait_for_job "test-python-approach")
python_logs=$(oc logs job/test-python-approach -n $NAMESPACE)

echo ""
echo "🔬 TEST 2: NEW GIT LFS APPROACH"  
echo "==============================="

# Clean cache for fair comparison
oc exec job/test-python-approach -n $NAMESPACE -- rm -rf /models/.cache/* || true

# Test 2: New Git LFS Approach  
cat <<EOF | oc apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: test-git-lfs-approach
  namespace: $NAMESPACE
  labels:
    paas.redhat.com/appcode: TAG-001
    app: performance-test
spec:
  ttlSecondsAfterFinished: 3600
  template:
    metadata:
      labels:
        paas.redhat.com/appcode: TAG-001
        app: performance-test
    spec:
      restartPolicy: Never
      containers:
      - name: git-lfs-downloader
        image: alpine/git:latest
        command: ["/bin/sh", "-c"]
        args:
        - |
          set -e
          
          echo "=== NEW GIT LFS APPROACH TEST ==="
          echo "Start time: \$(date)"
          echo "Model: $MODEL"
          START_TIME=\$(date +%s)
          
          # Track memory usage (Alpine style)
          echo "Initial memory usage:"
          cat /proc/meminfo | head -3
          
          echo "📦 Installing Git LFS dependencies..."
          DEP_START=\$(date +%s)
          apk add --no-cache git-lfs aria2 curl
          git lfs install --skip-repo
          DEP_END=\$(date +%s)
          DEP_TIME=\$((DEP_END - DEP_START))
          echo "✅ Dependencies installed in \$DEP_TIME seconds"
          
          echo "Memory after dependencies:"
          cat /proc/meminfo | head -3
          
          echo "📥 Downloading model with Git LFS..."
          DOWNLOAD_START=\$(date +%s)
          
          cd /models/.cache
          
          # Git LFS download
          git config --global user.name "Test"
          git config --global user.email "test@example.com"
          
          MODEL_DIR=\$(echo "$MODEL" | sed 's/\//-/g')
          
          echo "Cloning repository..."
          GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 \
            "https://huggingface.co/$MODEL" "\$MODEL_DIR"
          
          cd "\$MODEL_DIR"
          
          echo "Downloading LFS files..."
          git lfs pull || {
            echo "Trying aria2 fallback..."
            for file in \$(git lfs ls-files | awk '{print \$3}'); do
              aria2c -x 4 -s 4 -k 1M -c \
                "https://huggingface.co/$MODEL/resolve/main/\$file" \
                -o "\$file"
            done
          }
          
          DOWNLOAD_END=\$(date +%s)
          DOWNLOAD_TIME=\$((DOWNLOAD_END - DOWNLOAD_START))
          
          TOTAL_END=\$(date +%s)
          TOTAL_TIME=\$((TOTAL_END - START_TIME))
          
          echo ""
          echo "=== GIT LFS APPROACH RESULTS ==="
          echo "Dependencies time: \$DEP_TIME seconds"
          echo "Download time: \$DOWNLOAD_TIME seconds"
          echo "Total time: \$TOTAL_TIME seconds"
          echo "Final memory usage:"
          cat /proc/meminfo | head -3
          echo "Cache size:"
          du -sh /models/.cache
        resources:
          requests:
            cpu: "1"
            memory: "2Gi"
          limits:
            cpu: "4"
            memory: "8Gi"
        volumeMounts:
        - name: test-cache
          mountPath: /models
      volumes:
      - name: test-cache
        persistentVolumeClaim:
          claimName: $TEST_PVC
EOF

# Wait for Git LFS test to complete
git_lfs_time=$(wait_for_job "test-git-lfs-approach")
git_lfs_logs=$(oc logs job/test-git-lfs-approach -n $NAMESPACE)

echo ""
echo "📊 PERFORMANCE COMPARISON RESULTS"
echo "=================================="
echo ""

if [ "$python_time" -gt 0 ] && [ "$git_lfs_time" -gt 0 ]; then
    improvement=$((python_time - git_lfs_time))
    percentage=$(( (improvement * 100) / python_time ))
    
    echo "🐍 Python Approach: $python_time seconds"
    echo "🚀 Git LFS Approach: $git_lfs_time seconds"
    echo ""
    echo "⚡ Performance Improvement: $improvement seconds ($percentage% faster)"
    
    if [ $improvement -gt 0 ]; then
        echo "✅ Git LFS approach is faster!"
    else
        echo "⚠️  Python approach was faster in this test"
    fi
else
    echo "❌ One or both tests failed, check logs above"
fi

echo ""
echo "📝 Detailed Logs:"
echo ""
echo "=== PYTHON APPROACH LOGS ==="
echo "$python_logs"
echo ""
echo "=== GIT LFS APPROACH LOGS ==="
echo "$git_lfs_logs"

# Cleanup
echo ""
read -p "🧹 Clean up test resources? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cleanup
    echo "✅ Cleanup completed"
fi 