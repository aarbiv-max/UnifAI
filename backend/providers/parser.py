from flask import jsonify
from backend.be_utils.files_cleaner import FileCleaner
from backend.be_utils.git.utils import get_git_api
from backend.providers.forms import get_form, update_form_status
from backend.providers.hf import upload_json_to_hf
from backend.shared.fields import FormFields
from data_pre.parsers.RobotParserWrapper import RobotParserWrapper
from data_pre.parsers.TreeSitterParserWrapper import TreeSitterParserWrapper
from shared.enums import FormStatus

def get_parser(repo_local_path, file_paths, framework, project_name, organization_name, repo_url, git_branch_name):
    """
    Factory function to return the appropriate parser based on the framework.
    """
    framework = framework.lower()
    
    if framework in ["go", "typescript", "python"]:
        return TreeSitterParserWrapper(repo_local_path, file_paths, project_name, organization_name, repo_url, git_branch_name)
    elif framework == "robot":
        return RobotParserWrapper(repo_local_path, file_paths, project_name, organization_name, repo_url, git_branch_name)
    else:
        raise ValueError(f"❌ Unsupported framework: {framework}")

async def trigger_parser(form_id):
    """
    Retrieve repo details from DB, clone it, and start parsing.
    """
    update_form_status(form_id, FormStatus.CLONING)
    
    repo_info = get_form(form_id)  # Retrieve repository details based on form ID
    if not repo_info:
        return {"error": "Invalid form_id or repo not found"}, 400  

    repo_url = repo_info.get(FormFields.GIT_URL.name, "") 
    file_paths = repo_info.get(FormFields.FILES_PATH.name, [])  
    framework = repo_info.get(FormFields.TESTS_CODE_FRAMEWORK.name, "Unknown")  
    auth_token = repo_info.get(FormFields.GIT_CREDENTIAL_KEY.name, None)  
    project_name = repo_info.get(FormFields.PROJECT_NAME.name, None) 
    git_branch_name = repo_info.get(FormFields.GIT_BRANCH_NAME.name, None)

    git_api = get_git_api(repo_url, auth_token)  
    repo_local_path = git_api._clone_repo()  # Clone the repository locally
    organization_name = git_api.org_name

    update_form_status(form_id, FormStatus.PARSING)

    parser = get_parser(repo_local_path, file_paths, framework, project_name, organization_name, repo_url, git_branch_name)
    parsing_result = parser.parse_files()  # Parse the files and retrieve JSON

    update_form_status(form_id, FormStatus.UPLOADHF)
    
    upload_json_to_hf(parsing_result, project_name)  # Upload parsing results to HF storage
    
    update_form_status(form_id, FormStatus.DONE)
    
    FileCleaner.delete_path(repo_local_path)  # Clean up the cloned repository from local path

   
