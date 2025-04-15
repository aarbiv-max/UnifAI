import json
import os
from backend.be_utils.git.utils import generate_git_file_url
from data_pre.parsers.BaseParser import BaseParser
from data_pre.parsers.components.tree_sitter_parser import TreeSitterParser


class TreeSitterParserWrapper(BaseParser):
    def __init__(self, repo_local_path, file_paths, project_name, organization_name, repo_url, git_branch_name):
        """
        Parser for Go and TypeScript using TreeSitter.
        """
        super().__init__(repo_local_path, file_paths, project_name, organization_name, repo_url, git_branch_name)

    def parse_files(self):
        """
        Parses files using TreeSitter.
        """
        project_files_mapping = []
        for path in self.file_paths:
            full_path = os.path.join(self.repo_local_path, path.lstrip("/"))
            if not os.path.exists(full_path):
                print(f"⚠️ File not found: {full_path}")
                continue
            
            file_git_path = generate_git_file_url(local_file_path = full_path, repo_local_path = self.repo_local_path, repo_url = self.repo_url, branch = self.git_branch_name)
            print(f"🛠️ Parsing ({self.project_name}): {file_git_path}")
            
            parser = TreeSitterParser.create_parser(
                file_path=full_path, 
                realtive_path=full_path, 
                project_name=self.full_project_name,
                file_git_path=file_git_path
            )

            entire_file_mapping = [parser.enitre_file_parsing()]
            entire_file_mapping.extend(parser.functions_parsing())
            entire_file_mapping.extend(parser.test_parsing())

            try:
                project_files_mapping.extend(entire_file_mapping)
                self.counter += 1
            except (TypeError, ValueError) as e:
                print(f"Failed to update with: {e}")

        self.parsed_files = project_files_mapping
        json_file_path = os.path.join(self.repo_local_path, f"{self.project_name}_parsed.json")

        with open(json_file_path, "w", encoding="utf-8") as json_file:
            json.dump(self.parsed_files, json_file, indent=4)

        return json_file_path
