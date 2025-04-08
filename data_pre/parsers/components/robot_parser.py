import ctypes
import re
import os
from .tree_sitter_parser import TreeSitterParser

# Get the path to so_files inside data_pre
current_dir = os.path.dirname(os.path.abspath(__file__))
data_pre_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
so_files_dir = os.path.join(data_pre_dir, "so_files")
ROBOT_LANGUAGE_PATH = os.path.join(so_files_dir, "robot-eric.so")
go_lib = ctypes.CDLL(ROBOT_LANGUAGE_PATH)
# ROBOT_FILE_PATH = '/home/cloud-user/Projects/Robot-POC-InstructLab/fullTests/6003_Scale_in_out_worker_node_after_failed_scale_out.robot'
# ROBOT_FILE_PATH =  '/home/cloud-user/Projects/Robot-POC-InstructLab/24.0/4022_Add_Rsyslog_rule_and_Delete_Rsyslog_rule.robot'
ROBOT_FILE_PATH =  '/home/cloud-user/Projects/Robot-POC-InstructLab/24.0/8103_Zabbix_server_is_running_in_all_manage_nodes.robot'

class RobotParser(TreeSitterParser):
    def __init__(self, language_path=ROBOT_LANGUAGE_PATH, language_name='robot', file_path=ROBOT_FILE_PATH, realtive_path=ROBOT_FILE_PATH, project_name=""):
        super().__init__(language_path, language_name, file_path, realtive_path, project_name)
        self.test_cases = []

    def get_main_section_node(self, root_node, section_name):
        try:
            for child in root_node.children:
                for body_child in child.children:
                    if body_child.type == section_name:
                        return body_child
        except:
            return None
        
    def add_end_to_if_statements(self, robot_file_path):
        def split_text_sections(lines):
            sections = []
            current_section = []
            
            for line in lines:
                if line.strip() and not line[0].isspace():  # Check if line starts at indentation 0
                    if current_section:
                        sections.append(current_section)
                        current_section = []
                current_section.append(line.rstrip('\n'))  # Remove trailing newline
            
            # Add the last section if it exists
            if current_section:
                sections.append(current_section)
            
            return sections
        
        # Step 1: Read the file content
        with open(robot_file_path, 'r') as file:
            code_lines_text = file.readlines()

        sections_lines = split_text_sections(code_lines_text)
        modified_lines = []
        
        for lines in sections_lines:
            in_if_statement = False
            found_continuation = False
            last_continuation_line = None  # To track the last continuation line
            indent_level = None

            i = 0  # Index for looping through lines
            while i < len(lines):
                line = lines[i]
                stripped_line = line.strip()

                # Step 2: Detect IF statement (match an IF statement not already inside a block)
                if re.match(r'^\s*IF\s+.*$', stripped_line) and not in_if_statement:
                    modified_lines.append(line)
                    indent_level = len(line) - len(line.lstrip())
                    in_if_statement = True
                    i += 1
                    continue

                # Step 3: Detect continuation lines ('...')
                if in_if_statement:
                    if re.match(r'^\s*\.\.\.\s*.*$', stripped_line):  # Match continuation without indentation
                        last_continuation_line = len(modified_lines)  # Track the last continuation line
                        modified_lines.append(line)
                        found_continuation = True
                        i += 1
                        continue

                    # After the continuation, check for END/ELSE in the same indent_level
                    if found_continuation:
                        end_or_else_found = False

                        # Check upcoming lines for END, ELSE
                        for j in range(i, len(lines)):
                            upcoming_line = lines[j]
                            upcoming_line_indent_level = len(upcoming_line) - len(upcoming_line.lstrip())

                            if indent_level == upcoming_line_indent_level:
                                # If END or ELSE is found in the same indent_level, skip adding END
                                if re.match(r'^\s*(END|ELSE)\s*$', upcoming_line):
                                    end_or_else_found = True
                                    break

                        # TODO: Can be added to the IF statement below: current_indent == indent_level (where "current_indent = len(line) - len(line.lstrip())")
                        # If no END/ELSE found, we add END right after the last continuation line
                        if not end_or_else_found and last_continuation_line is not None:
                            # Insert END after the last continuation line if no END or ELSE is found
                            modified_lines.insert(last_continuation_line + 1, ' ' * indent_level + 'END\n')
                            
                        # Reset after handling this IF block
                        in_if_statement = False
                        found_continuation = False
                        last_continuation_line = None

                        # Edge Case | Scenario where we are currently under IF statement that came right after a line we added with END statement
                        if re.match(r'^\s*IF\s+.*$', stripped_line):
                            in_if_statement = True

                    if not found_continuation:
                        # If END statement noticed where there is not any indication for continuation statement, change the state of 'if in_if_statment'
                        if re.match(r'^\s*(END)\s*$', stripped_line):
                            in_if_statement = False

                    # Add the current line to the modified lines
                    modified_lines.append(line)
                    i += 1
                    continue

                # Add lines outside of IF handling
                modified_lines.append(line)
                i += 1

        # Step 5: Write the modified lines back to the file
        with open(robot_file_path, 'w') as file:
            for line in modified_lines:
                file.write(line.rstrip('\n') + '\n')

    def extract_filename_without_extension(self):
        # Get the basename (the part after the last '/')
        filename = os.path.basename(self.file_path)
        # Split the filename on the last '.' and return the part before it
        return os.path.splitext(filename)[0]

    def robot_sections_parser(self):
        root_node = self.get_root_node()

        sections = {
            "settings_section": [],
            "variables_section": [],
            "test_cases_section": [],
            "keywords_section": [],
        }

        for child in root_node.children:
            if child.type == 'section':
                section_header = child.child(0)
                if section_header:
                    section_type = section_header.type
                    if section_type in sections:
                        for item in child.children[0:]:
                            if item.type != 'newline':
                                sections[section_type].append(item.text.decode('utf-8').strip())

        return sections

    def test_cases_parser(self, specific_test_case_name=None):
        def map_internal_use(keyword_body_node, child_type, grandchild_type, target_type, target_child_type, nested_target_type=None, attribute_type=None):
            """
            Maps internal uses of keywords, variables, or settings within a keyword body node.
            
            Args:
                keyword_body_node (Node): The body node of the keyword to inspect.
                child_type (str): The type of child node to look for.
                grandchild_type (str): The type of grandchild node to look for.
                target_type (str): The type of target node to collect.
                target_child_type (str): The type of child within the target node to inspect.
                nested_target_type (str): The type of nested target node to look for within the target child.
                attribute_type (str): The type of attribute node to extract the name from.
            
            Returns:
                set: A set of extracted names.
            """
            internal_uses = set()

            for child in keyword_body_node.children:
                if child.type == child_type:
                    for grandchild in child.children:
                        if grandchild.type == grandchild_type:
                            for target_child in grandchild.children:
                                if target_child.type == target_type:
                                    if nested_target_type:
                                        for target_subchild in target_child.children:
                                            if target_subchild.type == target_child_type:
                                                for nested_child in target_subchild.children:
                                                    if nested_child.type == nested_target_type:
                                                        name_node = None
                                                        for attribute in nested_child.children:
                                                            if attribute.type == attribute_type:
                                                                name_node = attribute
                                                                break
                                                        if name_node:
                                                            name = name_node.text.decode('utf-8').strip()
                                                            internal_uses.add(name)
                                    else:
                                        name_node = target_child
                                        name = name_node.text.decode('utf-8').strip()
                                        internal_uses.add(name)

            return internal_uses                             

        # Using the generic function to map internal keywords, variables, and settings
        def map_internal_keywords_calls(keyword_body_node):
            return map_internal_use(
                keyword_body_node,
                child_type="statement",
                grandchild_type="keyword_invocation",
                target_type="keyword",
                target_child_type=None,
                attribute_type=None,
            )

        def map_internal_variable_use(keyword_body_node):
            return map_internal_use(
                keyword_body_node,
                child_type="statement",
                grandchild_type="keyword_invocation",
                target_type="arguments",
                target_child_type="argument",
                nested_target_type="scalar_variable",
                attribute_type="variable_name",
            )

        def map_internal_setting_use(keyword_body_node):
            return map_internal_use(
                keyword_body_node,
                child_type="statement",
                grandchild_type="keyword_invocation",
                target_type="arguments",
                target_child_type="argument",
                nested_target_type="scalar_variable",
                attribute_type="variable_name",
            )


        def extract_definitions(node, section_type, item_type, name_type, body_type=None, extract_func=None, skip_list=None):
            """
            Extracts definitions from a parsed tree-sitter node.

            Args:
                node (Node): The root node or current node to parse.
                section_type (str): The type of the section node to extract from.
                item_type (str): The type of the item node to extract.
                name_type (str): The type of the name node within the item node.
                body_type (str): The type of the body node within the item node (optional).
                extract_func (func): Additional function to extract specific data (optional).
                skip_list (list): List of strings to skip (optional).

            Returns:
                dict: A dictionary of extracted definitions.
            """
            definitions = {}

            if node.type == section_type:
                for child in node.children:
                    if child.type == item_type:
                        name_node = None
                        body_node = None
                        additional_data = {}

                        for item_child in child.children:
                            if item_child.type == name_type:
                                name_node = item_child
                            if body_type and item_child.type == body_type:
                                body_node = item_child
                            if extract_func:
                                additional_data.update(extract_func(item_child, skip_list, content[child.start_byte:child.end_byte].strip()))

                        if name_node or 'name' in additional_data:
                            name = additional_data.pop('name') if 'name' in additional_data else name_node.text.decode('utf-8').strip() 
                            text = content[child.start_byte:child.end_byte].strip()

                            definitions[name] = {
                                'node': body_node,
                                'text': text,
                                **additional_data
                            }

            for child in node.children:
                definitions.update(extract_definitions(child, section_type, item_type, name_type, body_type, extract_func, skip_list))

            return definitions

        def extract_settings_additional(item_child, skip_list, text):
            settings_data = {}
            setting_value_node = None

            def extract_setting_value(setting_value):
                match = re.search(r'([^/]+)\.robot$', setting_value)
                return match.group(1) if match else setting_value 

            if item_child.type == 'arguments' and skip_list:
                if all(setting not in text for setting in skip_list):
                    for arg_child in item_child.children:
                        if arg_child.type == 'argument':
                            setting_value_node = arg_child
                            break

                if setting_value_node:
                    setting_value = setting_value_node.text.decode('utf-8').strip()
                    settings_data = {
                        'name': extract_setting_value(setting_value),
                        'value': setting_value
                    }

            return settings_data

        def extract_variable_additional(item_child, _, __):
            variable_data = {}
            variable_value_node = None

            if item_child.type == 'arguments':
                for arg_child in item_child.children:
                    if arg_child.type == 'argument':
                        variable_value_node = arg_child
                        break

            if variable_value_node:
                variable_value = variable_value_node.text.decode('utf-8').strip()
                variable_data = {'value': variable_value}

            return variable_data

        # Specific functions for each type of definition
        def extract_keyword_definitions(node):
            return extract_definitions(
                node,
                section_type='keywords_section',
                item_type='keyword_definition',
                name_type='name',
                body_type='body',
                extract_func=lambda item_child, _, __: {
                    'internal_nodes': map_internal_keywords_calls(item_child),
                    'variable_names': map_internal_variable_use(item_child),
                    # 'setting_names': map_internal_setting_use(item_child), 
                    'var_text': '',
                    'setting_text': '',
                }
            )

        def extract_settings_definitions(node):
            return extract_definitions(
                node,
                section_type='settings_section',
                item_type='setting_statement',
                name_type='arguments',
                extract_func=extract_settings_additional,
                skip_list=['Documentation', 'Force Tags', 'Test Timeout', 'Suite Setup', 'Suite Teardown']
            )

        def extract_variable_definitions(node):
            return extract_definitions(
                node,
                section_type='variables_section',
                item_type='variable_definition',
                name_type='variable_name',
                extract_func=extract_variable_additional
            )

        def append_invocations(invocations, node, definitions, child_type, grandchild_type, process_node_func, is_recursive=True):
            for child in node.children:
                if child.type == child_type:
                    for grandchild in child.children:
                        if grandchild.type == grandchild_type:
                            process_node_func(grandchild, invocations, definitions)
                elif is_recursive:
                    invocations = append_invocations(invocations, child, definitions, child_type, grandchild_type, process_node_func)
            return invocations

        def process_keyword_invocation(grandchild, invocations, definitions):
            keyword_name_node = None
            for grandchild_child in grandchild.children:
                if grandchild_child.type == 'keyword':
                    keyword_name_node = grandchild_child
                    break

            if keyword_name_node:
                keyword_name = keyword_name_node.text.decode('utf-8').strip()
                if keyword_name in definitions:
                    test_case_text, variable_text, setting_text = invocations
                    test_case_text += "\n\n" + definitions[keyword_name]['text']
                    variable_text += definitions[keyword_name]['var_text']
                    setting_text += definitions[keyword_name]['setting_text']
                    invocations[:] = [test_case_text, variable_text, setting_text]

        def process_variable_invocation(grandchild, invocations, definitions):
            for arg_child in grandchild.children:
                if arg_child.type == 'arguments':
                    for argument in arg_child.children:
                        if argument.type == 'argument':
                            for var_child in argument.children:
                                if var_child.type == 'scalar_variable':
                                    var_name_node = None
                                    for scalar_variable_child in var_child.children:
                                        if scalar_variable_child.type == 'variable_name':
                                            var_name_node = scalar_variable_child
                                            break

                                    if var_name_node:
                                        var_name = var_name_node.text.decode('utf-8').strip()
                                        if var_name in definitions:
                                            invocations.add(var_name)

        def process_setting_invocation(grandchild, invocations, definitions):
            setting_name_node = None
            for grandchild_child in grandchild.children:
                if grandchild_child.type == 'keyword':
                    setting_name_node = grandchild_child
                    break

            if setting_name_node:
                setting_name = setting_name_node.text.decode('utf-8').strip()
                if setting_name.split('.')[0] in definitions:
                    invocations.add(setting_name)

        def append_keyword_invocations(test_case_text, variable_text, setting_text, node, keyword_definitions):
            invocations = [test_case_text, variable_text, setting_text]
            invocations = append_invocations(invocations, node, keyword_definitions, 'statement', 'keyword_invocation', process_keyword_invocation)
            return invocations

        def append_variable_invocations(variables_names, node, variable_definitions):
            invocations = variables_names
            invocations = append_invocations(invocations, node, variable_definitions, 'statement', 'keyword_invocation', process_variable_invocation)
            return invocations

        def append_settings_invocations(settings_names, node, settings_definitions):
            invocations = settings_names
            invocations = append_invocations(invocations, node, settings_definitions, 'statement', 'keyword_invocation', process_setting_invocation)
            return invocations

        def extract_test_cases(node, keyword_definitions, variable_definitions, settings_definitions):
            if node.type == 'test_case_definition':
                test_case_name = content[node.start_byte:node.end_byte].strip().split('\n')[0]
                if specific_test_case_name and test_case_name != specific_test_case_name:
                    return  # Skip this test case if it does not match the specific name
                    
                setting_text = "*** Settings ***"
                variable_text = "\n\n*** Variables ***"
                
                variables_names = set()
                variables_names = append_variable_invocations(variables_names, node, variable_definitions)

                settings_names = set()
                settings_names = append_settings_invocations(settings_names, node, settings_definitions)

                test_case_text = "\n\n*** Test Cases ***\n\n"
                test_case_text += content[node.start_byte:node.end_byte].strip()

                test_case_text += "\n\n*** Keywords ***"
                test_case_text, variable_text, setting_text = append_keyword_invocations(test_case_text, variable_text, setting_text, node, keyword_definitions)

                # Each var_name which is part of the TC's and do not appear inside the internal keyword function calls must be added 
                for var_name in variables_names:
                    if var_name not in variable_text:
                        variable_text += "\n" + variable_definitions[var_name]['text']
                
                # Each setting_var_call which is part of the TC's and do not appear inside the internal keyword function calls must be added
                for setting_name in settings_names:
                    if setting_name.split('.')[0] not in setting_text:
                        setting_text += "\n" + settings_definitions[setting_name.split('.')[0]]['text']

                self.test_cases.append(setting_text + variable_text + test_case_text)

            for child in node.children:
                extract_test_cases(child, keyword_definitions, variable_definitions, settings_definitions)

        root_node, content = self.get_root_node()
        keyword_definitions = extract_keyword_definitions(root_node)
        variable_definitions = extract_variable_definitions(root_node)
        settings_definitions = extract_settings_definitions(root_node)
        self.expand_internal_function_calls(keyword_definitions)

        for keyword in keyword_definitions:
            for internal_keyword in keyword_definitions[keyword]['internal_nodes']:
                # Note: internal_keyword also includes declared keywords which make use of 'Settings' definitions  
                if keyword_definitions.get(internal_keyword, None):
                    keyword_definitions[keyword]['text'] += "\n\n" + keyword_definitions[internal_keyword]['text']

                if settings_definitions.get(internal_keyword.split('.')[0], None):
                    keyword_definitions[keyword]['setting_text'] += "\n" + settings_definitions[internal_keyword.split('.')[0]]['text'] 

            for var_name in keyword_definitions[keyword]['variable_names']: 
                if variable_definitions.get(var_name, None):
                    keyword_definitions[keyword]['var_text'] += "\n" + variable_definitions[var_name]['text'] 

        extract_test_cases(root_node, keyword_definitions, variable_definitions, settings_definitions)

        return self.test_cases

    def combine_robot_tests(self, content1, content2):
        def extract_sections(content):
            section_mapping = {
                'settings': 'settings',
                'variables': 'variables',
                'test cases': 'test_cases',
                'keywords': 'keywords'
            }

            sections = {key: [] for key in section_mapping.values()}
            current_section = None

            lines = content.splitlines()

            for line in lines:
                stripped_line = line.strip()
                if stripped_line.startswith('***'):
                    section_name = stripped_line.replace('*', '').strip().lower()
                    current_section = section_mapping.get(section_name)
                elif current_section:
                    sections[current_section].append(line)  # Preserve original line (with indentation)

            return sections

        def combine_sections(sections1, sections2):
            combined_sections = {}

            for section_name, lines in sections1.items():
                combined_sections[section_name] = lines.copy()
                if section_name in sections2:
                    for line in sections2[section_name]:
                        if line not in combined_sections[section_name]:
                            combined_sections[section_name].append(line)
                        # Duplicate code can appear under the following sections: keywords/test cases 
                        # elif section_name == 'test_cases':
                        #     combined_sections[section_name].append(line)

            for section_name, lines in sections2.items():
                if section_name not in combined_sections:
                    combined_sections[section_name] = lines

            return combined_sections

        def generate_combined_test(combined_sections):
            combined_test = []

            for section_name, lines in combined_sections.items():
                combined_test.append(f'*** {section_name.replace("_", " ").capitalize()} ***')

                if section_name in ['test_cases', 'keywords']:
                    combined_test.extend(lines)
                    combined_test.append('')  # Add a blank line between different lines for these sections
                else:
                    combined_test.extend(line for line in lines if line.strip())  # No empty lines between different lines

                if section_name not in ['test_cases', 'keywords']:
                    combined_test.append('')  # Add a blank line between sections

            return '\n'.join(combined_test)

        sections1 = extract_sections(content1)
        sections2 = extract_sections(content2)

        combined_sections = combine_sections(sections1, sections2)
        combined_test = generate_combined_test(combined_sections)

        return combined_test

    def get_test_cases_name_list(self):
        def extract_test_cases(root_node):
            test_cases = []

            for child in root_node.children:
                if child.type == "test_case_definition":
                    test_case_name = ""
                    documentation = ""

                    # Extract test case name
                    for name_child in child.children:
                        if name_child.type == "name":
                            test_case_name = name_child.text.decode("utf-8").strip()

                    # Extract documentation if it starts with [Documentation]
                    for body_child in child.children:
                        if body_child.type == "body":
                            for setting in body_child.children:
                                if setting.type == "test_case_setting":
                                    setting_text = setting.text.decode("utf-8").strip()
                                    if re.match(r'\[Documentation\]', setting_text):
                                        for argument in setting.children:
                                            if argument.type == "arguments":
                                                documentation = argument.text.decode("utf-8").strip()

                    # Add the test case information to the list
                    test_cases.append({
                        "name": test_case_name,
                        "documentation": documentation
                    })

            return test_cases

        root_node, content = self.get_root_node()
        test_cases_node = self.get_main_section_node(root_node, 'test_cases_section')

        test_cases_list = {
            self.extract_filename_without_extension(): extract_test_cases(test_cases_node)
        }

        return test_cases_list

    def section_parser(self, section_name):
        def extract_definitions(node, section_type, item_type, name_type, body_type=None, extract_func=None, skip_list=None):
            """
            Extracts definitions from a parsed tree-sitter node.

            Args:
                node (Node): The root node or current node to parse.
                section_type (str): The type of the section node to extract from.
                item_type (str): The type of the item node to extract.
                name_type (str): The type of the name node within the item node.
                body_type (str): The type of the body node within the item node (optional).
                extract_func (func): Additional function to extract specific data (optional).
                skip_list (list): List of strings to skip (optional).

            Returns:
                dict: A dictionary of extracted definitions.
            """
            definitions = {}

            if node.type == section_type:
                for child in node.children:
                    if child.type == item_type:
                        name_node = None
                        body_node = None
                        additional_data = {}

                        for item_child in child.children:
                            if item_child.type == name_type:
                                name_node = item_child
                            if body_type and item_child.type == body_type:
                                body_node = item_child
                            if extract_func:
                                additional_data.update(extract_func(item_child, skip_list, content[child.start_byte:child.end_byte].strip()))

                        if name_node or 'name' in additional_data:
                            name = additional_data.pop('name') if 'name' in additional_data else name_node.text.decode('utf-8').strip() 
                            text = content[child.start_byte:child.end_byte].strip()

                            definitions[name] = {
                                'text': text,
                                **additional_data
                            }

            for child in node.children:
                definitions.update(extract_definitions(child, section_type, item_type, name_type, body_type, extract_func, skip_list))

            return definitions

        def extract_settings_additional(item_child, skip_list, text):
            settings_data = {}
            setting_value_node = None

            def extract_setting_value(setting_value):
                match = re.search(r'([^/]+)\.robot$', setting_value)
                return match.group(1) if match else setting_value 

            if item_child.type == 'arguments' and skip_list:
                if all(setting not in text for setting in skip_list):
                    for arg_child in item_child.children:
                        if arg_child.type == 'argument':
                            setting_value_node = arg_child
                            break

                if setting_value_node:
                    setting_value = setting_value_node.text.decode('utf-8').strip()
                    settings_data = {
                        'name': extract_setting_value(setting_value),
                        'value': setting_value
                    }

            return settings_data

        def extract_variable_additional(item_child, _, __):
            variable_data = {}
            variable_value_node = None

            if item_child.type == 'arguments':
                for arg_child in item_child.children:
                    if arg_child.type == 'argument':
                        variable_value_node = arg_child
                        break

            if variable_value_node:
                variable_value = variable_value_node.text.decode('utf-8').strip()
                variable_data = {'value': variable_value}

            return variable_data

        def extract_settings_definitions(node):
            return extract_definitions(
                node,
                section_type='settings_section',
                item_type='setting_statement',
                name_type='arguments',
                extract_func=extract_settings_additional,
                skip_list=['Documentation', 'Force Tags', 'Test Timeout', 'Test Tags']
            )

        def extract_variable_definitions(node):
            return extract_definitions(
                node,
                section_type='variables_section',
                item_type='variable_definition',
                name_type='variable_name',
                extract_func=extract_variable_additional
            )

        root_node, content = self.get_root_node()

        if section_name == "settings":
            settings_definitions = extract_settings_definitions(root_node)
            settings_text = ""

            for setting_header, setting_item in settings_definitions.items():
                # Adding only setting with "value" attr, stands for settings which are not part of 'skip_list'
                if setting_item.get("value"):
                    settings_text+= setting_item.get('text', '') + "\n"

            return settings_text, settings_definitions

        if section_name == "variables":
            variables_definitions = extract_variable_definitions(root_node)
            variables_text = ""

            for variable_header, variable_item in variables_definitions.items():
                # Adding only variable with "value" attr, stands for variables which are not part of 'skip_list'
                if variable_item.get("value"):
                    variables_text+= variable_item.get('text', '') + "\n"

            return variables_text, variables_definitions

            return "", {}

    def get_keywords_name_list(self):
        def extract_keywords(root_node):
            keywords = []
            for child in root_node.children:
                if child.type == "keyword_definition":
                    keyword_name = ""
                    documentation = ""

                    # Extract keyword name
                    for name_child in child.children:
                        if name_child.type == "name":
                            keyword_name = name_child.text.decode("utf-8").strip()

                    # Extract documentation if it starts with [Documentation]
                    for body_child in child.children:
                        if body_child.type == "body":
                            for setting in body_child.children:
                                if setting.type == "keyword_setting":
                                    setting_text = setting.text.decode("utf-8").strip()
                                    if re.match(r'\[Documentation\]', setting_text):
                                        for argument in setting.children:
                                            if argument.type == "arguments":
                                                documentation = argument.text.decode("utf-8").strip()

                    # Add the keyword information to the list
                    keywords.append({
                        "name": keyword_name,
                        "documentation": documentation
                    })

            return keywords

        root_node, content = self.get_root_node()
        keywords_node = self.get_main_section_node(root_node, 'keywords_section')
        if keywords_node:
            return self.extract_filename_without_extension(), extract_keywords(keywords_node)

        return self.extract_filename_without_extension(), []

    def get_libraries_name_list(self):
        def extract_libraries(root_node):
            """
            Extracts libraries from the Robot Framework file settings section.
            Maps 'Library' arguments to 'library_name' and 'library_text'.
            """
            libraries = {}

            # Iterate through children of the root node
            for child in root_node.children:
                if child.type == "setting_statement":
                    library_name = ""
                    library_text = ""

                    # Check if the setting_statement contains arguments
                    child_text = child.text.decode("utf-8").strip() 
                    for arguments_node in child.children:
                        if arguments_node.type == "arguments":
                            # Check if the argumens starts with 'Library'
                            if child_text.startswith("Library"):
                                # Extract the library text (e.g., "String", "OperatingSystem", "OpenShiftLibrary", or file paths)
                                library_text = child_text

                                # Iterate through argument nodes
                                for argument_node in arguments_node.children:
                                    # The actual library name is the part after 'Library'
                                    for text_chunk_node in argument_node.children:
                                        if text_chunk_node.type == "text_chunk":
                                            library_name = text_chunk_node.text.decode("utf-8").strip()

                                # Add library information to the dictionary
                                libraries[library_name] = library_text

            return libraries

        root_node, content = self.get_root_node()
        settings_node = self.get_main_section_node(root_node, 'settings_section')
        if settings_node:
            return extract_libraries(settings_node)

        return {}

    def get_full_internal_calls_list(self, keywords_mapping, libraries_mapping):
        def extract_internal_calls(root_node, settings_mapping, variables_mapping):
            """
            Extracts test cases and keyword definitions, and maps keyword invocations based on the general mapping.
            """

            def map_library(type_mapping):
                """Helper function to map each library under 'calls' section which being used."""
                setting_mapping = {}
                
                # Iterate over the calls
                for call, call_data in type_mapping.items():
                    # Library mapping
                    if type_mapping[call] and 'text' in call_data:
                        setting_mapping.update({f'{call}': call_data})

                return setting_mapping

            def map_variable(variable_list):
                """
                Maps each variable from the variable_list to its corresponding entry in variables_mapping.

                Args:
                    variable_list: List of variable names to be mapped.
                    variables_mapping: Dictionary mapping variable names to their metadata (text and value).

                Returns:
                    A dictionary where each variable is mapped to its 'text' field.
                """
                variable_mapping = {}

                # Iterate over the variables in the list
                for variable in variable_list:
                    # Check if the variable exists in the variables_mapping
                    if variable in variables_mapping and 'text' in variables_mapping[variable]:
                        # Map the variable to its corresponding 'text' value
                        variable_mapping.update({
                            f'{variable}': {
                                'text': variables_mapping[variable]['text']
                            }
                        })

                return variable_mapping

            def internal_variables_mapping(node):
                """
                Recursively extracts all 'variable_name' nodes (can be located under 'statement' nodes)
                in the given tree structure.
                
                Args:
                    node: The root node to start traversal from.
                
                Returns:
                    A list of variable names extracted from 'variable_name' nodes.
                """
                variable_names = []

                # Recursive helper function to traverse the tree
                def traverse_tree(current_node):
                    # If the node is a 'variable_name', extract its text value
                    if current_node.type == "variable_name":
                        variable_name = current_node.text.decode("utf-8").strip()
                        variable_names.append(variable_name)
                    
                    # Continue traversal for child nodes
                    for child in current_node.children:
                        traverse_tree(child)
                
                # Start traversal from the root node
                traverse_tree(node)

                return variable_names

            def map_imports_file_locations(type_mapping):
                """Helper function to map file locations from 'calls' to 'imports_file_locations' using 'settings_mapping'."""
                imports_file_locations = {}
                
                # Iterate over the calls and their file locations
                for call, call_data in type_mapping.items():
                    file_location =  call_data['file_location'][0] if call_data.get("file_location", []) else ""
                    
                    # Check if any setting text in settings_mapping matches the file location
                    for setting_key, setting_value in settings_mapping.items():
                        setting_file_name = setting_value.get('value', '').split('/')[-1]
                        if setting_file_name and (setting_file_name in file_location):
                            # Map the setting path (with ../../) to the actual file location
                            imports_file_locations[setting_value['value']] = file_location

                return imports_file_locations

            def extract_definitions(node, type):
                """Helper function to extract definitions for both test cases and keywords."""
                name = ""
                documentation = ""
                type_mapping = {}
                code = ""

                def type_mapping_insertion(keyword_text):
                    if keyword_text in keywords_mapping:
                        keyword_info = keywords_mapping[keyword_text]
                        type_mapping[keyword_text] = {
                            "file_location": keyword_info["file_names"],
                            "documentation": keyword_info["documentation"]
                        }
                    
                    # Following code snippet maps all the Library internal functions calls 
                    keyword_text = keyword_text.split('.')[0]
                    if keyword_text in libraries_mapping:
                        library_info = libraries_mapping[keyword_text]
                        type_mapping[keyword_text] = {
                            "text": library_info
                        }

                # Extract the name (test case name or keyword name)
                for name_child in node.children:
                    if name_child.type == "name":
                        name = name_child.text.decode("utf-8").strip()

                # Extract documentation if it starts with [Documentation]
                for body_child in node.children:
                    if body_child.type == "body":
                        # code = body_child.text.decode("utf-8").strip()
                        code = node.text.decode("utf-8").strip()
                        for setting in body_child.children:
                            # Use appropriate setting type based on whether it's a test case or keyword
                            setting_type = "test_case_setting" if type == "Test_Case" else "keyword_setting"
                            if setting.type == setting_type:
                                setting_text = setting.text.decode("utf-8").strip()
                                if re.match(r'\[Documentation\]', setting_text):
                                    for argument in setting.children:
                                        if argument.type == "arguments":
                                            documentation = argument.text.decode("utf-8").strip()

                # Look for keyword invocations
                for statement in body_child.children:
                    if statement.type == "statement":
                        for invocation in statement.children:
                            # if invocation.type == "keyword_invocation":
                            keyword_text = ""
                            # Extract the keyword name
                            for keyword_child in invocation.children:
                                if keyword_child.type == "arguments":
                                    for arguments_child in keyword_child.children:
                                        if arguments_child.type == "argument":
                                            keyword_text = arguments_child.text.decode("utf-8").strip()
                                        type_mapping_insertion(keyword_text)

                                if keyword_child.type == "keyword":
                                    keyword_text = keyword_child.text.decode("utf-8").strip()
                                    type_mapping_insertion(keyword_text)

                # Map 'imports_file_locations' for resource mapping from settings
                imports_file_locations = map_imports_file_locations(type_mapping)
                internal_variables_code_mapping = internal_variables_mapping(node)
                library_mapping = map_library(type_mapping)
                variables_mapping = map_variable(internal_variables_code_mapping)

                return {
                    "code": code,
                    "settings": f"{library_mapping}",
                    "variables": f"{variables_mapping}",
                    "name": f"{name}",
                    "documentation": f"{documentation}",
                    # "calls": type_mapping,  # The new keyword mappings per definition
                    "imports_file_locations": f"{imports_file_locations}",  # Mapped resource imports
                    "file_location": f"https://scm.cci.nokia.net/cia/automation-tests-ncs/24/{self.realtive_path}",
                    "element_type": type,  # Either 'Test_Case' or 'Keyword'
                    "project_name": self.project_name
                }

            definitions = []
            test_cases_node = self.get_main_section_node(root_node, 'test_cases_section')
            keywords_node = self.get_main_section_node(root_node, 'keywords_section')

            if test_cases_node:
                for child in test_cases_node.children:
                    if child.type == "test_case_definition":
                        # Test case definition
                        definitions.append(extract_definitions(child, "test_case"))

            if keywords_node:
                for child in keywords_node.children:
                    if child.type == "keyword_definition":
                        # Keyword definition
                        definitions.append(extract_definitions(child, "keyword"))

            return definitions

        root_node, content = self.get_root_node()
        _, settings_mapping  = self.section_parser(section_name="settings")
        _, variables_mapping = self.section_parser(section_name="variables")
        return extract_internal_calls(root_node, settings_mapping, variables_mapping)

        # TODO: OLD VERSION THAT WORKED FOR TEST CASES MAPPING ONLY
        # def extract_test_cases(root_node):
        #     test_cases = []

        #     for child in root_node.children:
        #         if child.type == "test_case_definition":
        #             test_case_name = ""
        #             documentation = ""
        #             keyword_mapping = {}

        #             # Extract test case name
        #             for name_child in child.children:
        #                 if name_child.type == "name":
        #                     test_case_name = name_child.text.decode("utf-8").strip()

        #             # Extract documentation if it starts with [Documentation]
        #             for body_child in child.children:
        #                 if body_child.type == "body":
        #                     test_case_code = body_child.text.decode("utf-8").strip() 
        #                     for setting in body_child.children:
        #                         if setting.type == "test_case_setting":
        #                             setting_text = setting.text.decode("utf-8").strip()
        #                             if re.match(r'\[Documentation\]', setting_text):
        #                                 for argument in setting.children:
        #                                     if argument.type == "arguments":
        #                                         documentation = argument.text.decode("utf-8").strip()

        #             # Look for keyword invocations
        #             for statement in body_child.children:
        #                 if statement.type == "statement":
        #                     for invocation in statement.children:
        #                         if invocation.type == "keyword_invocation":
        #                             keyword_text = ""
        #                             # Extract the keyword name
        #                             for keyword_child in invocation.children:
        #                                 if keyword_child.type == "keyword":
        #                                     keyword_text = keyword_child.text.decode("utf-8").strip()

        #                             # Check if the keyword exists in the general mapping
        #                             if keyword_text in keywords_mapping:
        #                                 keyword_info = keywords_mapping[keyword_text]
        #                                 keyword_mapping[keyword_text] = {
        #                                     "file_location": keyword_info["file_names"],
        #                                     "documentation": keyword_info["documentation"]
        #                                 }

        #             # Add the test case information to the list
        #             test_cases.append({
        #                 "code": test_case_code,
        #                 "dependencies": {
        #                     "settings": "",
        #                     "varaibles": "",
        #                 },
        #                 "additional_data": {
        #                     "name": test_case_name,
        #                     "documentation": documentation,
        #                 },
        #                 "calls": keyword_mapping,  # The new keyword mappings per test case
        #                 "file_location": self.realtive_path,
        #                 "type": "Test_Case",
        #             })

        #     return test_cases

        # test_cases_node = self.get_main_section_node(root_node, 'test_cases_section')
        # if test_cases_node:
            # return extract_internal_calls(root_node)

        # return []

    def entire_file_parsing(self, robot_file_names_mapping):
        def map_imports_file_locations():
                """Helper function to map imported files located in settings section to 'imports_file_locations' using 'settings_mapping'."""
                imports_file_locations = {}
                _, settings_mapping  = self.section_parser(section_name="settings")
                    
                # Check if any setting text in settings_mapping matches the file location
                for setting_key, setting_value in settings_mapping.items():
                    setting_file_name = setting_value.get('value', '').split('/')[-1]
                    if setting_file_name and (setting_file_name in robot_file_names_mapping):
                        # Map the setting path (with ../../) to the actual file location
                        imports_file_locations[setting_value['value']] = robot_file_names_mapping[setting_file_name]

                return imports_file_locations

        def extract_entire_code(node, content, file_type):
            """Helper function to extract entire robot code."""
            return {
                "code": content,
                "name": f"{self.realtive_path}",
                "imports_file_locations": f"{map_imports_file_locations()}",  # Mapped resource imports
                "file_location": f"https://scm.cci.nokia.net/cia/automation-tests-ncs/24/{self.realtive_path}",
                "element_type": file_type,  # Either 'Test' or 'Resource'
                "project_name": self.project_name
            }

        root_node, content = self.get_root_node()
        file_type = "test" if self.get_main_section_node(root_node, 'test_cases_section') else "resource"
        return extract_entire_code(root_node, content, file_type)