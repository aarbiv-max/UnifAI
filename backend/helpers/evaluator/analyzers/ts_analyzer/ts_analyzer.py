import os
import re
from typing import Dict, List, Any, Tuple, Optional
from .base_analyzer import BaseAnalyzer


def normalize_path(p: str) -> str:
    # Replace backslashes (Windows) with forward slashes

    p = p.replace("\\", "/").strip()
    # Remove file extension if present

    if p.endswith(".ts") or p.endswith(".js"):
        p = p.rsplit(".", 1)[0]
    # Normalize the path (collapse ../ and ./)

    norm = os.path.normpath(p).replace("\\", "/")
    # Remove all leading ../ or ./ segments

    parts = norm.split("/")
    while parts and (parts[0] == ".." or parts[0] == "."):
        parts.pop(0)
    return "/".join(parts)


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

    snippet_args = snippet_fn.get("params", [])
    repo_params = repo_fn.get("params", [])

    def param_info(p):
        if isinstance(p, str):
            return {"type": p, "optional": False}
        return p

    repo_param_objs = [param_info(p) for p in repo_params]

    # ✅ Only count *non-optional* params as required

    required_count = len([p for p in repo_param_objs if not p.get("optional", False)])

    # --- Check argument count ---

    if len(snippet_args) < required_count:
        issues.append(
            f"Missing required parameter(s). Expected at least {required_count}, got {len(snippet_args)}."
        )
    elif len(snippet_args) > len(repo_param_objs):
        issues.append(
            f"Too many parameters. Expected at most {len(repo_param_objs)}, got {len(snippet_args)}."
        )
    # --- Type checks for provided arguments ---

    for i, arg in enumerate(snippet_args):
        if i >= len(repo_param_objs):
            break  # skip overflow
        expected_type = repo_param_objs[i]["type"]
        if isinstance(arg, dict):
            inferred = arg.get("inferredType", "unknown")
        else:
            inferred = infer_type_from_literal(arg)
        if not is_type_assignable(inferred, expected_type):
            issues.append(
                f"Parameter {i+1} type mismatch: expected '{expected_type}', got '{inferred}'."
            )
    return issues


def is_type_assignable(snippet_type: str, expected_type: str) -> bool:
    # Allow "any" to match anything

    if expected_type == "any" or snippet_type == "any":
        return True
    # Optional handling: remove `?` for comparison

    base_snippet_type = snippet_type.replace("?", "").strip()
    base_expected_type = expected_type.replace("?", "").strip()

    # Simple match or literal match

    if base_snippet_type == base_expected_type:
        return True
    # Structural type match for objects

    if base_expected_type.startswith("{") and base_snippet_type.startswith("{"):
        # extract prop keys

        def extract_keys(type_str):
            return set(re.findall(r"\b\w+\b(?=:)", type_str))

        snippet_keys = extract_keys(base_snippet_type)
        expected_keys = extract_keys(base_expected_type)

        # Subset is allowed

        return snippet_keys.issubset(expected_keys)
    return False


# --- TS Evaluator ---


