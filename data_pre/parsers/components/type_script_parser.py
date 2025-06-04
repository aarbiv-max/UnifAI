import ctypes
import re
import os
import uuid
from .tree_sitter_parser import TreeSitterParser
# Get the path to so_files inside data_pre
current_dir = os.path.dirname(os.path.abspath(__file__))
data_pre_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
so_files_dir = os.path.join(data_pre_dir, "so_files")
TYPE_SCRIPT_LANGUAGE_PATH = os.path.join(so_files_dir, "tree-sitter-typescript.so")
go_lib = ctypes.CDLL(TYPE_SCRIPT_LANGUAGE_PATH)

TYPE_SCRIPT_FILE_PATH =  '/home/cloud-user/Projects/tag-integration-with-mta/tackle-ui-tests/cypress/e2e/tests/administration/jira-connection/crud.test.ts'

class TypeScriptParser(TreeSitterParser):
    def __init__(self, language_path=TYPE_SCRIPT_LANGUAGE_PATH, language_name='typescript', file_path=TYPE_SCRIPT_FILE_PATH, realtive_path=TYPE_SCRIPT_FILE_PATH, project_name="", file_git_path=""):
        super().__init__(language_path, language_name, file_path, realtive_path, project_name, file_git_path)

    def get_declaration_node(self, root_node, declaration_name):
        try:
            for child in root_node.children:
                if child.type == declaration_name:
                    return child
        except:
            return None
    
    def get_all_imports(self, root_node):
        """Helper function to get all the imports of the file"""
        all_imports = []
        for node in root_node.children:
            if node.type == "import_statement":
                # Extract import details
                import_details = self._extract_import_details(node)
                if import_details:
                    all_imports.append(import_details)
        return all_imports
    
    def _extract_import_details(self, import_node):
        """Extract detailed import information"""
        # Extract import path
        import_names = []
        import_path_node = import_node.child_by_field_name("source")
        if not import_path_node:
            return None
        
        import_path = import_path_node.text.decode("utf-8").strip("'\"")

        # Find import names
        for child in import_node.children:
            # Check for import_clause
            if child.type == "import_clause":
                # Look for named_imports within import_clause
                for subchild in child.children:
                    if subchild.type == "named_imports":
                        for specifier in subchild.children:
                            if specifier.type == "import_specifier":
                                # Find name within import_specifier
                                for name_child in specifier.children:
                                    if name_child.type == "identifier":
                                        import_names.append(name_child.text.decode("utf-8"))

        return {
            "import_name": import_names,
            "import_path": import_path
        } if import_names else None
    
    def get_relevant_imports(self, code, all_imports):
        """Helper function to get relevant imports for a code block"""
        relevant_imports = []
        for import_info in all_imports:
            # Check if any of the import names are in the code
            matching_imports = [imp_name for imp_name in import_info['import_name'] if imp_name in code]
            if matching_imports:
                relevant_imports.append({"import_name": matching_imports, "import_path": import_info['import_path']})
        return relevant_imports
        
    def enitre_file_parsing(self):
        def extract_entire_code(node, content, file_type):
            """Helper function to extract entire typescript file code."""
            used_imports = self.get_all_imports(node)
            return {
                "element_type": f"{file_type}",
                "project_name": self.project_name,
                "uuid": str(uuid.uuid4()),
                "name": f"{os.path.basename(self.realtive_path)}",
                "imports": f"{used_imports}" if len(used_imports) > 0 else "",
                "file_location": self.file_git_path,
                "code": content,
            }

        root_node, content = self.get_root_node()
        file_type = "file"
        return extract_entire_code(root_node, content, file_type)

    def functions_parsing(self):
        root_node, content = self.get_root_node()
        functions = []

        # Get all imports
        all_imports = self.get_all_imports(root_node)

        def is_valid_first_level_function(node, current_function_depth):
            """
            Check if the node represents a first-level named function to be parsed
            Validates:
            1. Function is at root level or directly in a class
            2. Function declaration with a name
            3. Method definition with a name
            4. Const declaration with a named function
            5. Excludes nested functions
            """
            # Only parse functions at depth 0 (root level)
            if current_function_depth > 0:
                return False

            # Direct function declaration or method definition
            if node.type in ["function_declaration", "method_definition"]:
                name_node = node.child_by_field_name("name")
                return name_node is not None

            # Const declaration with named function
            if node.type == "lexical_declaration":
                for child in node.children:
                    if child.type == "variable_declarator":
                        name_node = child.child_by_field_name("name")
                        initializer = child.child_by_field_name("value")
                        
                        # Check if it's a named function or arrow function
                        if (name_node and 
                            initializer and 
                            initializer.type in ["function_declaration", "arrow_function", "function_expression"]):
                            return True
            
            return False

        def extract_function_details(node, parent_info=None):
            """
            Extract function details for named functions
            """
            # Handle direct function declaration or method definition
            if node.type in ["function_declaration", "method_definition"]:
                name_node = node.child_by_field_name("name")
                func_name = name_node.text.decode("utf-8") if name_node else None
                func_code = node.text.decode("utf-8")
            
            # Handle const function assignment
            elif node.type == "lexical_declaration":
                # Find the variable name and function
                for child in node.children:
                    if child.type == "variable_declarator":
                        name_node = child.child_by_field_name("name")
                        func_name = name_node.text.decode("utf-8") if name_node else None
                        
                        initializer = child.child_by_field_name("value")
                        func_code = initializer.text.decode("utf-8") if initializer else None
                        #TODO: Below line is up to deisgn decision of prompt_lab templates (what is expected from the parser)
                        #func_code = child.text.decode("utf-8")
            
            # If no valid name found, return None
            if not func_name:
                return None

            # Get relevant imports
            used_imports = self.get_relevant_imports(func_code, all_imports)

            # Prepare function details
            function_details = {
                "element_type": "function",
                "project_name": self.project_name,
                "uuid": str(uuid.uuid4()),
                "name": f"{func_name}",
                "imports": f"{used_imports}" if len(used_imports) > 0 else "",
                "file_location": self.file_git_path,
                "code": f"{func_code}",
                "parent": f"{parent_info}" or ""
            }

            return function_details

        def traverse_and_extract_functions(node, current_function_depth=0, parent_type=None, parent_name=None):
            """
            Recursively traverse the AST to find first-level named function declarations
            """
            # Prepare parent information if applicable
            parent_info = {}
            if parent_type and parent_name:
                parent_info = {
                    "type": parent_type,
                    "name": parent_name
                }

            # Track function depth based on function-like nodes
            function_increment = 1 if node.type in [
                "function_declaration", 
                "method_definition", 
                "arrow_function", 
                "function_expression",
                "lexical_declaration"
            ] else 0

            # Check for class declarations to get class name
            if node.type == "class_declaration":
                name_node = node.child_by_field_name("name")
                class_name = name_node.text.decode("utf-8") if name_node else "UnnamedClass"
                parent_type = "class_declaration"
                parent_name = class_name

            # Check for function declarations, method definitions, and const function declarations
            if is_valid_first_level_function(node, current_function_depth):
                function = extract_function_details(node, parent_info)
                if function:
                    functions.append(function)
            
            # Recursively traverse children
            for child in node.children:
                # Pass updated function depth to nested traversal
                traverse_and_extract_functions(
                    child, 
                    current_function_depth + function_increment, 
                    parent_type, 
                    parent_name
                )

        # Start the recursive traversal
        traverse_and_extract_functions(root_node)
        
        return functions

    def test_parsing(self):
        root_node, content = self.get_root_node()
        tests = []
        test_cases = []

        def find_describe_and_it_blocks(node):
            """Helper function to find both describe and it blocks using iteration"""
            describe_blocks = []
            it_blocks = []

            def traverse(current_node):
                # Check for describe block
                if current_node.type == "call_expression":
                    func_node = current_node.child_by_field_name("function")
                    if func_node and func_node.text.decode("utf-8") == "describe":
                        describe_blocks.append(current_node)
                    
                    # Check for it block
                    if func_node and func_node.text.decode("utf-8") == "it":
                        it_blocks.append(current_node)
                
                # Recurse through children
                for child in current_node.children:
                    traverse(child)

            traverse(node)
            return describe_blocks, it_blocks

        # Get initial data
        all_imports = self.get_all_imports(root_node)

        # Find all 'describe' and 'it' blocks
        describe_blocks, it_blocks = find_describe_and_it_blocks(root_node)

        # Process each 'describe' block
        for describe_block in describe_blocks:
            test_code = describe_block.text.decode("utf-8")
            
            # Extract test name from the first string argument
            test_name = ""
            args = describe_block.children
            for arg in args:
                if arg.type == "arguments":
                    for child in arg.children:
                        if child.type == "string":
                            test_name = child.text.decode("utf-8").strip('"\'')
                            break
                    break
            
            used_imports = self.get_relevant_imports(test_code, all_imports)
            test = {
                "element_type": "test",
                "project_name": self.project_name,
                "uuid": str(uuid.uuid4()),
                "name": f"{test_name}",
                "imports": f"{used_imports}" if len(used_imports) > 0 else "",
                "file_location": self.file_git_path,
                "code": f"{test_code}",
            }
            
            tests.append(test)

        # Process each 'it' block
        for it_block in it_blocks:
            test_case_code = it_block.text.decode("utf-8")
            
            # Extract test case name from the first string argument
            test_case_name = ""
            args = it_block.children
            for arg in args:
                if arg.type == "arguments":
                    for child in arg.children:
                        if child.type == "string":
                            test_case_name = child.text.decode("utf-8").strip('"\'')
                            break
                    break
            
            used_imports = self.get_relevant_imports(test_case_code, all_imports)
            test_case = {
                "element_type": "test case",
                "project_name": self.project_name,
                "uuid": str(uuid.uuid4()),
                "name": f"{test_case_name}",
                "imports": f"{used_imports}" if len(used_imports) > 0 else "",
                "file_location": self.file_git_path,
                "code": f"{test_case_code}",
            } 
            test_cases.append(test_case)
        
        tests.extend(test_cases)
        return tests

