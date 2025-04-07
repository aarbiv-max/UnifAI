const { Project } = require("ts-morph");

function isLocalSymbol(symbol, currentFilePath) {
  const decl = symbol?.getDeclarations()?.[0];
  const symbolPath = decl?.getSourceFile()?.getFilePath();
  return symbolPath && symbolPath === currentFilePath;
}

function analyzeTSCode(code, fileName = "virtual.ts") {
  const project = new Project({
    useInMemoryFileSystem: process.env.TS_IN_MEMORY !== "false"
  });
  const sourceFile = project.createSourceFile(fileName, code);
  const currentFilePath = sourceFile.getFilePath();

  const result = {
    functions: [],
    methods: [],
    classes: [],
    interfaces: [],
    imports: []
  };

  sourceFile.getFunctions().forEach(fn => {
    const name = fn.getName();
    const symbol = fn.getSymbol();
    const params = fn.getParameters().map(p => ({
      name: p.getName(),
      type: p.getType().getText()
    }));
    const returnType = fn.getReturnType().getText();
    const body = fn.getBodyText()?.replace(/\s+/g, ' ').trim();

    if (name) {
      result.functions.push({ name, params, returnType, body });
    }
  });

  sourceFile.getClasses().forEach(cls => {
    const clsName = cls.getName();
    const classSymbol = cls.getSymbol();
    if (clsName && isLocalSymbol(classSymbol, currentFilePath)) {
      result.classes.push(clsName);
      cls.getMethods().forEach(method => {
        const methodName = method.getName();
        const methodSymbol = method.getSymbol();
        const params = method.getParameters().map(p => ({
          name: p.getName(),
          type: p.getType().getText()
        }));
        const returnType = method.getReturnType().getText();
        const body = method.getBodyText()?.replace(/\s+/g, ' ').trim();

        if (methodName) {
          result.methods.push({ name: methodName, class: clsName, params, returnType, body });
        }
      });
    }
  });

  sourceFile.getInterfaces().forEach(intf => {
    const name = intf.getName();
    const symbol = intf.getSymbol();
    if (name) {
      result.interfaces.push(name);
    }
  });

  sourceFile.getImportDeclarations().forEach(imp => {
    const path = imp.getModuleSpecifierValue();
    if (path.startsWith("./") || path.startsWith("../")) {
      result.imports.push({ path, type: "local" });
    } else {
      result.imports.push({ path, type: "external" });
    }
  });

  return result;
}

const stdin = process.stdin;
let code = "";
stdin.setEncoding("utf8");

stdin.on("data", chunk => {
  code += chunk;
});

stdin.on("end", () => {
  const fileName = process.env.TS_FILE_NAME || "snippet.ts";
  const analysis = analyzeTSCode(code, fileName);
  console.log(JSON.stringify(analysis, null, 2));
});
