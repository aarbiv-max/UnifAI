import os
import json
import abc

class BaseParser(abc.ABC):
    def __init__(self, repo_local_path, file_paths, project_name, organization_name, repo_url, git_branch_name):
        """
        Base class for all parsers.

        :param repo_local_path: Local path to the cloned repository.
        :param file_paths: List of file paths to be parsed.
        :param project_name: The name of the project.
        :param organization_name: The name of the orgnization.
        """
        self.repo_local_path = repo_local_path
        self.file_paths = file_paths
        self.project_name = project_name
        self.organization_name = organization_name
        self.parsed_files = []
        self.counter = 0
        self.repo_url = repo_url
        self.git_branch_name = git_branch_name
        self.full_project_name = f"{self.organization_name}/{self.project_name}" if self.organization_name else self.project_name


    @abc.abstractmethod
    def parse_files(self):
        """
        Abstract method to be implemented by child classes.
        """
        pass

    def write_to_file(self, filename):
        """
        Writes parsed data to a JSON file.
        """
        json_data = json.dumps(self.parsed_files, indent=2)
        with open(filename, "w") as file:
            file.write(json_data)
        print(f"📂 Parsed data saved to {filename}")
