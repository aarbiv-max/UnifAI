import re
import os
import uuid
from .tree_sitter_parser import TreeSitterParser

PYTHON_LANGUAGE_PATH = '/home/cloud-user/Projects/playGround/tree-sitter-playground/tree-sitter-python/libtree-sitter-python.so'
PYTHON_FILE_PATH = '/home/cloud-user/Projects/example/test/test_sample.py'

class PythonParser(TreeSitterParser):
    """
    A parser for Python files using tree-sitter.
    
    This class extends the TreeSitterParser base class to provide Python-specific
    parsing functionality, including detection of imports, test files, and extraction
    of file metadata.
    """

    def __init__(self, language_path=PYTHON_LANGUAGE_PATH, language_name='python', 
                 file_path=PYTHON_FILE_PATH, realtive_path=PYTHON_FILE_PATH, project_name="", file_git_path=""):
        """
        Initialize the Python parser with the given parameters.
        
        Args:
            language_path (str): Path to the tree-sitter language .so file
            language_name (str): Name of the language ('python')
            file_path (str): Absolute path to the file to be parsed
            realtive_path (str): Relative path from the project root
            project_name (str): Name of the project
        """
        super().__init__(language_path, language_name, file_path, realtive_path, project_name, file_git_path)

    def get_module_node(self, root_node):
        """
        Get the module node from the root node.
        
        In tree-sitter-python, the top-level node is a 'module' which contains all
        the statements in the file.
        
        Args:
            root_node: The root node of the tree-sitter parse tree
            
        Returns:
            The module node, or None if not found
        """
        if root_node.type == 'module':
            return root_node
        return None

    def get_import_nodes(self, module_node):
        """
        Get all import nodes from the module node.
        
        Args:
            module_node: The module node from the parse tree
            
        Returns:
            List of import nodes (import_statement and import_from_statement)
        """
        import_nodes = []

        if not module_node:
            return import_nodes

        for child in module_node.children:
            if child.type in ('import_statement', 'import_from_statement'):
                import_nodes.append(child)

        return import_nodes

    def get_import_node_code(self, root_node):
        """
        Get the code of all imports in a Python file.
        
        Args:
            root_node: The root node of the parse tree
            
        Returns:
            str: A string containing all import statements
        """
        module_node = self.get_module_node(root_node)
        if not module_node:
            return ""

        import_nodes = self.get_import_nodes(module_node)
        import_statements = []

        for node in import_nodes:
            import_statements.append(node.text.decode("utf-8").strip())

        return "\n".join(import_statements)

    def is_test_file(self, content):
        """
        Determine if a file is a test file based on its content.
        
        A file is considered a test if it contains 'pytest' or '@pytest' strings.
        
        Args:
            content (str): The content of the file
            
        Returns:
            bool: True if the file is a test file, False otherwise
        """
        return '`pytest`' in content or '@pytest' in content or 'pytest' in content

    def get_all_classes(self, module_node):
        """
        Helper function to get all class definitions in the file.
        
        Args:
            module_node: The module node from the parse tree
            
        Returns:
            list: A list of class names defined in the file
        """
        all_classes = []

        if not module_node:
            return all_classes

        for child in module_node.children:
            if child.type == 'class_definition':
                # In tree-sitter-python, the class name is in the identifier node
                for node in child.children:
                    if node.type == 'identifier':
                        all_classes.append(node.text.decode("utf-8"))
                        break

        return all_classes

    def get_all_functions(self, module_node):
        """
        Helper function to get all function definitions in the file.
        
        Args:
            module_node: The module node from the parse tree
            
        Returns:
            list: A list of function names defined in the file
        """
        all_functions = []

        if not module_node:
            return all_functions

        for child in module_node.children:
            if child.type == 'function_definition':
                # In tree-sitter-python, the function name is in the identifier node
                for node in child.children:
                    if node.type == 'identifier':
                        all_functions.append(node.text.decode("utf-8"))
                        break

        return all_functions

    def get_global_variables(self, module_node):
        """
        Helper function to get all global variable assignments in the file.
        
        Args:
            module_node: The module node from the parse tree
            
        Returns:
            str: A string containing all global variable assignments
        """
        global_vars = []

        if not module_node:
            return ""

        for child in module_node.children:
            if child.type == 'expression_statement':
                for subchild in child.children:
                    if subchild.type == 'assignment':
                        global_vars.append(subchild.text.decode("utf-8").strip())

        return "\n".join(global_vars)

    def entire_file_parsing(self, python_file_names_mapping=None):
        """
        Parse the entire Python file and extract relevant information.
        
        Args:
            python_file_names_mapping: Optional mapping of file names
            
        Returns:
            dict: A dictionary containing metadata about the parsed file
        """
        def extract_entire_code(node, content, file_type):
            """
            Helper function to extract entire Python code and metadata.
            
            Args:
                node: The root node of the parse tree
                content: The content of the file
                file_type: The type of the file ('test' or 'file')
                
            Returns:
                dict: A dictionary containing metadata about the parsed file
            """
            module_node = self.get_module_node(node)
            used_imports = self.get_import_node_code(node)
            global_vars = self.get_global_variables(module_node)
            all_classes = self.get_all_classes(module_node)
            all_functions = self.get_all_functions(module_node)

            return {
                "element_type": file_type,
                "project_name": self.project_name,
                "uuid": str(uuid.uuid4()),
                "name": os.path.splitext(os.path.basename(self.realtive_path))[0],
                "imports": used_imports if used_imports else "",  # Mapped resource imports
                "classes": ", ".join(all_classes) if all_classes else "",
                "functions": ", ".join(all_functions) if all_functions else "",
                "file_location": self.file_git_path,
                "code": content,
                "global_vars": global_vars if global_vars else "",
                "tags": ""
            }

        root_node, content = self.get_root_node()
        file_type = "test" if self.is_test_file(content) else "file"
        return extract_entire_code(root_node, content, file_type)