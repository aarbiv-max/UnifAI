import os
import json
import subprocess
from typing import Dict, List, Any, Tuple

class TSCodeAnalyzer:
    def __init__(self):
        self.symbol_database = {
            'functions': [],
            'methods': [],
            'classes': {},  # name -> list of method names
            'interfaces': {},  # name -> dict of properties { propName: type }
            'imports': set()
        }

    def analyze_ts_file(self, file_path: str) -> Dict[str, Any]:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()

        try:
            result = subprocess.run(
                ["node", "../../../node_tools/ts_analyze.js"],
                input=code,
                text=True,
                capture_output=True,
                check=True,
                env={"TS_FILE_NAME": file_path}
            )
            data = json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"Error analyzing {file_path}: {e.stderr}")
            return {
                'functions': [],
                'methods': [],
                'classes': {},
                'interfaces': {},
                'imports': set()
            }

        classes = {cls: [] for cls in data.get('classes', [])}
        for m in data.get('methods', []):
            cls = m['class']
            if cls in classes:
                classes[cls].append(m['name'])

        interfaces = {}
        for iface in data.get('interfaces', []):
            if isinstance(iface, dict):
                interfaces[iface['name']] = iface.get('properties', {})
            else:
                interfaces[iface] = {}  # fallback

        return {
            'functions': data.get('functions', []),
            'methods': data.get('methods', []),
            'classes': classes,
            'interfaces': interfaces,
            'imports': set((imp['path'], imp['type']) for imp in data.get('imports', []))
        }

    def analyze_repository(self, repo_path: str):
        for root, _, files in os.walk(repo_path):
            for file in files:
                if file.endswith('.ts') and not file.endswith('.spec.ts'):
                    full_path = os.path.join(root, file)
                    file_symbols = self.analyze_ts_file(full_path)
                    self.symbol_database['functions'].extend(file_symbols['functions'])
                    self.symbol_database['methods'].extend(file_symbols['methods'])
                    for cls, methods in file_symbols['classes'].items():
                        self.symbol_database['classes'].setdefault(cls, set()).update(methods)
                    self.symbol_database['interfaces'].update(file_symbols['interfaces'])
                    self.symbol_database['imports'].update(file_symbols['imports'])

    def are_signatures_equivalent(self, sym1: Dict, sym2: Dict) -> Tuple[bool, List[str]]:
        issues = []
        if sym1['returnType'] != sym2['returnType']:
            issues.append('Different return type')
        if len(sym1['params']) != len(sym2['params']):
            issues.append('Parameter count mismatch')
        else:
            for p1, p2 in zip(sym1['params'], sym2['params']):
                if p1['type'] != p2['type']:
                    issues.append('Parameter type mismatch')
                    break
        if sym1.get('body', '').strip() != sym2.get('body', '').strip():
            issues.append('Functionality differs')
        return len(issues) == 0, issues

    def verify_code_snippet(self, code: str) -> Dict[str, List[Dict[str, Any]]]:
        try:
            result = subprocess.run(
                ["node",  "../../../node_tools/ts_analyze.js"],
                input=code,
                text=True,
                capture_output=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            print("JS script error:", e.stderr)
            raise

        snippet_data = json.loads(result.stdout)

        verification = {
            'functions': [],
            'methods': [],
            'classes': [],
            'interfaces': [],
            'imports': []
        }

        for fn in snippet_data.get('functions', []):
            match, issues = None, []
            for repo_fn in self.symbol_database['functions']:
                if fn['name'] == repo_fn['name']:
                    equivalent, issues = self.are_signatures_equivalent(fn, repo_fn)
                    if equivalent:
                        match = repo_fn
                        break
            verification['functions'].append({
                'name': fn['name'],
                'exists': match is not None,
                'issues': [] if match else issues
            })

        for m in snippet_data.get('methods', []):
            match, issues = None, []
            for repo_m in self.symbol_database['methods']:
                if m['name'] == repo_m['name'] and m['class'] == repo_m['class']:
                    equivalent, issues = self.are_signatures_equivalent(m, repo_m)
                    if equivalent:
                        match = repo_m
                        break
            verification['methods'].append({
                'name': m['name'],
                'class': m['class'],
                'exists': match is not None,
                'issues': [] if match else issues
            })

        for cls_name in snippet_data.get('classes', []):
            repo_methods = self.symbol_database['classes'].get(cls_name)
            if repo_methods is None:
                verification['classes'].append({
                    'name': cls_name,
                    'exists': False,
                    'issues': ['Class not found in repository']
                })
            else:
                snippet_methods = [m['name'] for m in snippet_data.get('methods', []) if m['class'] == cls_name]
                missing_methods = [m for m in snippet_methods if m not in repo_methods]
                issue_msg = [f"Missing method: {name}" for name in missing_methods]
                verification['classes'].append({
                    'name': cls_name,
                    'exists': True,
                    'issues': issue_msg if issue_msg else []
                })

        for iface in snippet_data.get('interfaces', []):
            iface_name = iface['name'] if isinstance(iface, dict) else iface
            iface_props = iface.get('properties', {}) if isinstance(iface, dict) else {}
            if iface_name not in self.symbol_database['interfaces']:
                verification['interfaces'].append({
                    'name': iface_name,
                    'exists': False,
                    'issues': ['Interface not found in repository']
                })
                continue
            repo_props = self.symbol_database['interfaces'][iface_name]
            issues = []
            for prop, typ in iface_props.items():
                if prop not in repo_props:
                    issues.append(f"Missing property: {prop}")
                elif repo_props[prop] != typ:
                    issues.append(f"Type mismatch in property '{prop}': expected '{repo_props[prop]}', got '{typ}'")
            verification['interfaces'].append({
                'name': iface_name,
                'exists': True,
                'issues': issues
            })

        for imp in snippet_data.get('imports', []):
            tup = (imp['path'], imp['type'])
            verification['imports'].append({
                'path': imp['path'],
                'type': imp['type'],
                'exists': tup in self.symbol_database['imports']
            })

        return verification

evaluator = TSCodeAnalyzer()
evaluator.analyze_repository("/tmp/typescript-starter")

snippet = '''
import { Controller, Get, Post } from '@nestjs/common';
import { NotARealService } from './fake-service';

@Controller()
export class AppController {
  @Get()
  getHello(): string {
    return "Hello from AppController";
  }

  @Post()
  createSomething(): string {
    return "Created something";
  }

  private helperFunction(): void {
    console.log("Helper");
  }
}

interface NotInRepo {
  id: number;
  label: string;
}

function doSomethingCool() {
  return true;
}
'''

result = evaluator.verify_code_snippet(snippet)
print(json.dumps(result, indent=2))
