#!/bin/bash

# Activate virtual environment
#source /LLaMA-Factory/myenv/bin/activate

DATA="{\"$DATASET_NAME\": {
  \"hf_hub_url\": \"$DATASET_REPO\",
  \"columns\": {
    \"prompt\": \"question\",
    \"response\": \"answer\",
    \"system\": \"system\"
    }}}"


# Run based on mode
#if [ "$MODE" == "inference" ]; then
#    echo "Starting vLLM Inference Server..."
#    exec vllm serve  $@
if [ "$MODE" == "training" ]; then
    
    #cd /app/LLaMA-Factory
    echo "logging in to hugging face"
    huggingface-cli login --token $token
    #update the dataset_info file
    echo "Updating LlamaFactory dataset info file..."
    # Activate virtualenv for training and start the training
    echo "${DATA}" > ./data/dataset_info.json
    #run the distribution script
    export MAX_TOKENS=$(python3 /tmp/dataset-token-size-distribution.py |grep Max_tokens |awk '{print $2}')
    echo "max tokens is: $MAX_TOKENS"
    echo "Starting LlamaFactory Training..."
    #exit 0
    #. /venv/bin/activate
    #screen -L -Logfile /app/train-screen.log -dmS training llamafactory-cli train /app/LLaMA-Factory/trainer_args.yaml
elif [ "$MODE" == "debug" ]; then
    echo "Debug mode enabled. Sleeping indefinitely..."
    sleep infinity
else
    echo "Invalid mode. Use 'inference', 'debug' or 'training'."
    exit 1
fi
