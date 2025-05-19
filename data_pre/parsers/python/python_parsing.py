import os
import json
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.tree_sitter_parser import TreeSitterParser

# AGENT_NAME = '(DEEP_CODE)'
AGENT_NAME = '(TAG)'
PYTHON_FOLDER = '/tmp/galaxy_ng'
PYTHON_PROJECT_NAME = 'ansible/galaxy_ng'
PYTHON_FILE_NAME = 'galaxy_ng'
PYTHON_SUFFIXES = [".py"]

def write_to_file(my_list, filename="TC's_mapping_list.txt"):
    # Write each item of the list to a new line in the file
    with open(filename, "w") as file:
        file.write(my_list)

def get_file_paths_with_suffixes(folder_path, suffixes, ignore_folders=None, include_subfolders=None):
    """
    Get file paths with specific suffixes, while ignoring specific folders and allowing selective inclusion of subfolders.
    The function ensures that if a folder matches ignore_folders, its subfolders specified in include_subfolders will still be traversed correctly.
    :param folder_path: The root folder to search in.
    :param suffixes: List of file suffixes to include (e.g., [".go"]).
    :param ignore_folders: List of folder names (directly under folder_path) to ignore.
    :param include_subfolders: List of specific subfolder paths to include.
    :return: List of file paths matching the criteria.
    """
    file_paths = []
    ignore_folders = set(ignore_folders or [])
    include_subfolders = set(include_subfolders or [])

    # Walk through the directory
    for root, dirs, files in os.walk(folder_path):
        # Relative path of the current directory
        rel_path = os.path.relpath(root, folder_path)

        # Check if the current folder should be skipped
        if any(rel_path == ignore or rel_path.startswith(f"{ignore}/") for ignore in ignore_folders):
            # Allow traversal if explicitly in include_subfolders
            if not any(include.startswith(rel_path) or rel_path.startswith(include) for include in include_subfolders):
                dirs[:] = []  # Prevent recursion into this directory
                continue

        # Process files in the current directory
        for file in files:
            if any(file.endswith(suffix) for suffix in suffixes):
                file_paths.append(os.path.join(root, file))

    return file_paths

def extract_unique_words(paths):
    """
    Extracts a set of unique words from a list of paths.
    Includes directory names and file names without extensions.
    Only includes file names with `.go` suffix.
    Args:
        paths (list): List of file paths as strings.
    Returns:
        set: Set of unique words.
    """
    unique_words = set()

    for path in paths:
        # Split the path into components
        components = path.split(os.sep)
        for component in components:
            # Check if it's a file with an extension
            if "." in component:
                name, extension = os.path.splitext(component)
                # Include only if the extension is .go
                if extension == ".go":
                    unique_words.add(name)
            else:
                # Add directory names
                unique_words.add(component)

    return unique_words

def parser_error_counter(python_files):
    # Initialize a counter and a list for paths
    error_count = 0
    error_paths = []

    # Loop through all the files
    for path in python_files:
        tree_sitter_parser = TreeSitterParser.create_parser(file_path=path)
        node, _ = tree_sitter_parser.get_root_node()

        # Check if the node contains an error
        if tree_sitter_parser.is_error_node(node):
            error_count += 1
            error_paths.append(path)

    # Print the total count and the paths with errors
    print(f"Total number of files with errors: {error_count}")
    print("Paths with errors:")
    for error_path in error_paths:
        print(error_path)

python_files = get_file_paths_with_suffixes(
    PYTHON_FOLDER,
    PYTHON_SUFFIXES,
    # ignore_folders=["vendor"],
    # include_subfolders=["vendor/github.com/openshift-kni/eco-goinfra"]
    )
print(f'python_FILES len: {len(python_files)}')

#########################################################################################################

project_file_names_mapping = {}
project_files_mapping = []
counter = 0

for path in python_files:
    print(f"Current path:{path}")
    realtive_file_path = path.replace(f"{PYTHON_FOLDER}/", "", 1)
    tree_sitter_parser = TreeSitterParser.create_parser(file_path=path, realtive_path=realtive_file_path, project_name=PYTHON_PROJECT_NAME)
    project_entire_file_mapping = [tree_sitter_parser.entire_file_parsing(project_file_names_mapping)]
    project_file_functions_mapping = tree_sitter_parser.internal_elements_parsing()
    project_entire_file_mapping.extend(project_file_functions_mapping)
    counter+= 1
    try:
        project_files_mapping.extend(project_entire_file_mapping)
    except (TypeError, ValueError) as e:
        print(f"Failed to update with: {e}")

json_formatted_str = json.dumps(project_files_mapping, indent=2)
write_to_file(json_formatted_str, filename=f'{PYTHON_FILE_NAME}_Mapping{AGENT_NAME}.json')
print(f"Number Of Parsed Files: {counter}")

# print(f"Parsed Json: \n {json_formatted_str}")