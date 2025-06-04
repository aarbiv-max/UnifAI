
from backend.be_utils.git.utils import get_git_api
from backend.providers.extensions import get_extensions_json


def get_directory_list(file_list_git, file_list_db):
    """Build a list of files from Git and add an attribute if each file is already in the database.

    :param str[] file_list_git: List of files from the Git provider.
    :param str[] file_list_db: List of files from the database.
    :return: List of files with a state indicating if they exist in the database.
    """
    frameworks = get_extensions_json()["frameworks"]
    database_set = {file_node["path"] + "/" + file_node["name"] for file_node in file_list_db}
    list_of_files = [
        {'file': git_file["path"], 'in_db': git_file["path"] in database_set}
        for git_file in file_list_git
        if (git_file.get("name") or git_file.get("path", "")).endswith(("resource","jmx", "robot", "ts", "go", "tsx", "js", "py")) and "__init__" not in str(git_file)
    ]
    return list_of_files


def list_of_files_from_git(repo_url, repo_auth_key, repo_folder_path, branch):
    """Retrieve a list of files from the appropriate Git provider and check if they exist in the database.

    :param str repo_url: Repository URL provided by the user.
    :param str repo_auth_key: Authentication key for the Git provider.
    :param str repo_folder_path: Folder path in the repository to scan.
    :param str branch: Branch name.
    :return: List of files from the repository with a state indicating database existence.
    """
    git_api = get_git_api(repo_url, repo_auth_key)  # Dynamically select the provider.
    file_list_git = git_api.list_files(repo_folder_path, branch)
    return get_directory_list(file_list_git, [])


def get_test_content_from_git(repo_url, repo_auth_key, branch, test_path):
    """Fetch the content of a test file from the appropriate Git provider.

    :param str repo_url: Repository URL provided by the user.
    :param str repo_auth_key: Authentication key for the Git provider.
    :param str branch: Branch name.
    :param str test_path: Path to the test file in the repository.
    :return: The content of the test file as a string.
    """
    git_api = get_git_api(repo_url, repo_auth_key)  # Dynamically select the provider.
    return git_api.get_file_content(test_path, branch)
