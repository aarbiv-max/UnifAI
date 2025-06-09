# Node Tools — TypeScript Static Analyzer

This directory contains the TypeScript analysis tooling used by the Python-based evaluator to extract structural code symbols (functions, methods, classes, etc.) from both:

- Arbitrary TypeScript **code snippets** (sent from Python)
- Actual **repository files** (for symbol database building)

---

## 🔧 Purpose

The main purpose is to:
- Parse TypeScript code structurally (not using regex)
- Identify user-defined symbols only
- Exclude anything imported from external libraries or built-ins

---

## 📁 Contents

| File               | Description |
|--------------------|-------------|
| `ts_analyze.js`    | Node.js script using `ts-morph` to parse and analyze TypeScript code from stdin |
| `package.json`     | Declares the dependencies (currently uses `ts-morph`) |
| `yarn.lock`        | Yarn lockfile to ensure consistent installs |
| `.gitignore`       | Ignores `node_modules/` from version control |
| `.yarnrc.yml`      | Yarn config file for the local environment |
| `.yarn/`           | Yarn internal data (auto-managed) |
| `node_modules/`    | Installed dependencies (not committed) |

---

## 🚀 How it works

1. Python sends a TypeScript snippet or file content to `ts_analyze.js` via stdin
2. `ts-morph` parses the code and builds an AST
3. It collects:
   - ✅ Only symbols defined **in the file**
   - ❌ Skips built-ins and external libraries (`node_modules`, global types, etc.)
4. The result is returned as JSON to Python

---

## 🧪 Example CLI Usage

```bash
echo "function greet() { return 'hi' }" | node ts_analyze.js
