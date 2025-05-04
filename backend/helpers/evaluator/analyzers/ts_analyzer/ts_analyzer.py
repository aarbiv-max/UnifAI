import re
import json
from typing import Dict, List, Any, Tuple, Optional
from .base_analyzer import BaseAnalyzer

# --- Utilities ---
def normalize_path(p: str) -> str:
    return p.replace("\\", "/").replace("./", "").replace("../", "").replace("src/", "").replace(".ts", "")

def clean_type_name(type_name: str) -> str:
    return re.sub(r"<.*?>", "", type_name).strip()

def are_signatures_equivalent(fn1: Dict, fn2: Dict) -> Tuple[bool, List[str]]:
    return True, []  # We moved detailed comparison to compare_parameters()

def infer_type_from_literal(arg: str) -> str:
    arg = arg.strip()
    if arg.isdigit():
        return "number"
    if arg in ("true", "false"):
        return "boolean"
    if arg.startswith('"') or arg.startswith("'"):
        return "string"
    return "unknown"

def compare_parameters(snippet_fn: Dict, repo_fn: Dict) -> List[str]:
    issues = []
    snippet_args = snippet_fn.get('params', [])
    repo_params = repo_fn.get('params', [])
    required_repo_params = [p for p in repo_params if not p.endswith('?')]

    if len(snippet_args) < len(required_repo_params):
        issues.append(f"Missing required parameter(s). Expected at least {len(required_repo_params)}, got {len(snippet_args)}.")
    elif len(snippet_args) > len(repo_params):
        issues.append(f"Too many parameters. Expected at most {len(repo_params)}, got {len(snippet_args)}.")

    for i, repo_param in enumerate(repo_params):
        repo_param_clean = repo_param.replace('?', '')
        if i < len(snippet_args):
            inferred = infer_type_from_literal(snippet_args[i])
            if inferred != repo_param_clean:
                issues.append(f"Parameter {i+1} type mismatch: expected '{repo_param_clean}', got '{inferred}'.")


    return issues

