import huggingface_hub
from huggingface_hub import HfApi, HfFolder
import os

class HF():
    def __init__(self, token: str = None):
       #Init functions runs these actions
       #1. Always start with login - not necessary
       #2. since we usually work in pods added a few settings to make life easier (espacially where progress bars are concenred)
       #3. defines the api object
       self.token = token or HfFolder.get_token() or os.environ['token']
       os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
       os.environ["COLUMNS"] = "80"  # Set a default terminal width
       os.environ["LINES"] = "24"    # Set a default terminal height
    #    print("Logging in to hugging face using predefined token")
    #    try:
    #      huggingface_hub.login(os.environ['token']) # might be unnecessary  
    #    except Exception as e:
    #      print("Login to Hugging face failed with following exception:")
    #      print(e)
       self.api = huggingface_hub.HfApi(token=self.token)
       


    def large_folder_upload(self, repo_id: str, folder_path: str, repo_type: str ="model"):
        #This function uploads the whole folder to hugging face 
        #note that it will upload to the space according to the token used
        print(f"Uploading requested {repo_type} to hugging face")
        try:
          self.api.upload_large_folder(repo_id=repo_id, folder_path=folder_path, repo_type=repo_type)
          print(f"Uploading folder is finished")
        except Exception as e:
          print("Upload to Hugging face failed with the following exception:")
          print(e)

    def folder_upload(self, repo_id: str, folder_path: str, repo_type: str ="model"):
        #This function uploads the whole folder to hugging face on file at a time
        #This allows us better control over the progress of the upload
        print(f"Uploading requested folder to hugging face")
        for root, _, files in os.walk(folder_path):
            for file in files:
                local_file_path = os.path.join(root, file)
                # This creates the path *within the repo*, relative to the base folder
                path_in_repo = os.path.relpath(local_file_path, folder_path)
                self.file_upload(repo_id=repo_id, file_path=local_file_path, path_in_repo=path_in_repo, repo_type=repo_type)

        print(f"Uploading folder is finished")


    def file_upload(self, repo_id: str, file_path: str, path_in_repo:str = None, repo_type: str ="model"):
        #This function uploads the whole folder to hugging face 
        #note that it will upload to the space according to the token used
        if not os.path.isfile(file_path):
           raise FileNotFoundError(f"The file {file_path} does not exist.")        
        print(f"Uploading requested file to hugging face")
        if not path_in_repo:
          path_in_repo = os.path.basename(file_path)
        try:
          self.api.upload_file(repo_id=repo_id, path_or_fileobj=file_path, path_in_repo=path_in_repo, repo_type=repo_type)
          print(f"Uploading folder is finished")
        except Exception as e:
          print("Upload to Hugging face failed with the following exception:")
          print(e)

    # def get_folder_files(self, folder: str = None):
    #     file_list = os.walk(folder)
    #     return file_list
        

    