from typing import Dict
from .analyzers.ts_analyzer.cypress_analyzer import CypressCodeAnalyzer
from .analyzers.ts_analyzer.ts_analyzer import TSCodeAnalyzer
from .analyzers.go_analyzer import GoCodeAnalyzer


class EvaluatorAgent:
    def __init__(self, repo_path: str, framework: str):
        """Initialize the evaluator agent based on the selected framework."""
        # Select the appropriate analyzer based on the framework
        if framework.lower() == 'cypress':
            self.analyzer = CypressCodeAnalyzer()
        elif framework.lower() == 'typescript':
            self.analyzer = TSCodeAnalyzer()
        elif framework.lower() == 'go':
            self.analyzer = GoCodeAnalyzer()
        else:
            raise ValueError(f"Unsupported framework: {framework}")

        # Analyze the repository based on the chosen framework
        self.analyzer.analyze_repository(repo_path)

    def evaluate_generated_code(self, code: str) -> Dict:
        """Evaluate generated code for project-specific symbol existence and compatibility"""
        if code.strip().startswith("```"):
            code = "\n".join(line for line in code.splitlines() if not line.strip().startswith("```"))

        verification_results = self.analyzer.verify_code_snippet(code)
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
        
        for category, results in verification_results.items():
            key = "name" if category != "cyCommands" else "command"
            
            missing = [r.get(key, 'unknown') for r in results if not r['exists']]
            if missing:
                issues.append(f"Missing {category}: {', '.join(missing)}")
                
        if not issues:
            return "All project-specific symbols verified successfully"
        return "Verification failed:\n" + "\n".join(issues)
