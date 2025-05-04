# Step-by-Step Guide to Export and Upload a Model to Hugging Face

This guide will walk you through exporting a model with LoRA adapters, uploading it to Hugging Face, and registering it via an API.

---

## Prerequisites

Before starting, ensure the following:

1. **SSH Access**: You can access the server where the model and adapters are stored.
   - Example SSH command:  
     ```bash
     ssh instruct@<server_address>
     ```
   - Replace `<server_address>` with the actual address. Enter the password when prompted.

2. **Hugging Face Account**: You have an account and a token for authentication.
   - Get a token from [Hugging Face](https://huggingface.co/settings/tokens).

3. **Required Tools**:
   - `llamafactory-cli`
   - `huggingface_hub` Python package (install via `pip install huggingface_hub`).

---

## Steps to Export the Model

1. **Navigate to the Model Directory**
   
   SSH into your server and navigate to the `LLaMA-Factory` directory where the model and adapters are stored:
   
   ```bash
   cd LLaMA-Factory/
   ```

2. **Export the Model**
   
   Use the `llamafactory-cli` tool to export the model with its adapters. Replace the placeholders with your actual paths and parameters:
   
   ```bash
   llamafactory-cli export \
       --model_name_or_path <base_model_name> \
       --adapter_name_or_path <adapter_path> \
       --template llama3 \
       --finetuning_type lora \
       --export_dir <export_directory> \
       --export_size 2 \
       --export_legacy_format False
   ```
   Example:
   ```bash
   llamafactory-cli export \
       --model_name_or_path oodeh/mta-DeepCode-r32-a32-epoch20 \
       --adapter_name_or_path saves/Qwen2.5-Coder-3B-Instruct/lora/train_2024-12-17-08-51-28/ \
       --template llama3 \
       --finetuning_type lora \
       --export_dir /home/instruct/mta-tests-model/ \
       --export_size 2 \
       --export_legacy_format False
   ```

3. **Add Metadata File**

   Navigate to the export directory and create a `card.json` file with metadata:

   ```bash
   cd <export_directory>
   ```

   Create the `card.json` file with the following content:

   ```json
   {
       "name": "<model_name>",
       "base_model": "<base_model_name>",
       "context_length": 8192,
       "model_type": "finetuned",
       "quantized": <true|false>,
       "finetune_steps": [
           {
               "base_model": "<base_model_name>",
               "step": 2,
               "data": "<dataset_name>",
               "epochs": <epochs>,
               "batch_size": <batch_size>,
               "dataset_size": <dataset_size>,
               "num_tests": ""
           }
       ],
       "project": "<project_name>",
       "prompt_template": {
           "user_tag": "<|start_header_id|>user<|end_header_id|>",
           "end_tag": "<|eot_id|>",
           "assistant_tag": "<|start_header_id|>assistant<|end_header_id|>"
       }
   }
   ```

   Replace placeholders like `<model_name>`, `<base_model_name>`, and `<dataset_name>` with actual values.

---

## Steps to Upload the Model to Hugging Face

1. **Login to Hugging Face**

   Run the following command and enter your Hugging Face token when prompted:

   ```bash
   huggingface-cli login
   ```

   Example token: `hf_YourTokenHere`

2. **Upload the Model**

   Use the following Python script to upload the model directory to Hugging Face:

   ```python
   from huggingface_hub import HfApi, upload_folder

   # Define variables
   model_dir = "<export_directory>"  # Path to your local model directory
   repo_name = "<repository_name>"   # Name of the model repository
   username = "<your_username>"      # Your Hugging Face username
   repo_id = f"{username}/{repo_name}"

   # Initialize Hugging Face API
   api = HfApi()

   # Create the repository if it doesn't already exist
   api.create_repo(repo_id, exist_ok=True)

   # Upload the entire directory to the repository
   upload_folder(
       folder_path=model_dir,
       repo_id=repo_id,
       commit_message="Initial upload of the model"
   )

   print(f"Model uploaded successfully to https://huggingface.co/{repo_id}")
   ```

3. **Verify Upload**

   After running the script, check your Hugging Face model repository at:
   
   ```
   https://huggingface.co/<your_username>/<repository_name>
   ```

---

## Steps to Register the Model via API

Use `curl` to register the model with your backend API. Replace `<hf_url>` and other placeholders with actual values:

```bash
curl --location '<api_endpoint>' \
--header 'Content-Type: application/json' \
--data '{
    "hfUrl": "<hf_url>",
    "quantized": false
}'
```

Example:

```bash
curl --location 'instructlab.jf42w.sandbox1115.opentlc.com:443/api/backend/registerTrainedModel' \
--header 'Content-Type: application/json' \
--data '{
    "hfUrl": "https://huggingface.co/oodeh/mta-DeepCode-r32-a32-epoch20",
    "quantized": false
}'
```

---

## Notes

- Replace all placeholders (e.g., `<server_address>`, `<base_model_name>`, `<repository_name>`) with actual values specific to your setup.
- Ensure all tools and dependencies are properly installed and configured.
- Validate each step to confirm successful completion before proceeding to the next.

