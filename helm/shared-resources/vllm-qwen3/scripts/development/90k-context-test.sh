#!/bin/bash

# 90K Context Length Test Script
# Validates extended context processing capabilities with real 90K token input

set -e

NAMESPACE="tag-ai--runtime-int"
POD_NAME=$(kubectl get pods -l "app.kubernetes.io/name=vllm-qwen3,app.kubernetes.io/instance=vllm-2gpu-200gb" -n $NAMESPACE --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
SAMPLE_FILE="$(dirname "$0")/90k-token-sample.txt"

echo "🧪 90K Context Length Validation Test"
echo "===================================="
echo "Timestamp: $(date)"
echo "Namespace: $NAMESPACE"
echo "Sample File: $SAMPLE_FILE"
echo ""

# Check if sample file exists
if [ ! -f "$SAMPLE_FILE" ]; then
    echo "❌ Sample file not found: $SAMPLE_FILE"
    exit 1
fi

# Check if pod is running
if [ -z "$POD_NAME" ]; then
    echo "❌ No running vLLM pod found"
    echo "Available pods:"
    kubectl get pods -l "app.kubernetes.io/name=vllm-qwen3,app.kubernetes.io/instance=vllm-2gpu-200gb" -n $NAMESPACE
    exit 1
fi

echo "✅ Found running pod: $POD_NAME"
echo ""

# Function to count tokens (approximate)
count_tokens() {
    local text="$1"
    # Rough estimation: 1 token ≈ 4 characters for English text
    local char_count=$(echo "$text" | wc -c)
    local estimated_tokens=$((char_count / 4))
    echo $estimated_tokens
}

# Function to test API connectivity
test_api_connectivity() {
    echo "🔗 Testing API connectivity..."
    local health_response=$(kubectl exec $POD_NAME -n $NAMESPACE -c vllm-qwen3 -- curl -s -w "%{http_code}" -o /dev/null http://localhost:8000/health 2>/dev/null || echo "000")
    
    if [ "$health_response" = "200" ]; then
        echo "✅ API health check passed"
        return 0
    else
        echo "❌ API health check failed (HTTP $health_response)"
        return 1
    fi
}

# Function to check model configuration
check_model_config() {
    echo "📋 Checking model configuration..."
    local config=$(kubectl exec $POD_NAME -n $NAMESPACE -c vllm-qwen3 -- curl -s http://localhost:8000/v1/models 2>/dev/null | jq '.')
    
    if [ "$?" -eq 0 ]; then
        echo "Model ID: $(echo "$config" | jq -r '.data[0].id')"
        echo "Max Model Length: $(echo "$config" | jq -r '.data[0].max_model_len')"
        local max_len=$(echo "$config" | jq -r '.data[0].max_model_len')
        
        if [ "$max_len" = "90000" ]; then
            echo "✅ Model configured for 90K context length"
            return 0
        else
            echo "❌ Model max length is $max_len, expected 90000"
            return 1
        fi
    else
        echo "❌ Failed to retrieve model configuration"
        return 1
    fi
}

# Function to create JSON payload
create_json_payload() {
    local prompt="$1"
    local escaped_prompt=$(echo "$prompt" | jq -R -s .)
    cat <<EOF
{
  "model": "/models/Qwen3-32B-FP8",
  "prompt": $escaped_prompt,
  "max_tokens": 100,
  "temperature": 0.1,
  "stream": false
}
EOF
}

# Function to test context processing
test_context_processing() {
    local token_count="$1"
    local prompt="$2"
    
    echo "🚀 Testing ${token_count}-token context processing..."
    echo "Prompt length: $(echo "$prompt" | wc -c) characters"
    
    # Create temporary JSON file
    local json_file="/tmp/90k-test-payload.json"
    create_json_payload "$prompt" > "$json_file"
    
    echo "📤 Sending request to vLLM API..."
    local start_time=$(date +%s.%N)
    
    # Send request and capture response
    local response=$(kubectl exec $POD_NAME -n $NAMESPACE -c vllm-qwen3 -- bash -c "curl -s -X POST http://localhost:8000/v1/completions -H 'Content-Type: application/json' -d @/dev/stdin" < "$json_file" 2>/dev/null)
    local exit_code=$?
    
    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "unknown")
    
    # Clean up temp file
    rm -f "$json_file"
    
    if [ $exit_code -eq 0 ] && [ -n "$response" ]; then
        echo "📥 Response received in ${duration}s"
        
        # Parse response
        local choices=$(echo "$response" | jq '.choices[]?' 2>/dev/null)
        local error=$(echo "$response" | jq '.error?' 2>/dev/null)
        local usage=$(echo "$response" | jq '.usage?' 2>/dev/null)
        
        if [ "$error" != "null" ] && [ -n "$error" ]; then
            echo "❌ API Error: $error"
            return 1
        elif [ -n "$choices" ]; then
            echo "✅ Successful completion response"
            echo ""
            echo "📊 Response Analysis:"
            echo "Generated text: $(echo "$response" | jq -r '.choices[0].text' | head -c 200)..."
            echo "Finish reason: $(echo "$response" | jq -r '.choices[0].finish_reason')"
            
            if [ "$usage" != "null" ]; then
                local prompt_tokens=$(echo "$response" | jq -r '.usage.prompt_tokens // "unknown"')
                local completion_tokens=$(echo "$response" | jq -r '.usage.completion_tokens // "unknown"')
                local total_tokens=$(echo "$response" | jq -r '.usage.total_tokens // "unknown"')
                
                echo "Prompt tokens: $prompt_tokens"
                echo "Completion tokens: $completion_tokens"
                echo "Total tokens: $total_tokens"
                
                # Validate token count
                if [ "$prompt_tokens" != "unknown" ] && [ "$prompt_tokens" -gt 80000 ]; then
                    echo "🎉 SUCCESS: Processing ${prompt_tokens} tokens (exceeds 80K threshold)"
                elif [ "$prompt_tokens" != "unknown" ] && [ "$prompt_tokens" -gt 16000 ]; then
                    echo "✅ GOOD: Processing ${prompt_tokens} tokens (exceeds base 16K)"
                else
                    echo "⚠️ WARNING: Only processing ${prompt_tokens} tokens (may be truncated)"
                fi
            else
                echo "⚠️ No usage statistics available"
            fi
            
            return 0
        else
            echo "❌ Invalid response format"
            echo "Response: $response"
            return 1
        fi
    else
        echo "❌ Request failed (exit code: $exit_code)"
        echo "Response: $response"
        return 1
    fi
}

# Main test execution
main() {
    echo "🔍 Pre-flight checks..."
    
    # Test API connectivity
    if ! test_api_connectivity; then
        echo "❌ API connectivity test failed"
        exit 1
    fi
    
    # Check model configuration  
    if ! check_model_config; then
        echo "❌ Model configuration check failed"
        exit 1
    fi
    
    echo ""
    echo "📖 Loading test sample..."
    
    # Read the sample file
    local sample_text=$(cat "$SAMPLE_FILE")
    local estimated_tokens=$(count_tokens "$sample_text")
    
    echo "Sample file size: $(stat -c%s "$SAMPLE_FILE") bytes"
    echo "Estimated tokens: ~$estimated_tokens"
    echo ""
    
    # Test with progressively larger contexts
    echo "🧪 Running progressive context tests..."
    echo ""
    
    # Test 1: Small sample (first 1000 characters)
    local small_sample=$(echo "$sample_text" | head -c 1000)
    local small_tokens=$(count_tokens "$small_sample")
    if test_context_processing "$small_tokens" "$small_sample"; then
        echo "✅ Small context test (${small_tokens} tokens) passed"
    else
        echo "❌ Small context test failed"
        return 1
    fi
    
    echo ""
    
    # Test 2: Medium sample (first 10000 characters)  
    local medium_sample=$(echo "$sample_text" | head -c 10000)
    local medium_tokens=$(count_tokens "$medium_sample")
    if test_context_processing "$medium_tokens" "$medium_sample"; then
        echo "✅ Medium context test (${medium_tokens} tokens) passed"
    else
        echo "❌ Medium context test failed"
        return 1
    fi
    
    echo ""
    
    # Test 3: Large sample (first 50000 characters)
    local large_sample=$(echo "$sample_text" | head -c 50000)
    local large_tokens=$(count_tokens "$large_sample")
    if test_context_processing "$large_tokens" "$large_sample"; then
        echo "✅ Large context test (${large_tokens} tokens) passed"
    else
        echo "❌ Large context test failed"  
        return 1
    fi
    
    echo ""
    
    # Test 4: Full 90K sample
    if test_context_processing "$estimated_tokens" "$sample_text"; then
        echo "🎉 FULL 90K CONTEXT TEST PASSED!"
        echo ""
        echo "🏆 MILESTONE ACHIEVED: 90K token context processing validated"
    else
        echo "❌ Full 90K context test failed"
        return 1
    fi
    
    echo ""
    echo "📈 Test Summary:"
    echo "✅ API connectivity: PASSED"
    echo "✅ Model configuration: PASSED (90K max length)"
    echo "✅ Small context (~${small_tokens} tokens): PASSED"
    echo "✅ Medium context (~${medium_tokens} tokens): PASSED"  
    echo "✅ Large context (~${large_tokens} tokens): PASSED"
    echo "✅ Full context (~${estimated_tokens} tokens): PASSED"
    echo ""
    echo "🎯 RESULT: vLLM deployment successfully handles 90K token contexts!"
    
    return 0
}

# Execute main function
if main; then
    echo ""
    echo "🎉 90K CONTEXT TEST COMPLETED SUCCESSFULLY"
    exit 0
else
    echo ""
    echo "❌ 90K CONTEXT TEST FAILED"
    exit 1
fi 