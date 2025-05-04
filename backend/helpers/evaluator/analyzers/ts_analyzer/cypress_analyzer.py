import json
import re
from .base_analyzer import BaseAnalyzer
from typing import Dict, List, Any, Tuple

GITHUB_BASE_URL = "https://github.com/konveyor/tackle-ui-tests/blob/main/"
class CypressCodeAnalyzer(BaseAnalyzer):
    def __init__(self):
        super().__init__(is_cypress=True)
        self.symbol_database = {
            'testBlocks': [],
            'cyCommands': [],
            'utilsFunctions': []  # Track functions from the utils directory
        }
        self.detected_cy_wrappers = {}

    def analyze_repository(self, repo_path: str):
        analysis = self.load_repo(repo_path)

        for rel_path, file_symbols in analysis.items():
            # Detect test blocks
            for block in file_symbols.get('testBlocks', []):
                block['file'] = rel_path
                self.symbol_database['testBlocks'].append(block)

            # Detect cyCommands and custom commands
            for cy_cmd in file_symbols.get('cyCommands', []):
                cy_cmd['file'] = rel_path
                self.symbol_database['cyCommands'].append(cy_cmd)

            # Detect functions wrapping Cypress commands
            for fn in file_symbols.get('functions', []):
                body = fn.get('body', '')
                for cy_cmd in ['click', 'type', 'get', 'visit', 'login', 'intercept', 'select']:
                    if f"cy.{cy_cmd}(" in body:
                        self.detected_cy_wrappers.setdefault(cy_cmd, set()).add(fn['name'])

                # Detect custom commands defined with Cypress.Commands.add
                if re.search(r"Cypress\.Commands\.add\('([^']+)',", body):
                    custom_command_matches = re.findall(r"Cypress\.Commands\.add\('([^']+)',", body)
                    for custom_command in custom_command_matches:
                        self.symbol_database['cyCommands'].append({
                            'command': custom_command,
                            'file': rel_path
                        })

                # Detect utility functions in cypress/utils/
                if 'utils/' in rel_path:
                    self.symbol_database['utilsFunctions'].append({
                        'function': fn['name'],
                        'file': rel_path
                    })

    def match_cy_command(self, cmd: Dict[str, Any], repo_commands: List[Dict[str, Any]]) -> Tuple[bool, Dict[str, Any], str]:
        # Direct match for built-in Cypress commands
        for repo_cmd in repo_commands:
            if cmd['command'] == repo_cmd['command']:
                return True, repo_cmd, 'direct'

        # Check for matches to custom Cypress commands
        for repo_cmd in repo_commands:
            if cmd['command'] == repo_cmd['command']:
                return True, repo_cmd, 'exact'  # This matches the custom command defined in Cypress.Commands.add

        # Check if the command is a wrapped command in utils (or other wrappers)
        for canonical, wrappers in self.detected_cy_wrappers.items():
            if cmd['command'] in wrappers:
                for repo_cmd in repo_commands:
                    if repo_cmd['command'] == canonical or repo_cmd['command'] in wrappers:
                        return True, repo_cmd, 'wrapper'

        return False, None, 'none'

    def verify_code_snippet(self, code: str):
        analysis = self.run_node_analyzer({"snippet.ts": code})
        snippet_data = analysis.get("/snippet.ts", {})

        verification = {
            'testBlocks': [],
            'cyCommands': []
        }

        # Test block verification
        repo_test_blocks = {(tb['type'], tb['name']): tb for tb in self.symbol_database['testBlocks']}
        for tb in snippet_data.get('testBlocks', []):
            key = (tb['type'], tb['name'])
            match = repo_test_blocks.get(key)
            issues = []
            if match:
                if match.get('body', '').strip() != tb.get('body', '').strip():
                    issues.append("Test block body differs")
            verification['testBlocks'].append({
                'type': tb['type'], 'name': tb['name'],
                'exists': match is not None,
                'file': match['file'] if match else None,
                'url': GITHUB_BASE_URL + match['file'] if match else None,
                'issues': issues
            })

        # Cypress command verification
        for cmd in snippet_data.get('cyCommands', []):
            matched, match, match_level = self.match_cy_command(cmd, self.symbol_database['cyCommands'])
            verification['cyCommands'].append({
                'command': cmd['command'],
                'args': cmd['args'],
                'exists': matched,
                'file': match['file'] if matched and match.get('file') else None,
                'url': GITHUB_BASE_URL + match['file'] if matched and match.get('file') else None,
                'matchLevel': match_level
            })

        return verification
