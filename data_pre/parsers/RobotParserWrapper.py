import json
import os
from backend.be_utils.git.utils import generate_git_file_url
from data_pre.parsers.BaseParser import BaseParser
from data_pre.parsers.components.robot_parser import RobotParser

class RobotParserWrapper(BaseParser):
    def __init__(self, repo_local_path, file_paths, project_name, organization_name, repo_url, git_branch_name):
        """
        Parser for Robot Framework.
        """
        super().__init__(repo_local_path, file_paths, project_name, organization_name, repo_url, git_branch_name)
        self.robot_file_keywords_mapping = {}
        self.robot_file_libraries_mapping = {}
        self.robot_file_names_mapping = {}

    def add_to_dict(self, file_name, objects_list, target_dict):
        """
        Adds objects to the target_dict where the key is the 'name' from the object.
        The value is a dictionary with two keys:
          - 'file_names': a list of file names
          - 'documentation': a list of documentation strings.

        If the 'name' already exists, append the file_name and documentation to the respective lists.
        """
        for obj in objects_list:
                name = obj['name']
                documentation = obj['documentation']

                if name not in target_dict:
                    # Add a new entry with 'file_names' and 'documentation' lists
                    target_dict[name] = {
                        'file_names': [file_name],
                        'documentation': [documentation]
                    }
                else:
                    # Append to existing lists
                    target_dict[name]['file_names'].append(file_name)
                    target_dict[name]['documentation'].append(documentation)

    def parse_files(self):
        """
        Parses Robot Framework files using RobotParser.
        """
        robot_files_internal_functions_mapping = []

        for path in self.file_paths:
            full_path = os.path.join(self.repo_local_path, path.lstrip("/"))
            if not os.path.exists(full_path):
                print(f"⚠️ File not found: {full_path}")
                continue

            print(f"🤖 Parsing Robot Framework File: {full_path}")
            file_git_path = generate_git_file_url(local_file_path = full_path ,repo_local_path = self.repo_local_path, repo_url = self.repo_url, branch = self.git_branch_name )
            parser = RobotParser(file_path=full_path, realtive_path=full_path, project_name=self.full_project_name)

            # Extract keywords & their details
            file_name, keywords_list = parser.get_keywords_name_list()
            relative_file_name = os.path.relpath(full_path, self.repo_local_path)
            self.robot_file_names_mapping[file_name] = relative_file_name

            # Add extracted keywords to the mapping
            self.add_to_dict(relative_file_name, keywords_list, self.robot_file_keywords_mapping)

            # Parse the entire file & internal function calls
            entire_file_mapping = [parser.enitre_file_parsing(self.robot_file_names_mapping)]
            internal_functions_mapping = parser.get_full_internal_calls_list(
                self.robot_file_keywords_mapping,
                self.robot_file_libraries_mapping
            )

            entire_file_mapping.extend(internal_functions_mapping)

            try:
                robot_files_internal_functions_mapping.append(entire_file_mapping)
                self.counter += len(entire_file_mapping)
            except (TypeError, ValueError) as e:
                print(f"Failed to update with: {e}")

        # ✅ **Flatten the list** (robot_files_internal_functions_mapping → flat list)
        robot_files_internal_functions_mapping_flatten = [
            obj for internal_list in robot_files_internal_functions_mapping for obj in internal_list
        ]

        # ✅ **Filter out empty "code" entries**
        robot_files_internal_functions_mapping_flatten = list(
            filter(lambda obj: obj["code"] != "", robot_files_internal_functions_mapping_flatten)
        )

        # ✅ **Save the final JSON file**
        json_file_path = os.path.join(self.repo_local_path, f"{self.project_name}_robot_parsed.json")
        with open(json_file_path, "w", encoding="utf-8") as json_file:
            json.dump(robot_files_internal_functions_mapping_flatten, json_file, indent=4)

        return json_file_path
