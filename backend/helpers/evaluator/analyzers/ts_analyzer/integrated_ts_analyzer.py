from typing import Dict
from .cypress_analyzer import CypressCodeAnalyzer
from .ts_analyzer import TSCodeAnalyzer
from .base_analyzer import BaseAnalyzer


class IntegratedTSAnalyzer(BaseAnalyzer):
    def __init__(self, gitRepoLink):
        self.ts_analyzer = TSCodeAnalyzer(gitRepoLink)
        self.cy_analyzer = CypressCodeAnalyzer(gitRepoLink)
        self.symbol_database = {}  # Optional, if you want a shared one

    def analyze_repository(self, repo_path: str):
        self.ts_analyzer.analyze_repository(repo_path)
        print("here")
        self.cy_analyzer.analyze_repository(repo_path)
        # Optionally merge symbol databases here

    def verify_code_snippet(self, code: str) -> Dict:
        print("here")
        ts_result = self.ts_analyzer.verify_code_snippet(code)
        print(ts_result)
        cy_result = self.cy_analyzer.verify_code_snippet(code)

        # Merge the results intelligently
        return {
            "functions": ts_result.get("functions", []),
            "methods": ts_result.get("methods", []),
            "classes": ts_result.get("classes", []),
            "interfaces": ts_result.get("interfaces", []),
            "imports": ts_result.get("imports", []),
            "memberAccesses": ts_result.get("memberAccesses", []),
            "testBlocks": cy_result.get("testBlocks", []),
            "cyCommands": cy_result.get("cyCommands", [])
        }
