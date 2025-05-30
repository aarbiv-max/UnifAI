# max_seq_length = 8192  # Choose any! Llama 3 is up to 8k
# dtype = None
# load_in_4bit = True  # Use 4bit quantization to reduce memory usage. Can be False.
#
# from unsloth import FastLanguageModel
#
# model, tokenizer = FastLanguageModel.from_pretrained(
#     model_name="/home/instruct/openshift-qe-infra/openshift-qe-infra-training-loraRank16-loraAlpha16/checkpoint-12730"
# )
# # FastLanguageModel.for_inference(model)  # Enable native 2x faster inferenc
#
# model.push_to_hub("oodeh/openshift-qe-r16-a16", token = "hf_xxxx") # Online saving
# tokenizer.push_to_hub("oodeh/openshift-qe-r16-a16", token = "hf_xxxx") # Online saving

from huggingface_hub import HfApi, HfFolder, Repository
import os

# Define variables
model_dir = "mta-tests-model/"  # Path to your local model directory
repo_name = "mta-TAG-r16-a16-epoch20"              # Name of the model repository
username = "oodeh"                 # Your Hugging Face username or organization
repo_id = f"{username}/{repo_name}"        # Full repo name, e.g., "username/your-model-name"

# Initialize Hugging Face API
api = HfApi()

# Create the repository if it doesn’t already exist
api.create_repo(repo_id, exist_ok=True)

# Upload the entire directory to the repository
from huggingface_hub import upload_folder
upload_folder(
    folder_path=model_dir,
    repo_id=repo_id,
    commit_message="Initial upload of the model"
)

print(f"Model uploaded successfully to https://huggingface.co/{repo_id}")