class TSCodeAnalyzer:
    def __init__(self, gitRepoLink):
        self.base = BaseAnalyzer(is_cypress=False)
        self.repo = {}
        self.snippet = {}
        self.declarations = []
        self.gitRepoLink = gitRepoLink

    def analyze_repository(self, repo_path: str):
        self.repo_path = repo_path

    def verify_code_snippet(self, snippet_code: str) -> Dict:
        self.load(self.repo_path, snippet_code)
        return self.evaluate()

    def load(self, repo_path: str, snippet_code: str):
        base = BaseAnalyzer()
        repo_result = base.load_repo(repo_path)
        snippet_result = base.analyze_snippet(snippet_code)
        self.repo = repo_result
        self.snippet = snippet_result.get("/snippet", {})
        self._infer_declarations(snippet_code)

    def _infer_declarations(self, snippet_code: str):
        self.declarations = []

        # 1. Add declared vars with types

        for decl in self.snippet.get("declarations", []):
            name = decl.get("name")
            raw_type = decl.get("type", "any")
            type_name = clean_type_name(raw_type)
            kind, path = self._resolve_type(type_name)
            self.declarations.append(
                {
                    "name":     name,
                    "type":     type_name,
                    "raw_type": raw_type,
                    "kind":     kind,
                    "path":     path if path else "local",
                }
            )
        # 2. Add 'assignedTo' variables from 'new ClassName(...)' calls

        for call in self.snippet.get("calls", []):
            if call.get("type") == "function" and call.get("name", "").startswith(
                "new "
            ):
                class_name = call["name"].replace("new ", "").strip()
                assigned_to = call.get("assignedTo")
                if assigned_to:
                    kind, path = self._resolve_type(class_name)
                    self.declarations.append(
                        {
                            "name": assigned_to,
                            "type": class_name,
                            "kind": kind,
                            "path": path if path else "local",
                        }
                    )
        # 3. Infer enum-like objects from member access

        for call in self.snippet.get("calls", []):
            if call.get("type") == "method":
                obj = call.get("object")
                if (
                    obj
                    and "." not in obj
                    and not any(d["name"] == obj for d in self.declarations)
                ):
                    self.declarations.append(
                        {"name": obj, "type": obj, "kind": "enum", "path": "local"}
                    )
        # 4. Include local functions/classes/interfaces

        for fn in self.snippet.get("functions", []):
            self.declarations.append(
                {"name": fn["name"], "kind": "function", "path": "local"}
            )
        for cls_name in self.snippet.get("classes", {}):
            self.declarations.append(
                {"name": cls_name, "kind": "class", "path": "local"}
            )
        for intf_name in self.snippet.get("interfaces", {}):
            self.declarations.append(
                {"name": intf_name, "kind": "interface", "path": "local"}
            )

    def _resolve_type(self, type_name: str) -> Tuple[str, Optional[str]]:
        for path, file in self.repo.items():
            if type_name in file.get("classes", {}):
                return "class", path
            if type_name in file.get("interfaces", {}):
                return "interface", path
        return "unknown", None

    def get_repo_file_by_path(self, path: str) -> Optional[Dict[str, Any]]:
        path = "/" + path
        if not path:
            return None
        # Try direct match first

        if path in self.repo:
            return self.repo[path]
        # Fallback: suffix match

        for repo_path, data in self.repo.items():
            if (
                repo_path.endswith(path)
                or repo_path.endswith(path + ".ts")
                or repo_path.endswith(path + ".js")
            ):
                return data
        return None

    def evaluate(self) -> Dict[str, List[Dict[str, Any]]]:
        result = {
            key: []
            for key in [
                "functions",
                "methods",
                "classes",
                "interfaces",
                "imports",
                "memberAccesses",
            ]
        }

        # --- Functions ---

        for fn in self.snippet.get("functions", []):

            exists = False
            path = None
            issues = []
            usages = []

            for decl in self.declarations:
                if decl["name"] == fn["name"] and decl["kind"] == "function":
                    exists = True
                    path = decl["path"]
                    break
            repo_fn = None
            if exists and path != "local":
                repo_file = self.get_repo_file_by_path(path)
                if repo_file:
                    repo_fn = next(
                        (
                            f
                            for f in repo_file.get("functions", [])
                            if f["name"] == fn["name"]
                        ),
                        None,
                    )
                    if repo_fn:
                        issues.extend(compare_parameters(fn, repo_fn))
            # Record usages

            for call in self.snippet.get("calls", []):
                if call.get("type") == "function" and call.get("name") == fn["name"]:
                    usage_issues = compare_parameters(
                        {"params": call.get("args", [])}, repo_fn or fn
                    )
                    usages.append(
                        {"args": call.get("args", []), "issues": usage_issues}
                    )
            result["functions"].append(
                {
                    "name":   fn["name"],
                    "exists": exists,
                    "path":   path if exists else None,
                    "issues": issues,
                    "usages": usages,
                }
            )
        # --- Methods ---

        for m in self.snippet.get("methods", []):
            exists = False
            issues = []
            path = None
            usages = []
            repo_method = None

            for decl in self.declarations:
                if decl["name"] == m.get("class") and decl["kind"] == "class":
                    if decl["path"] != "local":
                        file = self.get_repo_file_by_path(decl["path"])
                        if file:
                            repo_methods = file.get("methods", [])
                            repo_method = next(
                                (
                                    meth
                                    for meth in repo_methods
                                    if meth["name"] == m["name"]
                                ),
                                None,
                            )
                            if repo_method:
                                exists = True
                                path = decl["path"]
                                issues.extend(compare_parameters(m, repo_method))
                    else:
                        exists = True
                        path = "local"
                    break
            # Record usages

            for call in self.snippet.get("calls", []):
                if (
                    call.get("type") == "method"
                    and call.get("name") == m["name"]
                    and call.get("objectType") == m.get("class")
                ):
                    usage_issues = compare_parameters(
                        {"params": call.get("args", [])}, repo_method or m
                    )
                    usages.append(
                        {"args": call.get("args", []), "issues": usage_issues}
                    )
            result["methods"].append(
                {
                    "name":   m["name"],
                    "class":  m.get("class"),
                    "exists": exists,
                    "path":   path if exists else None,
                    "issues": issues,
                    "usages": usages,
                }
            )
        # --- Classes ---

        for cls_name in self.snippet.get("classes", {}):
            found_decl = next(
                (
                    d
                    for d in self.declarations
                    if d["name"] == cls_name and d["kind"] == "class"
                ),
                None,
            )
            exists = found_decl is not None
            result["classes"].append(
                {
                    "name":   cls_name,
                    "exists": exists,
                    "path":   found_decl["path"] if exists else None,
                }
            )
        # --- Interfaces ---

        for intf_name in self.snippet.get("interfaces", {}):
            found_decl = next(
                (
                    d
                    for d in self.declarations
                    if d["name"] == intf_name and d["kind"] == "interface"
                ),
                None,
            )
            exists = found_decl is not None
            result["interfaces"].append(
                {
                    "name":   intf_name,
                    "exists": exists,
                    "path":   found_decl["path"] if exists else None,
                }
            )
        # --- Imports ---

        for imp in self.snippet.get("imports", []):
            imported_file_path = normalize_path(imp["path"])
            file_data = self.get_repo_file_by_path(imported_file_path)
            match_found = False
            if file_data:
                match_found = (
                    imp["name"] in file_data.get("classes", {})
                    or imp["name"] in file_data.get("interfaces", {})
                    or imp["name"] in file_data.get("enums", {})
                    or any(
                        func["name"] == imp["name"]
                        for func in file_data.get("functions", [])
                    )
                )
            result["imports"].append(
                {
                    "name":         imp["name"],
                    "path":         imp["path"],
                    "exists":       match_found,
                    "resolvedPath": imported_file_path if match_found else None,
                }
            )

            if file_data:
                # ✅ If this is an imported enum

                if imp["name"] in file_data.get("enums", {}):
                    self.declarations.append(
                        {
                            "name": imp["name"],
                            "type": imp["name"],
                            "kind": "enum",
                            "path": imported_file_path,
                        }
                    )
                # ✅ If this is an imported function

                for func in file_data.get("functions", []):
                    if func["name"] == imp["name"]:
                        usages = []
                        for call in self.snippet.get("calls", []):
                            if (
                                call.get("type") == "function"
                                and call.get("name") == func["name"]
                            ):
                                issues = compare_parameters(
                                    {"params": call.get("args", [])}, func
                                )
                                usages.append(
                                    {"args": call.get("args", []), "issues": issues}
                                )
                        result["functions"].append(
                            {
                                "name":   func["name"],
                                "exists": True,
                                "path":   imported_file_path,
                                "issues": [],
                                "usages": usages,
                            }
                        )
                # ✅ If this is an imported class — include its methods

                used_methods = {
                    (call["objectType"], call["name"])
                    for call in self.snippet.get("calls", [])
                    if call.get("type") == "method"
                }

                for method in file_data.get("methods", []):
                    if (method.get("class"), method["name"]) in used_methods:
                        usages = []
                        for call in self.snippet.get("calls", []):
                            if (
                                call.get("type") == "method"
                                and call.get("name") == method["name"]
                                and call.get("objectType") == method.get("class")
                            ):
                                issues = compare_parameters(
                                    {"params": call.get("args", [])}, method
                                )
                                usages.append(
                                    {"args": call.get("args", []), "issues": issues}
                                )
                        result["methods"].append(
                            {
                                "name":   method["name"],
                                "class":  method.get("class"),
                                "exists": True,
                                "path":   imported_file_path,
                                "issues": [],
                                "usages": usages,
                            }
                        )
        # --- Member Accesses ---

        for access in self.snippet.get("memberAccesses", []):
            obj = access["object"]
            member = access["member"]
            issues = []
            exists = False
            path = None

            decl = next((d for d in self.declarations if d["name"] == obj), None)
            if decl:
                if decl["path"] != "local":
                    file = self.get_repo_file_by_path(decl["path"])
                    if file:
                        if decl["kind"] == "class":
                            if any(
                                m["name"] == member for m in file.get("methods", [])
                            ):
                                exists = True
                                path = decl["path"]
                            else:
                                issues.append(
                                    f"Method '{member}' not found in class '{decl['type']}'"
                                )
                        elif decl["kind"] == "interface":
                            props = file.get("interfaces", {}).get(decl["type"], {})
                            if member in props:
                                exists = True
                                path = decl["path"]
                            else:
                                issues.append(
                                    f"Property '{member}' not found in interface '{decl['type']}'"
                                )
                        elif decl["kind"] == "enum":
                            if member in file.get("enums", {}).get(decl["type"], {}):
                                exists = True
                                path = decl["path"]
                            else:
                                issues.append(
                                    f"Enum member '{member}' not found in enum '{decl['type']}'"
                                )
                else:
                    exists = True
                    path = "local"
            else:
                issues.append(f"Variable '{obj}' is not declared or imported.")
            result["memberAccesses"].append(
                {
                    "object": obj,
                    "name":   member,
                    "exists": exists,
                    "path":   path if exists else None,
                    "issues": issues,
                }
            )
        return result
