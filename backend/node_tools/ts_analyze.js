// <top of ts‐morph file>
const { Project, SyntaxKind } = require("ts-morph");
const path = require("path");
const fs = require("fs");

// 1) ignore‐list
const IGNORE_MEMBERS = new Set([
  "then", "catch", "finally",
  "expect", "to", "be", "equal", "have", "not", "deep", "property", "length", "include"
]);

function normalizePath(p) {
  return p.replace(/\\/g, "/").replace(/^\.?\/*src\//, "").replace(/\.ts$/, "");
}

async function analyze(files) {
  const project = new Project({
    useInMemoryFileSystem: true,
    compilerOptions: {
      target: 99, // ESNext
      module: 99,
      allowJs: true,
      skipLibCheck: true,
      strict: false
    },
    skipAddingFilesFromTsConfig: true
  });

  for (const [filename, content] of Object.entries(files)) {
    project.createSourceFile(filename, content, { overwrite: true });
  }

  const result = {};

  for (const sourceFile of project.getSourceFiles()) {
    const filePath = normalizePath(sourceFile.getFilePath());
    result[filePath] = {
      functions: [],
      methods: [],
      classes: {},
      interfaces: {},
      imports: [],
      memberAccesses: [],
      enums: {},
      calls: []
    };

    // --- collect functions---
    for (const fn of sourceFile.getFunctions()) {
      const name = fn.getName();
      if (!name) continue;
      let params = [], returnType = "any";
      try {
        params = fn.getParameters().map(p => ({
          type: p.getType().getText(),
          optional: p.isOptional()
        }));
      } catch {}
      try {
        returnType = fn.getReturnType().getText();
      } catch {}

      result[filePath].functions.push({
        name, params, returnType,
        body: fn.getBodyText()?.replace(/\s+/g, " ").trim() || ""
      });
    }

    // --- collect classes & methods  ---
    for (const cls of sourceFile.getClasses()) {
      const clsName = cls.getName();
      if (!clsName) continue;
      result[filePath].classes[clsName] = [];
      for (const method of cls.getMethods()) {
        const methodName = method.getName();
        let params = [], returnType = "any";
        try { params = method.getParameters().map(p => p.getType().getText()); } catch {}
        try { returnType = method.getReturnType().getText(); } catch {}

        result[filePath].methods.push({
          name: methodName, class: clsName, params, returnType,
          body: method.getBodyText()?.replace(/\s+/g, " ").trim() || ""
        });
        result[filePath].classes[clsName].push(methodName);
      }
    }

    // --- collect enums & interfaces & imports---
    result[filePath].enums = {};
    for (const enm of sourceFile.getEnums()) {
      const enumName = enm.getName();
      const members = enm.getMembers().map(m => m.getName());
      result[filePath].enums[enumName] = members;
    }

    for (const intf of sourceFile.getInterfaces()) {
      const intfName = intf.getName();
      const props = {};
      for (const prop of intf.getProperties()) {
        try {
          props[prop.getName()] = prop.getType().getText();
        } catch {}
      }
      result[filePath].interfaces[intfName] = props;
    }

    for (const imp of sourceFile.getImportDeclarations()) {
      const modulePath = imp.getModuleSpecifierValue();
      const namedImports = imp.getNamedImports();
      if (namedImports.length === 0) {
        const defaultImport = imp.getDefaultImport();
        if (defaultImport) {
          result[filePath].imports.push({ name: defaultImport.getText(), path: modulePath });
        }
      } else {
        for (const named of namedImports) {
          const alias = named.getAliasNode()?.getText();
          const name = named.getName();
          result[filePath].imports.push({
            name: alias || name,
            originalName: name,
            path: modulePath
          });
        }
      }
    }

    // --- collect member accesses ---
    for (const access of sourceFile.getDescendantsOfKind(SyntaxKind.PropertyAccessExpression)) {
      const expr = access.getExpression();
      const name = access.getName();

      // 1) skip built-in if in IGNORE_MEMBERS
      if (IGNORE_MEMBERS.has(name)) {
        continue;
      }

      let prop = null;
      let isBuiltIn = false;
      let sourcePath = null;
      let isLocal = false;
      let unresolved = true;

      try {
        const exprType = expr.getType();
        prop = exprType?.getProperty(name);
        const symbol = exprType?.getSymbol();
        if (symbol) {
          const declarations = symbol.getDeclarations();
          if (declarations.length > 0) {
            const declSourceFile = declarations[0].getSourceFile();
            const declPath = declSourceFile.getFilePath();
            sourcePath = normalizePath(declPath);
            unresolved = false;

            // 2) Anything from node_modules is "built-in" for our purposes
            if (declPath.includes("/node_modules/")) {
              isBuiltIn = true;
            }
            // 3) If same file => local
            if (declPath === sourceFile.getFilePath()) {
              isLocal = true;
            }
          }
        }
      } catch {}

      const objectText = expr.getText();
      // 4) skip if truly built-in or a Cypress "cy.*"
      if (isBuiltIn || objectText.startsWith("cy")) {
        continue;
      }

      // 5) If we reached here, this is a user‐defined member‐access
      result[filePath].memberAccesses.push({
        object: objectText,
        member: name,
        path: unresolved ? null : (isLocal ? "local" : sourcePath)
      });
    }

    // --- collect calls --
    for (const call of sourceFile.getDescendantsOfKind(SyntaxKind.CallExpression)) {
      const expr = call.getExpression();

      // A) plain function call
      if (expr.getKind() === SyntaxKind.Identifier) {
        const fnName = expr.getText();
        if (IGNORE_MEMBERS.has(fnName)) {
          continue;
        }
        result[filePath].calls.push({
          type: "function",
          name: fnName,
          args: call.getArguments().map(arg => ({
            text: arg.getText(),
            inferredType: arg.getType().getText()
          }))
        });
      }

      // B) property‐access call (obj.method(...))
      if (expr.getKind() === SyntaxKind.PropertyAccessExpression) {
        const objExpr = expr.getExpression();
        const methodName = expr.getName();
        if (IGNORE_MEMBERS.has(methodName)) {
          continue;
        }

        let objectType = "";
        try {
          objectType = objExpr.getType().getSymbol()?.getName() || "";
        } catch {}
        result[filePath].calls.push({
          type: "method",
          object: objExpr.getText(),
          name: methodName,
          args: call.getArguments().map(arg => arg.getText()),
          objectType: objectType
        });
      }
    }
  }

  return result;
}

async function main() {
  const input = JSON.parse(fs.readFileSync(0, "utf-8"));
  const result = await analyze(input.files);
  console.log(JSON.stringify(result, null, 2));
}

main().catch(e => {
  console.error("TS Morph Error:", e);
  process.exit(1);
});
