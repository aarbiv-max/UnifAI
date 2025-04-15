from abc import ABC, abstractmethod
import io
import os
import re
import subprocess
import threading
from urllib.parse import quote_plus
import concurrent.futures
import requests

BASE_CLONE_DIR = "/tmp/repos"
GIT_EXTENSION = ".git"

class AbstractAPI(ABC):
    def __init__(self, base_url, repo_url, auth):
        self.base_url = base_url
        self.repo_url = repo_url
        self.auth = auth
        # self._validate_git_url(self.repo_url)
        self.org_name, self.project_name = self._extract_repo_details(repo_url)

    def _extract_repo_details(self, repo_url):
        """Extract organization (if exists) and project name from the Git URL."""
        match = re.search(r"https://[\w.-]+/(.+)/([^/]+)\.git$|https://[\w.-]+/([^/]+)\.git$", repo_url)

        if match:
            org_path, project_name, single_project = match.groups()
            org_name = org_path if org_path else None  # If there's an org, use it; otherwise, return None
            project_name = project_name if project_name else single_project  # Get the correct project name
            return org_name, project_name

        raise ValueError(f"❌ Unable to extract repository details from URL: {repo_url}")

    def _get(self, url, headers=None):
        """Generic GET request for all providers with error handling."""
        try:   
            response = requests.get(url, headers=headers,  verify=False)
            response.raise_for_status()
            return self._parse_response(response)

        except requests.exceptions.HTTPError as http_err:
            status_code = http_err.response.status_code
            error_messages = {
                401: "❌ Unauthorized: Invalid or missing Credential Key.",
                403: "❌ Forbidden: You do not have permission to access this resource.",
                404: "❌ Not Found: The requested resource does not exist. This could be due to an incorrect Git URL or a non-existent branch.",
                400: "❌ Bad Request: Invalid request format or missing parameters."
            }
            raise ValueError(error_messages.get(status_code, f"HTTP Error {status_code}: {http_err.response.text}"))

        except requests.exceptions.RequestException as req_err:
            raise ValueError(f"Request failed: {str(req_err)}")

    def _validate_git_url(self, repo_url):
            """Validates whether the given URL is a valid Git repository URL and is accessible."""
            git_url_pattern = re.compile(r"^https://[\w.-]+/([\w.-]+/)*[\w.-]+\.git$")

            if not git_url_pattern.match(repo_url):
                raise ValueError( 
                    f"❌ Invalid Git URL format: {repo_url}\n"
                    "✅ Expected format: 'https://<git-provider>/<owner>/<repository>.git'\n"
                    "🔹 Example: 'https://github.com/user/repo.git'")
            try:
                response = requests.head(repo_url, headers=self._get_headers(), allow_redirects=True, timeout=5, verify=False)
                if response.status_code not in [200, 301, 302]:
                    raise ValueError(f"Repository URL is not accessible: {repo_url}")
            except requests.RequestException:
                raise ValueError(f"Failed to reach the repository URL: {repo_url}")

    def _clone_repo(self):
        repo_name = self.repo_url.split("/")[-1].replace(".git", "")
        local_path = os.path.join(BASE_CLONE_DIR, repo_name)

        if os.path.exists(local_path):
            print(f"✅ Repository already cloned: {local_path}")
            return local_path

        print(f"🔄 Cloning repository {self.repo_url} into {local_path}...")
        os.makedirs(BASE_CLONE_DIR, exist_ok=True)
   
        git_token = self.get_git_token()
        
        authenticated_repo_url = self.repo_url.replace("https://", f"https://oauth2:{git_token}@")
        git_env = os.environ.copy()
        git_env["GIT_SSL_NO_VERIFY"] = "true"
     
        result = subprocess.run(
            ["git", "clone", "--depth=1", authenticated_repo_url, local_path],
            capture_output=True, text=True, env=git_env
        )
        if result.returncode == 0:
            print(f"✅ Repository cloned successfully: {local_path}")
            return local_path
        else:
            raise ValueError(f"❌ Failed to clone repo: {result.stderr}")

        
    def list_files(self, dir_name, branch):
        """Retrieve all files from GitLab using parallel requests."""
        files = []
        lock = threading.Lock()
        max_threads = 10 

        # Fetch total pages initially to schedule tasks efficiently
        url = self._build_list_files_url(dir_name, branch, 1)
        response, headers = self._get(url, headers=self._get_headers())

        if not isinstance(response, list) or not response:
            raise ValueError(f"❌ No files found in the specified directory: {dir_name}")

        with lock:
            files.extend(response)

        total_pages = int(headers.get("X-Total-Pages", 1))

        def fetch_page(page_num):
            url = self._build_list_files_url(dir_name, branch, page_num)
            response, _ = self._get(url, headers=self._get_headers())
            if isinstance(response, list):
                with lock:
                    files.extend(response)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            # Start from page 2 as page 1 was already fetched
            executor.map(fetch_page, range(2, total_pages + 1))

        filtered_files = [item for item in files if self._is_valid_file(item)]

        if filtered_files:
            return filtered_files
        else:
            raise ValueError(f"❌ No valid files found in the specified directory: {dir_name}")
        
    def get_file_content(self, file_path, branch):
        """Fetch content of a specific file from GitLab.

        :param str file_path: Path of the file to retrieve
        :param str branch: Branch name to fetch the file from
        :return: File content as a string
        """
        if file_path.startswith('/'):
            file_path = file_path[1:]

        file_path_encoded = quote_plus(file_path)
        url = self._build_file_content_url(file_path_encoded, branch)

        response = requests.get(url, headers=self._get_headers(), verify=False)
        if response.status_code == 200:
            return self._decode_file_content(response) 
        else:
            raise ValueError(f"Failed to fetch file content: {response.status_code} - {response.text}")    
        
    def _build_url(self, endpoint, params=None):
        base_url_clean = self.base_url.rstrip('/')
        if base_url_clean.endswith(GIT_EXTENSION): 
            base_url_clean = base_url_clean[:-4]  
        url = f"{base_url_clean}/{endpoint}"
        if params:
            query_string = "&".join(f"{key}={quote_plus(str(value))}" for key, value in params.items())
            url = f"{url}?{query_string}"
        return url
    
    def _is_valid_file(self, file):
        return isinstance(file, dict) and file.get("type") == "blob"
    
    @abstractmethod
    def _get_headers(self):
        pass

    @abstractmethod
    def _build_list_files_url(self, dir_name, branch, page=None):
        pass

    @abstractmethod
    def _build_file_content_url(self, file_path_encoded, branch):
        pass

    @abstractmethod
    def _decode_file_content(self, data):
        pass
    
    @abstractmethod
    def get_git_token(self):
        pass

    @abstractmethod
    def _parse_response(self, response):
        """Subclasses must implement this to parse API responses correctly."""
        pass