"""
TODO: Need to support default imports
E.G. import * as commonView from "../../../views/common.view";

TODO: Anonymous functions won't be parsed due to design decision, other functions definitions will be treated: 
function regularFunction() { ... }  // Will be parsed
const namedFunction = function() { ... }  // Will be parsed
class SomeClass {
     public static open() { ... }  // Will be parsed (method definition)
}
someObj.method(() => { ... })  // Will NOT be parsed (internal anonymous)

TODO: Regex handling:
1) Currently if for example there are 2 imports called `['click', 'clickByText']`, assuming that clickByText. appear as part of the code.
   In that scenario both of the imports will be mapped since 'clickByText' contain the word 'click', currently 'imports' key mapping based on regex logic.

2) Under /home/cloud-user/Projects/tag-integration-with-mta/tackle-ui-tests/cypress/utils/utils.ts:manageCredentialsForMultipleApplications
   There is a comment: // TODO: Add validation of application list, should be separated with coma in management's modal
   Since modal is part of the import_list it add it to 'imorts' as {'import_name': ['modal'], 'import_path': '../e2e/views/common.view'}
   We need to make sure we are not taking comment into account when mapping elements in the parser

3) Check how the parser interact with "import { A as B, C as D, E as F, } from "Z";" in the code the usage will be B. / D. 
   We need to check how we treat above example via imports parsing since if we put there 'A as B' it won't work with current logic.

TODO: Do we want to enrich types knowldge, by leveraging which types some elements are using?

TODO: Functional Component Support (should be treated similiar to Class Component):
1) When functional component is declared, reference 'useFocusHandlers' ({self.project_name}/client/src/app/components/FilterToolbar/MultiselectFilterControl.tsx) it parsed as function.
2) Once there are inner functions implementation under 'functional component' currently we are not parsing them as separating functions within our parser.
3) We should consider treat them as single function elements which will be parsed by our parser (same as we are doing with direct children of 'Class Component',
once those direct children elements are basically function declarations (whether it's anonymous function or any other function definition))
"""  

# Should go over the following website (making sure we cover all the basics of JS elements):
# https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Lexical_grammar

# JS grammar: https://github.com/tree-sitter/tree-sitter-javascript/blob/master/grammar.js
# TS grammar: https://github.com/tree-sitter/tree-sitter-typescript/blob/master/common/define-grammar.js
