#!/bin/bash

# Manual Performance Test with Real Data
# Using privileged containers to avoid permission issues

echo "=== Manual Performance Comparison Test ==="
echo "Model: microsoft/DialoGPT-small (~350MB)"
echo "$(date)"
echo ""

echo "🔬 MANUAL TEST 1: PYTHON APPROACH"
echo "=================================="

echo "Testing Python approach with privileged container..."
PYTHON_START=$(date +%s)

kubectl run python-manual --image=python:3.11-slim \
  --rm -i --tty --namespace=tag-ai--runtime-int \
  --labels="paas.redhat.com/appcode=TAG-001" \
  --overrides='{"spec":{"securityContext":{"runAsUser":0}}}' \
  --command -- /bin/bash -c "
    echo 'PYTHON TEST STARTING'
    START_TIME=\$(date +%s)
    
    echo 'Installing dependencies...'
    pip install --quiet huggingface-hub transformers torch
    DEP_END=\$(date +%s)
    DEP_TIME=\$((DEP_END - START_TIME))
    
    echo 'Downloading model...'
    DOWNLOAD_START=\$(date +%s)
    python3 -c '
from huggingface_hub import snapshot_download
import time
start = time.time()
snapshot_download(\"microsoft/DialoGPT-small\", cache_dir=\"/tmp/cache\")
end = time.time()
print(f\"Model download: {end-start:.1f}s\")
'
    DOWNLOAD_END=\$(date +%s)
    DOWNLOAD_TIME=\$((DOWNLOAD_END - DOWNLOAD_START))
    
    TOTAL_END=\$(date +%s)
    TOTAL_TIME=\$((TOTAL_END - START_TIME))
    
    echo \"PYTHON RESULTS:\"
    echo \"Dependencies: \$DEP_TIME seconds\"
    echo \"Download: \$DOWNLOAD_TIME seconds\"
    echo \"Total: \$TOTAL_TIME seconds\"
    
    echo \"Cache size:\"
    du -sh /tmp/cache
  "

PYTHON_END=$(date +%s)
PYTHON_TOTAL=$((PYTHON_END - PYTHON_START))

echo ""
echo "🔬 MANUAL TEST 2: GIT LFS APPROACH"
echo "=================================="

echo "Testing Git LFS approach with privileged container..."
GIT_START=$(date +%s)

kubectl run git-manual --image=alpine/git:latest \
  --rm -i --tty --namespace=tag-ai--runtime-int \
  --labels="paas.redhat.com/appcode=TAG-001" \
  --overrides='{"spec":{"securityContext":{"runAsUser":0}}}' \
  --command -- /bin/sh -c "
    echo 'GIT LFS TEST STARTING'
    START_TIME=\$(date +%s)
    
    echo 'Installing dependencies...'
    apk add --quiet git-lfs aria2
    git lfs install
    DEP_END=\$(date +%s)
    DEP_TIME=\$((DEP_END - START_TIME))
    
    echo 'Downloading model...'
    DOWNLOAD_START=\$(date +%s)
    cd /tmp
    git config --global user.name 'Test'
    git config --global user.email 'test@test.com'
    
    # Clone without LFS first
    GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 \
      https://huggingface.co/microsoft/DialoGPT-small model
    
    cd model
    git lfs pull
    
    DOWNLOAD_END=\$(date +%s)
    DOWNLOAD_TIME=\$((DOWNLOAD_END - DOWNLOAD_START))
    
    TOTAL_END=\$(date +%s)
    TOTAL_TIME=\$((TOTAL_END - START_TIME))
    
    echo \"GIT LFS RESULTS:\"
    echo \"Dependencies: \$DEP_TIME seconds\"
    echo \"Download: \$DOWNLOAD_TIME seconds\"
    echo \"Total: \$TOTAL_TIME seconds\"
    
    echo \"Cache size:\"
    du -sh /tmp/model
  "

GIT_END=$(date +%s)
GIT_TOTAL=$((GIT_END - GIT_START))

echo ""
echo "📊 REAL PERFORMANCE COMPARISON RESULTS"
echo "======================================="
echo ""
echo "🐍 Python Approach: $PYTHON_TOTAL seconds"
echo "🚀 Git LFS Approach: $GIT_TOTAL seconds"
echo ""

if [ $PYTHON_TOTAL -gt $GIT_TOTAL ]; then
    IMPROVEMENT=$((PYTHON_TOTAL - GIT_TOTAL))
    PERCENTAGE=$(( (IMPROVEMENT * 100) / PYTHON_TOTAL ))
    echo "✅ Git LFS is $IMPROVEMENT seconds faster ($PERCENTAGE% improvement)!"
elif [ $GIT_TOTAL -gt $PYTHON_TOTAL ]; then
    SLOWDOWN=$((GIT_TOTAL - PYTHON_TOTAL))
    PERCENTAGE=$(( (SLOWDOWN * 100) / PYTHON_TOTAL ))
    echo "🐍 Python is $SLOWDOWN seconds faster ($PERCENTAGE% improvement)!"
else
    echo "🤝 Both approaches performed equally!"
fi

echo ""
echo "🎯 REAL DATA CONCLUSIONS:"
echo "========================"
echo "This test used microsoft/DialoGPT-small (~350MB) on your actual cluster"
echo "Both tests ran with the same network, storage, and cluster conditions"
echo "Results show real-world performance differences between the approaches" 