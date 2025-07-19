#!/bin/bash

# Simplified Performance Test: Old Python vs New Git LFS
# This version avoids YAML complexity by using separate files

set -e

NAMESPACE="tag-ai--runtime-int"
MODEL="microsoft/DialoGPT-small"  # Small model for faster testing

echo "=== Simplified Model Download Performance Test ==="
echo "Model: $MODEL"
echo "Namespace: $NAMESPACE"
echo "$(date)"
echo ""

# Test 1: Python approach timing
echo "🔬 TEST 1: OLD PYTHON APPROACH"
echo "==============================="

PYTHON_START=$(date +%s)
echo "Starting Python test at $(date)"

kubectl run python-test-$RANDOM \
  --image=python:3.11-slim \
  --rm -i --tty \
  --namespace=$NAMESPACE \
  --labels="paas.redhat.com/appcode=TAG-001,app=performance-test" \
  --command -- /bin/bash -c "
    echo 'Python test starting...'
    START_TIME=\$(date +%s)
    
    echo 'Installing dependencies...'
    DEP_START=\$(date +%s)
    pip install --quiet --no-cache-dir huggingface-hub transformers torch
    DEP_END=\$(date +%s)
    DEP_TIME=\$((DEP_END - DEP_START))
    echo \"Dependencies: \$DEP_TIME seconds\"
    
    echo 'Downloading model...'
    DOWNLOAD_START=\$(date +%s)
    python3 -c \"
from huggingface_hub import snapshot_download
import time
start = time.time()
snapshot_download('$MODEL', cache_dir='/tmp/cache', resume_download=True)
end = time.time()
print(f'Download time: {end-start:.1f} seconds')
\"
    DOWNLOAD_END=\$(date +%s)
    DOWNLOAD_TIME=\$((DOWNLOAD_END - DOWNLOAD_START))
    
    TOTAL_END=\$(date +%s)
    TOTAL_TIME=\$((TOTAL_END - START_TIME))
    
    echo \"=== PYTHON RESULTS ===\"
    echo \"Dependencies: \$DEP_TIME seconds\"
    echo \"Download: \$DOWNLOAD_TIME seconds\"
    echo \"Total: \$TOTAL_TIME seconds\"
    
    # Memory info
    echo \"Memory usage:\"
    free -h | head -2
    
    # Cache size
    echo \"Cache size:\"
    du -sh /tmp/cache
  "

PYTHON_END=$(date +%s)
PYTHON_TOTAL=$((PYTHON_END - PYTHON_START))

echo ""
echo "🔬 TEST 2: NEW GIT LFS APPROACH"
echo "==============================="

GIT_START=$(date +%s)
echo "Starting Git LFS test at $(date)"

kubectl run git-test-$RANDOM \
  --image=alpine/git:latest \
  --rm -i --tty \
  --namespace=$NAMESPACE \
  --labels="paas.redhat.com/appcode=TAG-001,app=performance-test" \
  --command -- /bin/sh -c "
    echo 'Git LFS test starting...'
    START_TIME=\$(date +%s)
    
    echo 'Installing dependencies...'
    DEP_START=\$(date +%s)
    apk add --quiet --no-cache git-lfs aria2 curl
    git lfs install --skip-repo
    DEP_END=\$(date +%s)
    DEP_TIME=\$((DEP_END - DEP_START))
    echo \"Dependencies: \$DEP_TIME seconds\"
    
    echo 'Downloading model...'
    DOWNLOAD_START=\$(date +%s)
    
    cd /tmp
    git config --global user.name 'Test'
    git config --global user.email 'test@example.com'
    
    MODEL_DIR=\$(echo '$MODEL' | sed 's/\//-/g')
    
    # Clone without LFS files first
    GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 \
      'https://huggingface.co/$MODEL' \"\$MODEL_DIR\"
    
    cd \"\$MODEL_DIR\"
    
    # Download LFS files
    git lfs pull || {
      echo 'LFS failed, trying aria2...'
      for file in \$(git lfs ls-files | awk '{print \$3}'); do
        aria2c -x 4 -s 4 -k 1M -c \
          \"https://huggingface.co/$MODEL/resolve/main/\$file\" \
          -o \"\$file\"
      done
    }
    
    DOWNLOAD_END=\$(date +%s)
    DOWNLOAD_TIME=\$((DOWNLOAD_END - DOWNLOAD_START))
    
    TOTAL_END=\$(date +%s)
    TOTAL_TIME=\$((TOTAL_END - START_TIME))
    
    echo \"=== GIT LFS RESULTS ===\"
    echo \"Dependencies: \$DEP_TIME seconds\"
    echo \"Download: \$DOWNLOAD_TIME seconds\"
    echo \"Total: \$TOTAL_TIME seconds\"
    
    # Memory info (Alpine style)
    echo \"Memory usage:\"
    cat /proc/meminfo | head -3
    
    # Cache size
    echo \"Cache size:\"
    du -sh /tmp/\$MODEL_DIR
  "

GIT_END=$(date +%s)
GIT_TOTAL=$((GIT_END - GIT_START))

echo ""
echo "📊 FINAL PERFORMANCE COMPARISON"
echo "================================"
echo ""
echo "🐍 Python Approach Total: $PYTHON_TOTAL seconds"
echo "🚀 Git LFS Approach Total: $GIT_TOTAL seconds"
echo ""

if [ $PYTHON_TOTAL -gt $GIT_TOTAL ]; then
    IMPROVEMENT=$((PYTHON_TOTAL - GIT_TOTAL))
    PERCENTAGE=$(( (IMPROVEMENT * 100) / PYTHON_TOTAL ))
    echo "⚡ Git LFS is $IMPROVEMENT seconds faster ($PERCENTAGE% improvement)"
    echo "✅ Winner: Git LFS Approach!"
elif [ $GIT_TOTAL -gt $PYTHON_TOTAL ]; then
    SLOWDOWN=$((GIT_TOTAL - PYTHON_TOTAL))
    PERCENTAGE=$(( (SLOWDOWN * 100) / PYTHON_TOTAL ))
    echo "⚠️  Python was $SLOWDOWN seconds faster ($PERCENTAGE% better)"
    echo "🐍 Winner: Python Approach!"
else
    echo "🤝 Both approaches took the same time!"
fi

echo ""
echo "🎯 Test completed at $(date)" 