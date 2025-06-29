import json
import os
from typing import Iterator, Dict, Any
from prompt_lab.storage import HFExporter
from huggingface_hub import HfApi
import configparser

config = configparser.ConfigParser()
config.read("config/backend.cfg")

class HuggingFaceUtils():
    def  __init__(self):
    #   config_path = "../config/backend.cfg"
    #   config = configparser.ConfigParser()
    #   config.read(config_path)
      token = config.get("hf", "HF_TOKEN", fallback=None)
      self.hf_token = os.path.expandvars(token) if token else None
      self.api = HfApi(token=self.hf_token)

    def list_repo_files(self, repo_id: str):
      try:
        files_list = self.api.list_repo_files(repo_id=repo_id)
        return files_list
      except Exception as e:
        print(f"File listing failed: {e}")
      

    def download_file(self, repo_id: str , file_name: str, download_path: str=None):
        if not download_path:
           download_path = "/tmp"
        self.api.hf_hub_download(repo_id=repo_id, filename=file_name, local_dir=download_path,force_download=True)  


def json_record_provider(json_path: str) -> Iterator[Dict[str, Any]]:
    """
    Generator function to yield records from a JSON file.
    
    Args:
        json_path (str): Path to the JSON file.
    
    Yields:
        Dict[str, Any]: Each record from the JSON file.
    """
    with open(json_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
        if isinstance(data, list):  # Ensure JSON structure is a list of dictionaries
            for record in data:
                yield record
        else:
            raise ValueError("JSON file must contain a list of dictionaries.")


def upload_json_to_hf(json_path: str, project_name: str):
    """
    Reads a JSON file and uploads it to Hugging Face Hub using HFExporter.
    
    Args:
        json_path (str): Path to the JSON file.
    
    Returns:
        str: URL of the uploaded dataset.
    """
    hf_space = config.get("hf", "HF_SPACE", fallback=None)
    #data_set = config.get("hf", "HF_DATA_SET", fallback=None)
    token = config.get("hf", "HF_TOKEN", fallback=None)
    hf_token = os.path.expandvars(token) if token else None
    batch_size = config.getint("hf", "HF_BATCH_SIZE", fallback=1000)
    export_format = config.get("hf", "HF_EXPORT_FORMAT", fallback="json").lower()

    repo_id = f"{hf_space}/{project_name}"
    if not repo_id or not hf_token:
        raise ValueError("Missing required Hugging Face credentials. Set HF_REPO_ID and HF_TOKEN.")

    api = HfApi(token=hf_token)
    try:
        api.create_repo(repo_id=repo_id, repo_type="dataset", private=True, exist_ok=True)
        record_generator = json_record_provider(json_path)
        exporter = HFExporter(repo_id=repo_id, file_name=project_name, token=hf_token, batch_size=batch_size, export_format=export_format)
        upload_url = exporter.export(record_generator)
        
        return upload_url

    except Exception as e:
        raise ValueError(f"{e}")