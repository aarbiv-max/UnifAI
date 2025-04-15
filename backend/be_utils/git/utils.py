import re
import os
from backend.be_utils.git.github import GithubAPI
from backend.be_utils.git.gitlab import GitlabAPI
from urllib.parse import urlparse

GIT_HUB = "github"
GIT_LAB = "gitlab"

def detect_git_provider(repo_url):
    """
    Detects whether the repository URL is from GitLab or GitHub.

    :param repo_url: The repository URL entered by the user.
    :return: "gitlab" or "github", or raises an error if unknown.
    """
    if re.search(r'gitlab\.', repo_url, re.IGNORECASE):
        return GIT_LAB
    elif re.search(r'github\.', repo_url, re.IGNORECASE):
        return GIT_HUB
    else:
        raise ValueError("Unsupported Git provider. Only GitLab and GitHub are supported.")

def get_git_api(repo_url, repo_auth_key):
    """
    Create and return the appropriate Git API instance based on the repo URL.
    """
    provider = detect_git_provider(repo_url)  
    if provider == GIT_LAB:
        return GitlabAPI(repo_url, repo_auth_key)
    elif provider == GIT_HUB:
        repo_owner, repo_name = extract_github_repo_details(repo_url)
        return GithubAPI(repo_owner, repo_name, repo_auth_key)
    else:
        raise ValueError("Unsupported Git provider detected.")

def extract_github_repo_details(repo_url):
    # Parse GitHub URL to extract owner and repo name
    parts = repo_url.rstrip("/").split("/")
    if len(parts) < 2:
        raise ValueError("Invalid GitHub repository URL")
    return parts[-2], parts[-1]

def generate_git_file_url(local_file_path: str, repo_local_path: str, repo_url: str, branch: str = "main") -> str:
    """
    Generate a public URL to a Git file on GitHub or GitLab from the local file path.
    
    :param local_file_path: Absolute path to the file locally
    :param repo_local_path: Root directory where the repo is cloned
    :param repo_url: Original remote Git repo URL (e.g., https://github.com/org/repo.git)
    :param branch: Branch name (default: 'main')
    :return: Public URL to view the file on Git provider
    """
    # Normalize paths
    local_file_path = os.path.normpath(local_file_path)
    repo_local_path = os.path.normpath(repo_local_path)

    # Get relative path from root of repo
    relative_path = os.path.relpath(local_file_path, repo_local_path)

    # Clean up repo URL
    if repo_url.endswith(".git"):
        repo_url = repo_url[:-4]

    netloc = urlparse(repo_url).netloc.lower()
    # Detect platform and construct URL accordingly
    if GIT_HUB in netloc:
        return f"{repo_url}/blob/{branch}/{relative_path}"
    elif GIT_LAB in netloc:
        return f"{repo_url}/-/blob/{branch}/{relative_path}"
    else:
        # Fallback generic format
        return f"{repo_url}/blob/{branch}/{relative_path}"

