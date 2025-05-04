from .base_analyzer import BaseAnalyzer
from typing import Dict, List, Any, Tuple

GITHUB_BASE_URL = "https://github.com/konveyor/tackle-ui-tests/blob/main/"

class CypressCodeAnalyzer(BaseAnalyzer):
    def __init__(self):
        super().__init__()
        self.symbol_database = {
            'testBlocks': [],
            'cyCommands': []
        }
        self.detected_cy_wrappers = {}

    def analyze_repository(self, repo_path: str):
        files_data = self.load_repo(repo_path)
        analysis = self.analyze_code(files_data)

        for rel_path, file_symbols in analysis.items():
            for block in file_symbols.get('testBlocks', []):
                block['file'] = rel_path
                self.symbol_database['testBlocks'].append(block)

            for cy_cmd in file_symbols.get('cyCommands', []):
                cy_cmd['file'] = rel_path
                self.symbol_database['cyCommands'].append(cy_cmd)

            for fn in file_symbols.get('functions', []):
                body = fn.get('body', '')
                for cy_cmd in ['click', 'type', 'get', 'visit', 'login', 'intercept', 'select']:
                    if f"cy.{cy_cmd}(" in body:
                        self.detected_cy_wrappers.setdefault(cy_cmd, set()).add(fn['name'])

    def match_cy_command(self, cmd: Dict[str, Any], repo_commands: List[Dict[str, Any]]) -> Tuple[bool, Dict[str, Any], str]:
        for repo_cmd in repo_commands:
            if cmd['command'] == repo_cmd['command']:
                return True, repo_cmd, 'direct'
        for canonical, wrappers in self.detected_cy_wrappers.items():
            if cmd['command'] in wrappers:
                for repo_cmd in repo_commands:
                    if repo_cmd['command'] == canonical or repo_cmd['command'] in wrappers:
                        return True, repo_cmd, 'wrapper'
        return False, None, 'none'

    def verify_code_snippet(self, code: str):
        analysis = self.analyze_code({"snippet.ts": code})
        snippet_data = analysis.get("snippet.ts", {})

        verification = {
            'testBlocks': [],
            'cyCommands': []
        }

        repo_test_blocks = {(tb['type'], tb['name']): tb for tb in self.symbol_database['testBlocks']}
        for tb in snippet_data.get('testBlocks', []):
            key = (tb['type'], tb['name'])
            match = repo_test_blocks.get(key)
            issues = []
            if match and match.get('body', '').strip() != tb.get('body', '').strip():
                issues.append("Test block body differs")
            verification['testBlocks'].append({
                'type': tb['type'], 'name': tb['name'],
                'exists': match is not None,
                'file': match['file'] if match else None,
                'url': GITHUB_BASE_URL + match['file'] if match else None,
                'issues': issues
            })

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
