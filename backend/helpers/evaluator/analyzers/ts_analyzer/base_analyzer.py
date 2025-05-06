import os
import json
import subprocess
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
TS_NODE_SCRIPT_PATH = os.path.join(BASE_DIR, "node_tools", "ts_analyze.js")
CY_NODE_SCRIPT_PATH = os.path.join(BASE_DIR, "node_tools", "cy_analyze.js")


class BaseAnalyzer:
    def __init__(self, is_cypress: bool = False):
        self.symbol_database = {"testBlocks": [], "cyCommands": []}
        self.node_script_path = (
            CY_NODE_SCRIPT_PATH if is_cypress else TS_NODE_SCRIPT_PATH
        )

    def run_node_analyzer(self, files: Dict[str, str]) -> Dict[str, Any]:
        payload = {"files": files}
        try:
            result = subprocess.run(
                ["node", self.node_script_path],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                check=True,
            )
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            print("JS script error:", e.stderr)
            raise

    def _read_ts_file(self, full_path: str) -> str:
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()

    def load_repo(self, repo_path: str) -> Dict[str, Any]:
        ts_files = []

        for root, _, files in os.walk(repo_path):
            for file in files:
                if file.endswith(".ts"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, repo_path)
                    ts_files.append((rel_path, full_path))
        with ThreadPoolExecutor() as executor:
            contents = list(
                executor.map(
                    lambda pair: (pair[0], self._read_ts_file(pair[1])), ts_files
                )
            )
        files_data = dict(contents)
        return self.run_node_analyzer(files_data)

    def analyze_snippet(self, snippet_code: str) -> Dict[str, Any]:
        return self.run_node_analyzer({"snippet.ts": snippet_code})

    def analyze_snippet_batch(self, snippets: List[str]) -> List[Dict[str, Any]]:
        def analyze_single(snippet_code: str) -> Dict[str, Any]:
            return self.analyze_snippet(snippet_code)

        with ThreadPoolExecutor() as executor:
            return list(executor.map(analyze_single, snippets))
