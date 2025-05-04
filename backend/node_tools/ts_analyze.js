const { Project, SyntaxKind } = require("ts-morph");
const path = require("path");
const fs = require("fs");

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
      calls: []
    };

    // --- collect functions ---
    for (const fn of sourceFile.getFunctions()) {
      const name = fn.getName();
      if (!name) continue;
      let params = [], returnType = "any";
      try { params = fn.getParameters().map(p => p.getType().getText()); } catch {}
      try { returnType = fn.getReturnType().getText(); } catch {}

      result[filePath].functions.push({
        name, params, returnType,
        body: fn.getBodyText()?.replace(/\s+/g, " ").trim() || ""
      });
    }

    // --- collect classes and methods ---
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

    // --- collect interfaces ---
    for (const intf of sourceFile.getInterfaces()) {
      const intfName = intf.getName();
      const props = {};
      for (const prop of intf.getProperties()) {
        try { props[prop.getName()] = prop.getType().getText(); } catch {}
      }
      result[filePath].interfaces[intfName] = props;
    }

    // --- collect imports ---
    for (const imp of sourceFile.getImportDeclarations()) {
      const modulePath = imp.getModuleSpecifierValue();
      for (const named of imp.getNamedImports()) {
        result[filePath].imports.push({
          name: named.getName(),
          path: modulePath
        });
      }
    }

    // --- collect member accesses ---
    for (const access of sourceFile.getDescendantsOfKind(SyntaxKind.PropertyAccessExpression)) {
      const expr = access.getExpression();
      const name = access.getName();
      let prop = null;
      let isBuiltIn = false;
    
      try {
        const exprType = expr.getType();
        prop = exprType?.getProperty(name);
    
        // Check if the type is from lib.dom.d.ts or standard built-in libs
        const symbol = exprType?.getSymbol();
        if (symbol) {
          const declarations = symbol.getDeclarations();
          if (declarations.length > 0) {
            const declSourceFile = declarations[0].getSourceFile();
            const declPath = declSourceFile.getFilePath();
            if (declPath.includes("/node_modules/typescript/lib/") || declPath.includes("/lib.")) {
              isBuiltIn = true;
            }
          }
        }
      } catch {}
    
      if (!isBuiltIn) {
        result[filePath].memberAccesses.push({
          object: expr.getText(),
          member: name
        });
      }
    }

    for (const call of sourceFile.getDescendantsOfKind(SyntaxKind.CallExpression)) {
      const expr = call.getExpression();

      // Function call: sum(...)
      if (expr.getKind() === SyntaxKind.Identifier) {
        result[filePath].calls.push({
          type: "function",
          name: expr.getText(),
          args: call.getArguments().map(arg => arg.getText())
        });
      }

      // Method call: obj.method(...)
      if (expr.getKind() === SyntaxKind.PropertyAccessExpression) {
        const objExpr = expr.getExpression();
        const methodName = expr.getName();

        // Attempt to get the object type (for validation like class matching)
        let objectType = null;
        try {
          objectType = objExpr.getType().getSymbol()?.getName() || null;
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
