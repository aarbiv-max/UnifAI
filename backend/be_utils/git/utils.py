import re
from backend.be_utils.git.github import GithubAPI
from backend.be_utils.git.gitlab import GitlabAPI

GIT_HUB = "github"
GIT_LAB = "gitlab"

def detect_git_provider(repo_url):
    """
    Detects whether the repository URL is from GitLab or GitHub.

    :param repo_url: The repository URL entered by the user.
    :return: "gitlab" or "github", or raises an error if unknown.
    """
    if re.search(r'gitlab\.', repo_url, re.IGNORECASE) or re.search(r'scm\.cci\.nokia', repo_url, re.IGNORECASE):
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