# --- TS Evaluator ---
class TSCodeAnalyzer:
    def __init__(self):
        self.repo = {}
        self.snippet = {}
        self.declarations = []

    def load(self, repo_path: str, snippet_code: str):
        base = BaseAnalyzer()
        repo_result = base.load_repo(repo_path)
        snippet_result = base.analyze_snippet(snippet_code)
        self.repo = repo_result
        self.snippet = snippet_result.get("/snippet", {})
        self._infer_declarations(snippet_code)


    def _infer_declarations(self, snippet_code: str):
        self.declarations = []
        for line in snippet_code.splitlines():
            line = line.strip()
            if line.startswith(("const ", "let ", "var ")):
                parts = line.replace(";", "").split("=")
                if len(parts) == 2:
                    var_part, expr_part = parts
                    var_name = var_part.split(":")[0].replace("const", "").replace("let", "").replace("var", "").strip()
                    if "new " in expr_part:
                        expr_clean = expr_part.replace("new", "").strip()
                        raw_type_name = expr_clean.split("(")[0].strip()
                        type_name = clean_type_name(raw_type_name)
                        kind, path = self._resolve_type(type_name)
                        self.declarations.append({"name": var_name, "type": type_name, "raw_type": raw_type_name, "kind": kind, "path": path})
                    elif ":" in var_part:
                        _, type_annotation = var_part.split(":")
                        raw_type_name = type_annotation.strip()
                        type_name = clean_type_name(raw_type_name)
                        kind, path = self._resolve_type(type_name)
                        self.declarations.append({"name": var_name, "type": type_name, "raw_type": raw_type_name, "kind": kind, "path": path})

            elif line.startswith("class "):
                class_name = line.split()[1].split("{")[0].split("(")[0].strip()
                self.declarations.append({"name": class_name, "type": class_name, "kind": "class", "path": "/snippet"})

            elif line.startswith("interface "):
                interface_name = line.split()[1].split("{")[0].strip()
                self.declarations.append({"name": interface_name, "type": interface_name, "kind": "interface", "path": "/snippet"})

    def _resolve_type(self, type_name: str) -> Tuple[str, Optional[str]]:
        for path, file in self.repo.items():
            if type_name in file.get("classes", {}):
                return "class", path
            if type_name in file.get("interfaces", {}):
                return "interface", path
        return "unknown", None

    def get_repo_file_by_path(self, path: str) -> Optional[Dict[str, Any]]:
        if path and path in self.repo:
            return self.repo[path]
        return None

    def evaluate(self) -> Dict[str, List[Dict[str, Any]]]:
        result = {key: [] for key in ['functions', 'methods', 'classes', 'interfaces', 'imports', 'memberAccesses']}

        # --- Functions ---
        # --- Functions ---
        for fn in self.snippet.get('functions', []):
            exists = False
            path = None
            issues = []
            usages = []

            for decl in self.declarations:
                if decl['name'] == fn['name'] and decl['kind'] == "function":
                    exists = True
                    path = decl['path']
                    break

            repo_fn = None
            if exists and path:
                repo_file = self.get_repo_file_by_path(path)
                if repo_file:
                    repo_fn = next((f for f in repo_file.get('functions', []) if f['name'] == fn['name']), None)
                    if repo_fn:
                        issues.extend(compare_parameters(fn, repo_fn))

            # Record usages
            for call in self.snippet.get('calls', []):
                if call.get('type') == "function" and call.get('name') == fn['name']:
                    usage_issues = compare_parameters({'params': call.get('args', [])}, repo_fn or fn)
                    usages.append({"args": call.get('args', []), "issues": usage_issues})

            result['functions'].append({
                "name": fn['name'],
                "exists": exists,
                "path": path if exists else None,
                "issues": issues,
                "usages": usages
            })

        # --- Methods ---
        for m in self.snippet.get('methods', []):
            exists = False
            issues = []
            path = None
            usages = []
            repo_method = None

            for decl in self.declarations:
                if decl['name'] == m.get('class') and decl['kind'] == "class":
                    file = self.get_repo_file_by_path(decl['path'])
                    if file:
                        repo_methods = file.get('methods', [])
                        repo_method = next((meth for meth in repo_methods if meth['name'] == m['name']), None)
                        if repo_method:
                            exists = True
                            path = decl['path']
                            issues.extend(compare_parameters(m, repo_method))
                            break

            # Record usages
            for call in self.snippet.get('calls', []):
                if call.get('type') == "method" and call.get('name') == m['name'] and call.get('objectType') == m.get('class'):
                    usage_issues = compare_parameters({'params': call.get('args', [])}, repo_method or m)
                    usages.append({"args": call.get('args', []), "issues": usage_issues})

            result['methods'].append({
                "name": m['name'],
                "class": m.get('class'),
                "exists": exists,
                "path": path if exists else None,
                "issues": issues,
                "usages": usages
            })

        # --- Classes ---
        for cls_name in self.snippet.get('classes', {}):
            found_decl = next((d for d in self.declarations if d['name'] == cls_name and d['kind'] == "class"), None)
            exists = found_decl is not None
            result['classes'].append({"name": cls_name, "exists": exists, "path": found_decl['path'] if exists else None})

        # --- Interfaces ---
        for intf_name in self.snippet.get('interfaces', {}):
            found_decl = next((d for d in self.declarations if d['name'] == intf_name and d['kind'] == "interface"), None)
            exists = found_decl is not None
            result['interfaces'].append({"name": intf_name, "exists": exists, "path": found_decl['path'] if exists else None})

        # --- Imports ---
        # --- Imports ---
        for imp in self.snippet.get('imports', []):
            imported_file_path = normalize_path(imp['path'])
            file_data = self.get_repo_file_by_path(imported_file_path)
            match_found = False
            if file_data:
                match_found = (
                    imp['name'] in file_data.get('classes', {}) or
                    imp['name'] in file_data.get('interfaces', {}) or
                    any(func['name'] == imp['name'] for func in file_data.get('functions', []))
                )
            result['imports'].append({
                "name": imp['name'],
                "path": imp['path'],
                "exists": match_found,
                "resolvedPath": imported_file_path if match_found else None
            })

            # ✅ If this is an imported function
            for func in file_data.get("functions", []):
                if func["name"] == imp["name"]:
                    usages = []
                    for call in self.snippet.get("calls", []):
                        if call.get("type") == "function" and call.get("name") == func["name"]:
                            issues = compare_parameters({"params": call.get("args", [])}, func)
                            usages.append({"args": call.get("args", []), "issues": issues})

                    result["functions"].append({
                        "name": func["name"],
                        "exists": True,
                        "path": imported_file_path,
                        "issues": [],
                        "usages": usages
                    })

            # ✅ If this is an imported class — include its methods
            class_methods = [m for m in file_data.get("methods", []) if m.get("class") == imp["name"]]
            for method in class_methods:
                usages = []
                for call in self.snippet.get("calls", []):
                    if (
                        call.get("type") == "method" and
                        call.get("name") == method["name"] and
                        call.get("objectType") == imp["name"]
                    ):
                        issues = compare_parameters({"params": call.get("args", [])}, method)
                        usages.append({"args": call.get("args", []), "issues": issues})

                result["methods"].append({
                    "name": method["name"],
                    "class": imp["name"],
                    "exists": True,
                    "path": imported_file_path,
                    "issues": [],
                    "usages": usages
                })


        # --- Member Accesses ---
        for access in self.snippet.get('memberAccesses', []):
            obj = access['object']
            member = access['member']
            issues = []
            exists = False
            path = None

            decl = next((d for d in self.declarations if d['name'] == obj), None)
            if decl:
                file = self.get_repo_file_by_path(decl['path'])
                if file:
                    if decl['kind'] == "class":
                        repo_methods = file.get('methods', [])
                        if any(m['name'] == member for m in repo_methods):
                            exists = True
                            path = decl['path']
                        else:
                            issues.append(f"Method '{member}' not found in class '{decl['type']}'")
                    elif decl['kind'] == "interface":
                        props = file.get('interfaces', {}).get(decl['type'], {})
                        if member in props:
                            exists = True
                            path = decl['path']
                        else:
                            issues.append(f"Property '{member}' not found in interface '{decl['type']}'")
            else:
                issues.append(f"Variable '{obj}' is not declared or imported.")

            result['memberAccesses'].append({
                "object": obj,
                "member": member,
                "exists": exists,
                "path": path if exists else None,
                "issues": issues
            })

        return result

