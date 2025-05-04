import os
import json
import subprocess
from typing import Dict, List, Any

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
NODE_SCRIPT_PATH = os.path.join(BASE_DIR, "node_tools", "ts_analyze.js")
GITHUB_BASE_URL = "https://github.com/konveyor/tackle-ui-tests/blob/main/"

class BaseAnalyzer:
    def __init__(self):
        self.symbol_database = {}

    def run_node_analyzer(self, files: Dict[str, str]) -> Dict[str, Any]:
        payload = {"files": files}
        try:
            result = subprocess.run(
                ["node", NODE_SCRIPT_PATH],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                check=True
            )
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            print("JS script error:", e.stderr)
            raise

    def load_repo(self, repo_path: str):
        files_data = {}
        for root, _, files in os.walk(repo_path):
            for file in files:
                if file.endswith('.ts'):
                    full_path = os.path.join(root, file)
                    with open(full_path, 'r', encoding='utf-8') as f:
                        code = f.read()
                    rel_path = os.path.relpath(full_path, repo_path)
                    files_data[rel_path] = code
        return self.run_node_analyzer(files_data)

    def analyze_snippet(self, snippet_code: str):
        return self.run_node_analyzer({"snippet.ts": snippet_code})



