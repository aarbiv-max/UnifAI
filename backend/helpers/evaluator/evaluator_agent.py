from typing import Dict
from .analyzers.ts_analyzer.cypress_analyzer import CypressCodeAnalyzer
from .analyzers.ts_analyzer.ts_analyzer import TSCodeAnalyzer
from .analyzers.go_analyzer import GoCodeAnalyzer
from .analyzers.ts_analyzer.integrated_ts_analyzer import IntegratedTSAnalyzer

TYPE_SCRIPT = 'typescript'
GO = 'go'

class EvaluatorAgent:
    def __init__(self, repo_path: str, framework: str, gitRepoLink: str):
        """Initialize the evaluator agent based on the selected framework."""
        # Select the appropriate analyzer based on the framework
        if framework.lower() == TYPE_SCRIPT:
            self.analyzer = IntegratedTSAnalyzer(gitRepoLink)
        elif framework.lower() == GO:
            self.analyzer = GoCodeAnalyzer()
        else:
            raise ValueError(f"Unsupported framework: {framework}")

        # Analyze the repository based on the chosen framework
        self.analyzer.analyze_repository(repo_path)

    def evaluate_generated_code(self, code: str) -> Dict:
        """Evaluate generated code for project-specific symbol existence and compatibility"""
        if code.strip().startswith("```"):
            code = "\n".join(line for line in code.splitlines() if not line.strip().startswith("```"))

        verification_results = self.analyzer.verify_code_snippet(code=code)
        # Calculate overall validity
        all_valid = all(
            all(result['exists'] for result in category)
            for category in verification_results.values()
        )
        
        # Calculate accuracy percentage
        total_elements = 0
        existing_elements = 0
        
        for category in verification_results.values():
            total_elements += len(category)
            existing_elements += sum(1 for result in category if result['exists'])
        
        accuracy_percentage = (existing_elements / total_elements * 100) if total_elements > 0 else 0
        
        return {
            'is_valid': all_valid,
            'verification_details': verification_results,
            'summary': self._generate_summary(verification_results),
            'percentages_accuracy': round(accuracy_percentage, 2)
        }
        
    def _generate_summary(self, verification_results: Dict) -> str:
        """Generate a human-readable summary of verification results"""
        issues = []
        has_compile_errors = False

        for category, results in verification_results.items():
            key = "name" if category != "cyCommands" else "command"
            
            missing = [r.get(key, 'unknown') for r in results if not r['exists']]
            if missing:
                issues.append(f"Missing {category}: {', '.join(missing)}")
            
            # Detect compile-time issues even in existing items
            for r in results:
                if r.get("exists") and (
                    (isinstance(r.get("issues"), list) and r["issues"]) or
                    any(u.get("issues") for u in r.get("usages", []) if isinstance(u.get("issues"), list))
                ):
                    has_compile_errors = True
                    break  # no need to keep checking once we detect one

        if not issues and not has_compile_errors:
            return "All project-specific symbols verified successfully"
        
        summary_lines = ["Verification failed:"]
        summary_lines.extend(issues)
        if has_compile_errors:
            summary_lines.append("Some existing symbols contain issues that would cause compile-time errors.")

        return "\n".join(summary_lines)

