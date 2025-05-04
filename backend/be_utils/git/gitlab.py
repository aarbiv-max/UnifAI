import requests
from backend.be_utils.git.git import AbstractAPI
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) 

GITLAB_API_URL = "https://gitlab.cee.redhat.com/api/v4/projects"
GIT_EXTENSION = ".git"
PRIVATE_TOKEN = "private_token"
class GitlabAPI(AbstractAPI):
    base_url = None
    private_token = None

    def __init__(self, repo_url, private_token):
        super().__init__(repo_url, repo_url, {PRIVATE_TOKEN: private_token})
        self.private_token = private_token 
        self.base_url = self._get_project_api_url() 
        
    def _parse_response(self, response):
        """GitLab can return JSON or raw text (for unexpected cases), so handle both cases."""
        try:
            return response.json(), response.headers 
        except requests.exceptions.JSONDecodeError:
            return {"text": response.text}, response.headers 
        
    def _get_project_api_url(self):
        """Convert `repo_url` to `api/v4/projects/{ID}`."""
        project_name = self.base_url.split("/")[-1].replace(GIT_EXTENSION, "")
        search_url = f"{GITLAB_API_URL}?search={project_name}"
        headers = self._get_headers()
        projects, _ = self._get(search_url, headers=headers)
        if "error" in projects:
            raise ValueError(f"❌ GitLab project not found: {projects.get('error', 'Unknown error')}")
        
        for project in projects:
            if project["http_url_to_repo"].rstrip("/") == self.repo_url.rstrip("/"):  # Normalize URLs
                print(f"✅ Found exact project: {project['http_url_to_repo']}")
                return f"{GITLAB_API_URL}/{project['id']}"
        raise ValueError(f"❌ No exact match found for {self.repo_url}")

    def _get_headers(self):
        """GitLab requires authentication via headers."""
        return {"PRIVATE-TOKEN": self.private_token}

    def _build_list_files_url(self, dir_name, branch, page=None):
        params = {
            "ref": branch,
            "path": dir_name,
            "per_page": 10000,
            "recursive": 1
        }
        if page:
            params["page"] = page
        return self._build_url("repository/tree", params)

    def _build_file_content_url(self, file_path_encoded, branch):
        return self._build_url(f"repository/files/{file_path_encoded}/raw", {"ref": branch})

    def _decode_file_content(self, data):
        return data.text 
    
    def get_git_token(self):
        if PRIVATE_TOKEN in self.auth:
            return self.auth[PRIVATE_TOKEN]
        raise ValueError("No GitLab private token found. Cannot proceed.")