from tree_sitter import Language, Parser

class TreeSitterParser:
    def __init__(self, language_path, language_name, file_path, realtive_path, project_name, file_git_path):
        self.language = Language(language_path, language_name)
        self.parser = Parser()
        self.parser.set_language(self.language)
        self.file_path = file_path
        self.realtive_path = realtive_path
        self.project_name= project_name
        self.file_git_path = file_git_path
        
    @staticmethod
    def create_parser(file_path, realtive_path=None, project_name="", file_git_path=""):
        from .robot_parser import RobotParser
        from .go_parser import GoParser
        from .type_script_parser import TypeScriptParser
        from .python_parser import PythonParser
        
        if file_path.endswith('.robot'):
            return RobotParser(file_path=file_path, realtive_path=realtive_path, project_name=project_name, file_git_path = file_git_path)
        elif file_path.endswith('.go'):
            return GoParser(file_path=file_path, realtive_path=realtive_path, project_name=project_name, file_git_path = file_git_path)
        elif file_path.endswith('.ts') or file_path.endswith('.tsx') or file_path.endswith('.js'):
            return TypeScriptParser(file_path=file_path, realtive_path=realtive_path, project_name=project_name, file_git_path = file_git_path)
        elif file_path.endswith('.py'):
            return PythonParser(file_path=file_path, realtive_path=realtive_path, project_name=project_name, file_git_path = file_git_path)
        # TODO: Need to implement parser for TSX (GENIE-86/https://issues.redhat.com/browse/GENIE-86)
        # elif file_path.endswith('.tsx'):
        #     return TypeScriptCompiledParser(file_path=file_path, realtive_path=realtive_path, project_name=project_name)
        else:
            raise ValueError(f"Unsupported file extension for: {file_path}")

    def print_node(self, node, source_code, indent_level=0):
        indent = "  " * indent_level
        node_type = node.type
        start_point = node.start_point
        end_point = node.end_point
        text = source_code[node.start_byte:node.end_byte].decode('utf-8').strip()

        # Print the node's type, position, and content
        print(f"{indent}{node_type} [{start_point[0]}, {start_point[1]}] - [{end_point[0]}, {end_point[1]}]")

        # Print the content if the node has no children
        if len(node.children) == 0:
            print(f"{indent}  {text}")

        # Recursively print child nodes
        for child in node.children:
            self.print_node(child, source_code, indent_level + 1)

    def parse_and_print(self):
        with open(self.file_path, 'rb') as file:
            content = file.read()
        
        tree = self.parser.parse(content)
        root_node = tree.root_node

        self.print_node(root_node, content)

    def get_root_node(self):
        with open(self.file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        tree = self.parser.parse(bytes(content, 'utf-8'))
        root_node = tree.root_node
        return root_node, content

    def is_error_node(self, node):
        """
        Checks if the given node or any child node is of type 'ERROR'.

        Args:
            node: The root node or any node in the tree.

        Returns:
            True if the node or any of its descendants has the type 'ERROR', otherwise False.
        """
        # Check if the current node is of type 'ERROR'
        if node.type == "ERROR":
            return True
        
        # Recursively check the child nodes
        for child in node.children:
            if self.is_error_node(child):
                return True
        
        return False

    def expand_internal_function_calls(self, node_dict):
        """Expands the 'internal_nodes' and 'variable_names' for each node in the dictionary to include all nested sub-dependencies.
        
        Args: 
            node_dict (dict): A dictionary where each key is a node name and the value is another dictionary containing 'internal_nodes' and other keys.
        
        Returns:
            dict: The updated dictionary with 'internal_nodes' and 'variable_names' expanded to include all nested dependencies.
        """
        def collect_dependencies(node_name, visited):
            """
            Recursively collects all sub-dependencies for a given node.

            Args:
                node_name (str): The name of the node to collect dependencies for.
                visited (set): A set of already visited nodes to avoid infinite loops.

            Returns: 
                tuple: A set of all dependencies and a set of all variable names for the given node.
            """
            if node_name in visited:
                return set(), set()  # Avoid infinite loops by returning empty sets for already visited nodes
            visited.add(node_name)
            
            if node_name not in node_dict:
                return set(), set()  # If the node is not in the dictionary, return empty sets

            internal_nodes = node_dict[node_name]['internal_nodes']
            variable_names = node_dict[node_name].get('variable_names', set())

            all_dependencies = set(internal_nodes)  # Start with the direct internal nodes
            all_variable_names = set(variable_names)  # Start with the direct variable names
            
            for internal_node in internal_nodes:
                # Recursively collect dependencies and variable names for each internal node
                dependencies, variables = collect_dependencies(internal_node, visited)
                all_dependencies.update(dependencies)
                all_variable_names.update(variables)
            
            return all_dependencies, all_variable_names
        
        # Update each node's internal_nodes and variable_names to include all sub-dependencies
        for name, details in node_dict.items():
            visited = set()  # Initialize an empty set for visited nodes
            all_dependencies, all_variable_names = collect_dependencies(name, visited)  # Collect all dependencies and variable names for the node
            details['internal_nodes'] = list(all_dependencies)  # Update the node's internal_nodes
            details['variable_names'] = list(all_variable_names)  # Update the node's variable_names

        return node_dict