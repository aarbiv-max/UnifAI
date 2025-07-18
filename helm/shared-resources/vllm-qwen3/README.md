# vLLM Qwen3-32B-FP8 Helm Chart

![vLLM](https://img.shields.io/badge/vLLM-v0.9.2-blue)
![Kubernetes](https://img.shields.io/badge/Kubernetes-1.24+-green)
![OpenShift](https://img.shields.io/badge/OpenShift-4.10+-red)
![License](https://img.shields.io/badge/License-Apache%202.0-yellow)

A production-ready Helm chart for deploying [vLLM](https://github.com/vllm-project/vllm) with the Qwen3-32B-FP8 large language model on Kubernetes/OpenShift with GPU support.

## 🎯 Overview

This Helm chart provides a complete deployment solution for running Qwen3-32B-FP8 model using vLLM inference engine with:

- **High Performance**: FP8 quantization and tensor parallelism across multiple GPUs
- **Production Ready**: Comprehensive health checks, monitoring, and auto-scaling support
- **External Access**: OpenShift Routes for external API access
- **Dynamic Configuration**: Fully configurable without hardcoded values
- **Automated Testing**: Built-in API validation tests

## 📋 Prerequisites

### Hardware Requirements
- **GPUs**: 2x NVIDIA GPUs with at least 16GB VRAM each
- **Memory**: 32GB+ RAM recommended
- **CPU**: 8+ cores recommended
- **Storage**: 50GB+ for model caching

### Software Requirements
- Kubernetes 1.24+ or OpenShift 4.10+
- Helm 3.8+
- NVIDIA GPU Operator installed
- Node with GPU tolerations configured

### Cluster Setup
```bash
# Ensure GPU nodes are properly tainted
kubectl get nodes -l nvidia.com/gpu=true

# Verify GPU operator is running
kubectl get pods -n nvidia-gpu-operator
```

## 📦 Optional: Model Preloading (Recommended)

> **⚡ Performance Boost**: Preloading the model significantly reduces vLLM startup time from **15-30 minutes** to **1-3 minutes** for subsequent deployments.

The model preloading step is **completely optional** but highly recommended for production deployments. You can choose between:

- **Option A**: Standard deployment (model downloads during vLLM startup)
- **Option B**: Preload model first, then deploy vLLM with cached model

### Option B: Preload Model (Recommended)

#### 1. Run the Automated Preloader
```bash
cd helm/shared-resources/vllm-qwen3
./preload-and-deploy.sh
```

This script will:
1. 📥 Download the Qwen3-32B-FP8 model (~30-40GB) to a persistent volume
2. ✅ Verify the model is accessible
3. 🚀 Deploy vLLM with the preloaded model cache
4. ⚡ Result: Ultra-fast vLLM startup (1-3 minutes)

#### 2. Manual Preloading (Alternative)
```bash
# Step 1: Preload the model
oc apply -f model-preloader.yaml

# Step 2: Monitor preload progress (10-20 minutes)
oc logs -f job/vllm-model-preloader -n tag-ai--runtime-int

# Step 3: Deploy vLLM with cached model
helm install vllm-qwen3 ./ \
  --namespace tag-ai--runtime-int \
  --set volumes.modelCache.enabled=true
```

### Benefits of Preloading
- ⚡ **Faster Restarts**: Pod restarts take 1-3 minutes instead of 15-30 minutes
- 🔄 **Persistent Cache**: Model persists across deployments and pod restarts  
- 📈 **Better Resource Utilization**: No model download during production startup
- 🛡️ **Reliability**: Separate model download from application deployment

## 🚀 Quick Start

> **📝 Note**: This covers **Option A** (standard deployment). For faster startup times, see the [Optional Model Preloading](#-optional-model-preloading-recommended) section above.

### 1. Install the Chart
```bash
# Add to your Helm repositories (if applicable)
helm repo add your-repo https://your-helm-repo.com
helm repo update

# Install with default configuration
helm install vllm-qwen3 ./helm/shared-resources/vllm-qwen3/ \
  --namespace your-namespace \
  --create-namespace

# Or install with custom values
helm install vllm-qwen3 ./helm/shared-resources/vllm-qwen3/ \
  --namespace your-namespace \
  --values custom-values.yaml
```

### 2. Monitor Deployment
```bash
# Check pod status 
# Note: Model loading takes 15-30 minutes for first-time deployment
#       or 1-3 minutes if using preloaded model cache
kubectl get pods -n your-namespace -l app.kubernetes.io/name=vllm-qwen3

# Monitor model loading progress
kubectl logs -f -n your-namespace -l app.kubernetes.io/name=vllm-qwen3
```

### 3. Verify Installation
```bash
# Run comprehensive API tests with adequate timeout
helm test vllm-qwen3 -n your-namespace --logs --timeout 600s

# Check external route (OpenShift)
oc get routes -n your-namespace
```

## ⚙️ Configuration

### 🔧 YARN RoPE Scaling for Extended Context

This deployment includes **YARN (Yet Another RoPE extensioN)** scaling to extend the model's context length beyond its original training window:

```yaml
vllm:
  maxModelLen: "80000"   # Practical tested limit with 4x YARN scaling (77K+ tokens verified)
  ropeScaling: "{\"rope_type\":\"yarn\",\"factor\":4.0,\"original_max_position_embeddings\":32768}"
```

**Benefits of YARN Scaling:**
- ✅ **Extended Context**: Handle longer documents and conversations (32K → 77K+ tokens (tested))
- ✅ **Better Performance**: YARN provides more stable extrapolation than linear scaling
- ✅ **Preserved Quality**: Maintains model quality at extended lengths
- ✅ **Production Ready**: Tested and verified in production deployments

**Configuration Parameters:**
- `rope_type: "yarn"`: Uses YARN interpolation method (correct parameter name)
- `factor: 4.0`: Extends context by 4x (32,768 → 131,072 tokens)
- `original_max_position_embeddings: 32768`: Qwen3's original training context

**⚠️ Important - Practical vs Theoretical Limits:**
- **Theoretical Maximum**: 131,072 tokens (4x factor)
- **Tested Working Limit**: 77,538 tokens (verified in production)
- **Recommended Setting**: 80,000 tokens (provides buffer above tested limit)
- **Performance**: 51 seconds processing time for 77K tokens

**To Disable YARN Scaling:**
```yaml
vllm:
  ropeScaling: ""  # Use original context length only
```

### Key Configuration Options

| Parameter | Description | Default | Example |
|-----------|-------------|---------|---------|
| `vllm.model` | HuggingFace model ID | `"Qwen/Qwen3-32B-FP8"` | `"meta-llama/Llama-2-70b-hf"` |
| `gpu.count` | Number of GPUs | `2` | `4` |
| `vllm.maxModelLen` | Maximum sequence length | `"80000"` | `"65536"` |
| `vllm.gpuMemoryUtilization` | GPU memory usage | `"0.85"` | `"0.9"` |
| `vllm.quantization` | Quantization method | `"fp8"` | `"int8"` |
| `vllm.ropeScaling` | RoPE scaling for context extension | YARN with 4x factor | `""` (disabled) |
| `route.enabled` | Enable OpenShift Route | `true` | `false` |
| `resources.limits.memory` | Memory limit | `32Gi` | `64Gi` |

### Example Custom Values

```yaml
# custom-values.yaml
vllm:
  model: "microsoft/Phi-3.5-mini-instruct"
  maxModelLen: "80000"  # Extended context with YARN 4x scaling
  gpuMemoryUtilization: "0.9"
  quantization: "fp8"
  # YARN rope scaling extends context length beyond original training
  ropeScaling: "{\"rope_type\":\"yarn\",\"factor\":4.0,\"original_max_position_embeddings\":32768}"

gpu:
  count: 1
  deviceIds: [0]

resources:
  limits:
    cpu: '4'
    memory: 16Gi
    nvidia.com/gpu: 1
  requests:
    cpu: '2'
    memory: 8Gi
    nvidia.com/gpu: 1

route:
  enabled: true
  host: "my-vllm.apps.cluster.example.com"

tolerations:
  - key: nvidia.com/gpu
    operator: Exists
    effect: NoSchedule
  - key: custom-taint
    operator: Equal
    value: gpu-node
    effect: NoSchedule
```

## 🌐 External Access

### OpenShift Routes (Recommended)
When deployed on OpenShift, the chart automatically creates a Route for external access:

```bash
# Get the auto-generated route URL
export ROUTE_URL=http://$(oc get route vllm-qwen3 -n your-namespace -o jsonpath='{.spec.host}')

# Test the API
curl $ROUTE_URL/health
```

### Port Forwarding (Development)
For local development or testing:

```bash
# Forward port to local machine
kubectl port-forward svc/vllm-qwen3 8080:80 -n your-namespace

# Access via localhost
curl http://localhost:8080/health
```

### LoadBalancer (Cloud Providers)
Set `service.type: LoadBalancer` in values.yaml for cloud load balancer:

```yaml
service:
  type: LoadBalancer
  port: 80
```

## 🧪 API Usage

> **Note**: The examples below use `curl` for broad compatibility. If you prefer `wget`, you can use equivalent commands:
> ```bash
> # curl equivalent:
> curl -X POST /v1/completions -H "Content-Type: application/json" -d '{"data":"value"}'
> 
> # wget equivalent:
> wget -q -O - --post-data='{"data":"value"}' --header="Content-Type: application/json" /v1/completions
> ```

### Health Check
```bash
curl http://your-vllm-url/health
```

### List Available Models
```bash
curl http://your-vllm-url/v1/models
```

### Text Completion
```bash
curl -X POST http://your-vllm-url/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-32B-FP8",
    "prompt": "The capital of France is",
    "max_tokens": 50,
    "temperature": 0.7
  }'
```

### Extended Context Example (YARN Scaling)
```bash
# With YARN 4x scaling, you can now handle much longer prompts (up to 131K tokens)
curl -X POST http://your-vllm-url/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-32B-FP8",
    "prompt": "Please analyze this long document: [your 100K+ token document here]...",
    "max_tokens": 1000,
    "temperature": 0.7
  }'
```

### Chat Completion (if supported)
```bash
curl -X POST http://your-vllm-url/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-32B-FP8",
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ],
    "max_tokens": 100
  }'
```

## 🧪 Testing

### Automated Testing
The chart includes comprehensive API tests that validate:
- Health endpoint functionality
- Model availability and loading
- Text completion generation
- Token usage tracking
- Response time performance

```bash
# Run all tests with adequate timeout (recommended: 10 minutes)
helm test vllm-qwen3 -n your-namespace --timeout 600s

# Run tests with live logs and extended timeout
helm test vllm-qwen3 -n your-namespace --logs --timeout 600s

# For slower clusters or during high load, use longer timeout
helm test vllm-qwen3 -n your-namespace --timeout 900s

# Clean up test pods
kubectl delete pods -l "helm.sh/hook=test" -n your-namespace
```

> **⏱️ Timeout Recommendations**:
> - **Standard clusters**: `--timeout 600s` (10 minutes)
> - **Slower clusters or high load**: `--timeout 900s` (15 minutes)  
> - **Development/local testing**: `--timeout 300s` (5 minutes) may be sufficient
>
> The tests include actual model inference which can take 30-60 seconds per completion, especially during initial model warm-up or under load.

### Manual Testing
```bash
# Test health endpoint
curl -s http://your-vllm-url/health

# Test text generation
curl -s -X POST http://your-vllm-url/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "Qwen/Qwen3-32B-FP8", "prompt": "Hello world", "max_tokens": 10}'
```

## 📊 Monitoring

### Pod Status
```bash
# Check pod status
kubectl get pods -n your-namespace -l app.kubernetes.io/name=vllm-qwen3

# View detailed pod information
kubectl describe pod -n your-namespace -l app.kubernetes.io/name=vllm-qwen3
```

### Logs
```bash
# View recent logs
kubectl logs -n your-namespace -l app.kubernetes.io/name=vllm-qwen3 --tail=100

# Follow logs in real-time
kubectl logs -f -n your-namespace -l app.kubernetes.io/name=vllm-qwen3
```

### Resource Usage
```bash
# Check resource usage
kubectl top pods -n your-namespace -l app.kubernetes.io/name=vllm-qwen3

# Check GPU usage (if nvidia-smi available)
kubectl exec -it -n your-namespace deployment/vllm-qwen3 -- nvidia-smi
```

## 🔧 Troubleshooting

### Common Issues

#### Pod Stuck in Pending
```bash
# Check pod events
kubectl describe pod -n your-namespace -l app.kubernetes.io/name=vllm-qwen3

# Common causes:
# - Insufficient GPU resources
# - Missing tolerations for GPU nodes
# - Resource limits too high
```

#### Model Loading Timeout
```bash
# Check if readiness probe timeout is sufficient
# Default: 600s (10 minutes) for readiness probe
# Default: 900s (15 minutes) for liveness probe

# Increase probe timeouts in values.yaml:
healthProbes:
  readinessProbe:
    initialDelaySeconds: 1200  # 20 minutes
  livenessProbe:
    initialDelaySeconds: 1500  # 25 minutes
```

> **💡 Best Solution**: Use [Model Preloading](#-optional-model-preloading-recommended) to reduce startup time from 15-30 minutes to 1-3 minutes, eliminating timeout issues entirely.

#### Out of Memory Errors
```bash
# Check memory usage
kubectl describe pod -n your-namespace -l app.kubernetes.io/name=vllm-qwen3

# Solutions:
# 1. Increase memory limits
# 2. Reduce gpu.count
# 3. Lower gpuMemoryUtilization
# 4. Use smaller model
```

#### Route Not Accessible
```bash
# Check route status
oc get routes -n your-namespace

# Check service endpoints
kubectl get endpoints -n your-namespace vllm-qwen3

# Verify pod is ready
kubectl get pods -n your-namespace -l app.kubernetes.io/name=vllm-qwen3
```

#### Helm Test Timeouts
```bash
# If tests timeout, increase the timeout value
helm test vllm-qwen3 -n your-namespace --timeout 900s

# Check test pod logs for details
kubectl logs -n your-namespace -l "helm.sh/hook=test"

# Common causes:
# - Model inference taking longer than expected
# - High cluster load
# - Network latency
# - Model warming up (first request after deployment)

# Solution: Use longer timeout or run tests after service is fully warmed up
```

### Debug Commands

```bash
# Get all resources
kubectl get all -n your-namespace -l app.kubernetes.io/instance=vllm-qwen3

# Check events
kubectl get events -n your-namespace --sort-by='.lastTimestamp' | tail -20

# Port forward for direct access
kubectl port-forward -n your-namespace svc/vllm-qwen3 8080:80

# Check Helm release status
helm status vllm-qwen3 -n your-namespace

# View Helm release history
helm history vllm-qwen3 -n your-namespace
```

## 🔄 Upgrading

### Upgrade Chart
```bash
# Upgrade with new values
helm upgrade vllm-qwen3 ./helm/shared-resources/vllm-qwen3/ \
  --namespace your-namespace \
  --values new-values.yaml

# Upgrade with specific parameters
helm upgrade vllm-qwen3 ./helm/shared-resources/vllm-qwen3/ \
  --namespace your-namespace \
  --set vllm.model="new-model-name"
```

### Rollback
```bash
# View release history
helm history vllm-qwen3 -n your-namespace

# Rollback to previous version
helm rollback vllm-qwen3 -n your-namespace

# Rollback to specific revision
helm rollback vllm-qwen3 2 -n your-namespace
```

## 📈 Scaling

### Horizontal Scaling
```bash
# Scale replicas (if sufficient GPU resources)
kubectl scale deployment vllm-qwen3 --replicas=2 -n your-namespace

# Or use values.yaml:
replicaCount: 2
```

### Vertical Scaling
Update resources in values.yaml:
```yaml
resources:
  limits:
    cpu: '16'
    memory: 64Gi
    nvidia.com/gpu: 4
  requests:
    cpu: '8'
    memory: 32Gi
    nvidia.com/gpu: 4

gpu:
  count: 4

vllm:
  tensorParallelSize: 4
```

## 🔐 Security

### HuggingFace Token
Create secret for private models:
```bash
kubectl create secret generic huggingface-token-secret \
  --from-literal=token=your-hf-token \
  --namespace your-namespace
```

### Security Contexts
The chart includes security best practices:
- Non-root user execution
- Read-only root filesystem
- Dropped capabilities
- Security context constraints

## 📚 Additional Resources

- [vLLM Documentation](https://docs.vllm.ai/)
- [Qwen Model Cards](https://huggingface.co/Qwen)
- [Kubernetes GPU Operator](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/overview.html)
- [OpenShift Routes](https://docs.openshift.com/container-platform/4.10/networking/routes/route-configuration.html)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with `helm template` and `helm test`
5. Submit a pull request

## 📝 License

This Helm chart is licensed under the Apache License 2.0. See LICENSE file for details.

## 📞 Support

For issues and questions:
- Create an issue in the repository
- Check troubleshooting section above
- Review vLLM documentation
- Check Kubernetes/OpenShift logs

---

**Note**: Model loading times vary based on hardware and network conditions. The Qwen3-32B-FP8 model typically takes 15-30 minutes to load on first deployment, or 1-3 minutes when using [Model Preloading](#-optional-model-preloading-recommended). 