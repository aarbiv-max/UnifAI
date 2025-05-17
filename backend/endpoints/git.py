from flask import Blueprint
from backend.be_utils.utils import json_response
from backend.providers.git import get_test_content_from_git, list_of_files_from_git
from helpers.apiargs import from_query
from webargs import fields

git_bp = Blueprint("git", __name__)

@git_bp.route("/files", methods=["GET"])
@from_query({"repo_url": fields.Str(load_default='', data_key="gitUrl"),
             "repo_auth_key": fields.Str(load_default='', data_key="gitCredentialKey"),
             "repo_folder_path": fields.Str(load_default='', data_key="gitFolderPath"),
             "branch": fields.Str(load_default='dev', data_key="gitBranchName")})
def get_test_list_from_git(repo_url, repo_auth_key, repo_folder_path, branch):
    """
    :param str repo_url: representing the git repo url
    :param str repo_auth_key: authentication key for the dedicated git repo
    :param str repo_folder_path: valid folder to expand exist on the dedicated git repo
    :param str branch: valid branch to expand from under the dedicated git repo
    :return: list of files from git, list of { 'file': filename, in_db: boolean }"""
    try:
        list_of_files = list_of_files_from_git(repo_url, repo_auth_key, repo_folder_path, branch)
        return json_response({"result": list_of_files})
    
    except ValueError as e:
        return json_response({"error": str(e)}), 400  

    except Exception as e:
        return json_response({"error": f"An unexpected error occurred: {str(e)}"}), 500 


@git_bp.route("/gitLabFileContent", methods=["GET"])
@from_query({"repo_url":         fields.Str(required=True, data_key="gitUrl"),
             "repo_auth_key":    fields.Str(required=True, data_key="gitCredentialKey"),
             "repo_folder_path": fields.Str(required=True, data_key="gitFolderPath"),
             "branch":           fields.Str(load_default='dev', data_key="gitBranchName"),
             "test_path":        fields.Str(required=True, data_key="testPath")})
def get_test_details(repo_url, repo_auth_key, repo_folder_path, branch, test_path):
    """Fetch details for a specific test file from GitLab.

    :param str repo_url: Git repository URL
    :param str repo_auth_key: Authentication key for GitLab
    :param str repo_folder_path: Folder path in the Git repository
    :param str branch: Branch name
    :param str test_path: Path of the test file
    :return: Content of the test file
    """
    test_content = get_test_content_from_git(repo_url, repo_auth_key, branch, test_path)
    return json_response({"result": {"path": test_path, "content": test_content}})