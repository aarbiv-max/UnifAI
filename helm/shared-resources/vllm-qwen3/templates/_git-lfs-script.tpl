{{/*
Git LFS Model Download Script Template
This template provides the shared Git LFS logic for model downloading
that can be used in both initContainers and standalone jobs.

Usage:
{{- include "vllm-qwen3.gitLfsScript" . }}

Parameters can be passed via context:
- .Values.vllm.model - Model identifier (e.g., "Qwen/Qwen3-32B-FP8")
- .Values.volumes.modelCache.forceRedownload - Force redownload flag
- .installTools - Whether to install git-lfs and aria2 (default: false for initContainer)
*/}}
{{- define "vllm-qwen3.gitLfsScript" -}}
set -e
echo "=== Optimized Git LFS Model Preloader ==="
echo "Model: {{ .Values.vllm.model }}"
echo "Cache directory: /models/.cache"
{{- if hasKey .Values.volumes.modelCache "forceRedownload" }}
echo "Force redownload: {{ .Values.volumes.modelCache.forceRedownload }}"
{{- end }}
echo "Timestamp: $(date)"
echo ""

{{- if .installTools }}
# Install required tools (git-lfs + aria2 for better performance)
echo "Setting up download tools..."
apk add --no-cache git-lfs aria2 curl
git lfs install --skip-repo
{{- else }}
# Check if git-lfs and aria2 are available, if not use basic tools
echo "Checking available tools..."
if command -v git-lfs >/dev/null 2>&1; then
  echo "✅ git-lfs available"
  git lfs install --skip-repo
else
  echo "⚠️ git-lfs not available, will use basic git"
fi
{{- end }}

# Create cache directory structure
mkdir -p /models/.cache
cd /models/.cache

# Check available space
echo "Available disk space:"
df -h /models/
echo ""

# Extract model organization and name for directory structure
{{- $modelParts := splitList "/" .Values.vllm.model }}
MODEL_ORG="{{ index $modelParts 0 }}"
MODEL_NAME="{{ index $modelParts 1 }}"
MODEL_DIR="models--${MODEL_ORG}--${MODEL_NAME}"

echo "Model info:"
echo "  Organization: $MODEL_ORG"
echo "  Model Name: $MODEL_NAME"
echo "  Directory: $MODEL_DIR"
echo ""

# Check if model is already cached (following hfd.sh pattern)
{{- if hasKey .Values.volumes.modelCache "forceRedownload" }}
if [ "{{ .Values.volumes.modelCache.forceRedownload }}" != "true" ] && [ -d "$MODEL_DIR" ]; then
{{- else }}
if [ -d "$MODEL_DIR" ]; then
{{- end }}
  echo "✅ Existing model directory found, validating..."
  cd "$MODEL_DIR"
  
  # Check if it's a git repository, if not that's okay too
  if [ -d ".git" ] && git status >/dev/null 2>&1; then
    echo "🔄 Git repository detected, updating..."
    GIT_LFS_SKIP_SMUDGE=1 git pull || {
      echo "⚠️  Git pull failed, but will use existing model"
    }
  else
    echo "✅ Using existing cached model files"
  fi
{{- if hasKey .Values.volumes.modelCache "forceRedownload" }}
elif [ "{{ .Values.volumes.modelCache.forceRedownload }}" = "true" ]; then
  echo "🔄 Force redownload enabled, cleaning existing cache..."
  rm -rf "$MODEL_DIR"
{{- end }}
fi

# Clone repository if needed (following proven hfd.sh pattern)
if [ ! -d "$MODEL_DIR/.git" ]; then
  echo "📥 Cloning model repository..."
  echo "Repository: https://huggingface.co/{{ .Values.vllm.model }}"
  
  # Set git config for the operation
  git config --global user.name "vLLM Model Loader"
  git config --global user.email "vllm@cluster.local"
  git config --global advice.detachedHead false
  
  # Clone without LFS files first (much faster)
  REPO_URL="https://huggingface.co/{{ .Values.vllm.model }}"
  GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 --single-branch "$REPO_URL" "$MODEL_DIR" || {
    echo "❌ Git clone failed"
    exit 1
  }
  
  cd "$MODEL_DIR"
  
  # Clear any placeholder LFS files
  echo "🧹 Preparing LFS files..."
  for file in $(git lfs ls-files | awk '{print $3}'); do
    if [ -f "$file" ]; then
      truncate -s 0 "$file"
    fi
  done
else
  cd "$MODEL_DIR"
fi

# Download LFS files using optimized approach
echo ""
echo "📦 Downloading LFS files..."

# Get list of LFS files
LFS_FILES=$(git lfs ls-files | awk '{print $3}')
if [ -z "$LFS_FILES" ]; then
  echo "✅ No LFS files to download"
else
  echo "LFS files to download:"
  echo "$LFS_FILES" | head -5
  [ $(echo "$LFS_FILES" | wc -l) -gt 5 ] && echo "... and $(echo "$LFS_FILES" | wc -l | awk '{print $1-5}') more"
  echo ""
  
{{- if .installTools }}
  # Download with git lfs (uses built-in resumability and chunking)
  git lfs pull || {
    echo "⚠️  git lfs pull failed, trying alternative download..."
    
    # Fallback: download files individually with aria2
    for file in $LFS_FILES; do
      echo "📥 Downloading $file with aria2..."
      file_dir=$(dirname "$file")
      mkdir -p "$file_dir"
      
      url="https://huggingface.co/{{ .Values.vllm.model }}/resolve/main/$file"
      aria2c -x 4 -s 4 -k 1M -c "$url" -d "$file_dir" -o "$(basename "$file")" || {
        echo "❌ Failed to download $file"
        exit 1
      }
    done
  }
{{- else }}
  # Download with git lfs if available, otherwise skip
  if command -v git-lfs >/dev/null 2>&1; then
    git lfs pull || {
      echo "⚠️  git lfs pull failed, but model may already be cached"
    }
  else
    echo "⚠️  git-lfs not available, assuming model is already cached"
  fi
{{- end }}
fi

# Verify the download
echo ""
echo "=== Verification ==="
echo "Repository status:"
git status --porcelain

echo ""
echo "Model directory size:"
du -sh .

echo ""
echo "Model files:"
find . -type f \( -name "*.safetensors" -o -name "*.bin" -o -name "*.json" -o -name "*.txt" \) | head -10

# Count important files
CONFIG_FILES=$(find . -name "config.json" | wc -l)
TOKENIZER_FILES=$(find . -name "tokenizer*" | wc -l)  
MODEL_FILES=$(find . \( -name "*.safetensors" -o -name "*.bin" \) | wc -l)

echo ""
echo "File summary:"
echo "  Config files: $CONFIG_FILES"
echo "  Tokenizer files: $TOKENIZER_FILES"  
echo "  Model files: $MODEL_FILES"

if [ "$CONFIG_FILES" -gt 0 ] && [ "$MODEL_FILES" -gt 0 ]; then
  echo "✅ Model download verification successful!"
else
  echo "❌ Model download verification failed!"
  echo "Expected at least 1 config file and 1 model file"
  exit 1
fi

echo ""
echo "🎉 Optimized model download completed successfully!"
echo "📁 Model cached at: /models/.cache/$MODEL_DIR"
echo "🚀 Ready for vLLM deployment!"
{{- end -}} 