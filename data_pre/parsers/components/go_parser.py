import re
import os
import uuid
from .tree_sitter_parser import TreeSitterParser
import sys
import ctypes

# Get the path to so_files inside data_pre
current_dir = os.path.dirname(os.path.abspath(__file__))
data_pre_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
so_files_dir = os.path.join(data_pre_dir, "so_files")
GO_LANGUAGE_PATH = os.path.join(so_files_dir, "go.so")
go_lib = ctypes.CDLL(GO_LANGUAGE_PATH)

GO_FILE_PATH =  '/home/cloud-user/Projects/openshift-tests-private/test/extended/clusterinfrastructure/metrics.go'

class GoParser(TreeSitterParser):
    def __init__(self, language_path=GO_LANGUAGE_PATH, language_name='go', file_path=GO_FILE_PATH, realtive_path=GO_FILE_PATH, project_name=""):
        super().__init__(language_path, language_name, file_path, realtive_path, project_name)

    def get_declaration_node(self, root_node, declaration_name):
        try:
            for child in root_node.children:
                if child.type == declaration_name:
                    return child
        except:
            return None
        
    # Helper function to get all the imports of the function
    def get_all_imports(self, root_node):
        all_imports = []
        import_decl = self.get_declaration_node(root_node, "import_declaration")
        if import_decl:
            for child in import_decl.children:
                if child.type == "import_spec_list":
                    for import_spec_list_child in child.children:
                        if import_spec_list_child.type == "import_spec":
                            all_imports.append(import_spec_list_child.text.decode("utf-8"))
        return all_imports
    
    def get_all_structs(self, root_node):
        """Helper function to get all struct definitions in the file."""
        all_structs = []
        for child in root_node.children:
            if child.type == "type_declaration":
                for spec in child.children:
                    if spec.type == "type_spec":
                        type_node = spec.child_by_field_name("type")
                        if type_node and type_node.type == "struct_type":
                            struct_name = spec.child_by_field_name("name").text.decode("utf-8")
                            all_structs.append(struct_name)
        return all_structs

    def get_all_interfaces(self, root_node):
        """Helper function to get all interface definitions in the file."""
        all_interfaces = []
        for child in root_node.children:
            if child.type == "type_declaration":
                for spec in child.children:
                    if spec.type == "type_spec":
                        type_node = spec.child_by_field_name("type")
                        if type_node and type_node.type == "interface_type":
                            interface_name = spec.child_by_field_name("name").text.decode("utf-8")
                            all_interfaces.append(interface_name)
        return all_interfaces

    def get_used_types(self, code, all_types):
        """Helper function to find used types (structs or interfaces) in a piece of code."""
        used_types = []
        for type_name in all_types:
            if re.search(r'\b' + re.escape(type_name) + r'\b', code):
                used_types.append(type_name)
        return used_types
        
    def entire_file_parsing(self):
        def get_file_package(root_node):
            """Helper function to get the code of all the imports in a go file."""
            imports_file_locations = {}
            package_node = self.get_declaration_node(root_node, declaration_name="package_clause")
            package_code = package_node.text.decode("utf-8").strip() if package_node else ""
            return package_code
        
        def get_import_node_code(root_node):
                """Helper function to get the code of all the imports in a go file."""
                imports_file_locations = {}
                imports_node = self.get_declaration_node(root_node, declaration_name="import_declaration")
                imports_code = imports_node.text.decode("utf-8").strip() if imports_node else ""
                return imports_code

        def extract_entire_code(node, content, file_type):
            """Helper function to extract entire robot code."""
            used_imports = get_import_node_code(node)
            package_name = get_file_package(node)
            
            return {
                "element_type": file_type,
                "project_name": self.project_name,
                "uuid": str(uuid.uuid4()),
                "name": os.path.basename(self.realtive_path),
                "imports": f"{used_imports}" if len(used_imports) > 0 else "",  # Mapped resource imports
                "structs": "",
                "interfaces": "",
                "file_location": f"github.com/{self.project_name}/{self.realtive_path}",
                "code": content,
                "global_vars": "",
                "package": f"{package_name}" if package_name else "",
                "tags": ""
            }
        root_node, content = self.get_root_node()
        file_type = "file"
        return extract_entire_code(root_node, content, file_type)
    
    def functions_parsing(self):
        root_node, content = self.get_root_node()
        functions = []

        # Helper function to get package name
        def get_package_name(node):
            package_node = self.get_declaration_node(node, "package_clause")
            return package_node.text.decode("utf-8").split()[-1] if package_node else ""
        
        # Helper function to get relevant imports for a function
        def get_relevant_imports(func_code, all_imports):
            relevant_imports = []
            for imp in all_imports:
                import_name = imp.split()[-1].strip('"').split('/')[-1]
                if re.search(r'\b' + re.escape(import_name) + r'\b', func_code):
                    relevant_imports.append(imp)
            return relevant_imports

        # Helper function to get global variables
        def get_global_vars(root_node):
            global_vars = {}
            for child in root_node.children:
                if child.type == "var_declaration":
                    # var_name = child.child_by_field_name("name").text.decode("utf-8")
                    # var_value = child.text.decode("utf-8")
                    # global_vars[var_name] = var_value
                    for var_spec in child.children:
                        if var_spec.type == "var_spec":
                            var_name = var_spec.child_by_field_name("name").text.decode("utf-8")
                            if var_spec.child_by_field_name("value"):
                                var_value = var_spec.child_by_field_name("value").text.decode("utf-8")
                                global_vars[var_name] = var_value
            return global_vars
        
        # Helper function to get global variables used in a function
        def get_used_global_vars(func_code, all_global_vars):
            used_global_vars = {}
            for var_name, var_value in all_global_vars.items():
                if re.search(r'\b' + re.escape(var_name) + r'\b', func_code):
                    used_global_vars[var_name] = var_value
            return used_global_vars

        # Get all imports/structs/interfaces
        all_imports = self.get_all_imports(root_node)
        all_structs = self.get_all_structs(root_node)
        all_interfaces = self.get_all_interfaces(root_node)

        # Get global variables
        global_vars = get_global_vars(root_node)

        # Get package name
        package_name = get_package_name(root_node)

        # Find all function declarations
        for child in root_node.children:
            if child.type == "function_declaration" or child.type == "method_declaration":
                func_name = child.child_by_field_name("name").text.decode("utf-8")
                func_code = child.text.decode("utf-8")
                
                used_imports = get_relevant_imports(func_code, all_imports)
                used_structs = self.get_used_types(func_code, all_structs)
                used_interfaces = self.get_used_types(func_code, all_interfaces)
                global_vars = get_used_global_vars(func_code, global_vars)
                function = {
                    "element_type": "function",
                    "project_name": self.project_name,
                    "uuid": str(uuid.uuid4()),
                    "name": func_name,
                    "imports": f"{used_imports}" if len(used_imports) > 0 else "",
                    "structs": f"{used_structs}" if len(used_structs) > 0 else "",
                    "interfaces": f"{used_interfaces}" if len(used_interfaces) > 0 else "",
                    "file_location": f"github.com/{self.project_name}/{self.realtive_path}",
                    "code": func_code,
                    # "file_code": content,
                    "global_vars": f"{global_vars}" if len(global_vars) > 0 else "",
                    "package": f"{package_name}" if package_name else "",
                    "tags": ""
                }
                functions.append(function)
        
        return functions
    
    def test_parsing(self):
        root_node, content = self.get_root_node()
        tests = []
        test_cases = []

        def get_package_name(node):
            """Helper function to get package name"""
            package_node = self.get_declaration_node(node, "package_clause")
            return package_node.text.decode("utf-8").split()[-1] if package_node else ""

        def get_relevant_imports(test_code, all_imports):
            """Helper function to get relevant imports for a test"""
            relevant_imports = []
            for imp in all_imports:
                import_name = imp.split()[-1].strip('"').split('/')[-1]
                if re.search(r'\b' + re.escape(import_name) + r'\b', test_code):
                    relevant_imports.append(imp)
            return relevant_imports

        def get_global_vars(root_node):
            """Helper function to get all global variables"""
            global_vars = {}
            for child in root_node.children:
                if child.type == "var_declaration":
                    for var_spec in child.children:
                        if var_spec.type == "var_spec":
                            var_name = var_spec.child_by_field_name("name").text.decode("utf-8")
                            if var_spec.child_by_field_name("value"):
                                var_value = var_spec.child_by_field_name("value").text.decode("utf-8")
                                global_vars[var_name] = var_value
            return global_vars

        def get_used_global_vars(test_code, all_global_vars):
            """Helper function to get global variables used in a test"""
            used_global_vars = {}
            for var_name, var_value in all_global_vars.items():
                if re.search(r'\b' + re.escape(var_name) + r'\b', test_code):
                    used_global_vars[var_name] = var_value
            return used_global_vars

        def extract_tags(node):
            """Helper function to extract test tags from square brackets in the description"""
            tags = []
            args = node.child_by_field_name("arguments")
            if args:
                for arg in args.children:
                    if arg.type == "interpreted_string_literal":
                        description = arg.text.decode("utf-8").strip('"')
                        # Find all text within square brackets using regex
                        bracket_tags = re.findall(r'\[(.*?)\]', description)
                        tags.extend(bracket_tags)
            return tags

        # def find_describe_blocks(node):
        #     """Helper function to recursively find g.Describe blocks"""
        #     test_blocks = []
            
        #     if node.type == "call_expression":
        #         func_expr = node.child_by_field_name("function")
        #         if func_expr and func_expr.text.decode("utf-8") == "g.Describe":
        #             test_blocks.append(node)
            
        #     for child in node.children:
        #         test_blocks.extend(find_describe_blocks(child))
                
        #     return test_blocks

        def find_describe_and_it_blocks(node):
            """Helper function to find both g.Describe and g.It blocks using iteration"""
            describe_blocks = []
            it_blocks = []
            nodes_to_visit = [node]
            
            while nodes_to_visit:
                current_node = nodes_to_visit.pop(0)
                
                if current_node.type == "call_expression":
                    func_expr = current_node.child_by_field_name("function")
                    if func_expr:
                        func_name = func_expr.text.decode("utf-8")
                        if func_name == "g.Describe" or func_name == "ginkgo.Describe" or func_name == "Describe" or re.fullmatch(r"\w*Describe(?!Table).*", func_name) or re.fullmatch(r"(?:.+\.)?SIG(?:\w+)?Describe", func_name) or func_name == "When":
                            describe_blocks.append(current_node)
                        elif func_name == "g.It" or func_name == "It" or func_name == "DescribeTable" or func_name == "ginkgo.DescribeTable":
                            it_blocks.append(current_node)
                
                nodes_to_visit.extend(current_node.children)
                    
            return describe_blocks, it_blocks

        # Get initial data
        all_imports = self.get_all_imports(root_node)
        all_structs = self.get_all_structs(root_node)
        all_interfaces = self.get_all_interfaces(root_node)
        global_vars = get_global_vars(root_node)
        package_name = get_package_name(root_node)

        # Find all g.Describe and g.It blocks
        describe_blocks, it_blocks = find_describe_and_it_blocks(root_node)

        # Process each g.Describe block
        for describe_block in describe_blocks:
            test_code = describe_block.text.decode("utf-8")
            
            # Extract test name from the first string argument
            test_name = ""
            args = describe_block.child_by_field_name("arguments")
            if args and args.children:
                for arg in args.children:
                    if arg.type == "interpreted_string_literal":
                        test_name = arg.text.decode("utf-8").strip('"')
                        break
            
            used_imports = get_relevant_imports(test_code, all_imports)
            used_structs = self.get_used_types(test_code, all_structs)
            used_interfaces = self.get_used_types(test_code, all_interfaces)
            global_vars = get_used_global_vars(test_code, global_vars)
            tags = extract_tags(describe_block)
            test = {
                "element_type": "test",
                "project_name": self.project_name,
                "uuid": str(uuid.uuid4()),
                "name": test_name,
                "imports": f"{used_imports}" if len(used_imports) > 0 else "",
                "structs": f"{used_structs}" if len(used_structs) > 0 else "",
                "interfaces": f"{used_interfaces}" if len(used_interfaces) > 0 else "",
                "file_location": f"github.com/{self.project_name}/{self.realtive_path}",
                "code": test_code,
                # "file_code": content,
                "global_vars": f"{global_vars}" if len(global_vars) > 0 else "",
                "package": f"{package_name}" if package_name else "",
                "tags": f"{tags}" if len(tags) > 0 else ""
            }
            
            tests.append(test)

        # Process each g.It block
        for it_block in it_blocks:
            test_case_code = it_block.text.decode("utf-8")
            
            # Extract test case name from the first string argument
            test_case_name = ""
            args = it_block.child_by_field_name("arguments")
            if args and args.children:
                for arg in args.children:
                    if arg.type == "interpreted_string_literal":
                        test_case_name = arg.text.decode("utf-8").strip('"')
                        break
            
            used_imports = get_relevant_imports(test_case_code, all_imports)
            test_case = {
                "element_type": "test case",
                "project_name": self.project_name,
                "uuid": str(uuid.uuid4()),
                "name": test_case_name,
                "imports": f"{used_imports}" if len(used_imports) > 0 else "" ,
                "structs": "",
                "interfaces": "",
                "file_location": f"github.com/{self.project_name}/{self.realtive_path}",
                "code": test_case_code,
                # "file_code": content,
                "global_vars": "",
                "package": "",
                "tags": ""
            } 
            test_cases.append(test_case)
        
        tests.extend(test_cases)
        return tests