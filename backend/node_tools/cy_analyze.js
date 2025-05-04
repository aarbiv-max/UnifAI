const { Project, SyntaxKind } = require("ts-morph");
const fs = require("fs");

function normalizePath(p) {
  return p.replace(/\\/g, "/").replace(/^\.\/\/?\/*src\//, "");
}
async function analyze(files) {
  const project = new Project({
    useInMemoryFileSystem: true,
    compilerOptions: {
      target: 99,  // ESNext
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
    const filePath = sourceFile.getFilePath();
    console.error(`Processing file: ${filePath}`);

    result[filePath] = {
      testBlocks: [],
      cyCommands: [],
      utilsFunctions: []  // To store utility functions like `getTable()`
    };

    const calls = sourceFile.getDescendantsOfKind(SyntaxKind.CallExpression);

    for (const call of calls) {
      const expr = call.getExpression();
      const args = call.getArguments();

      // --- Cypress Test Block Detection ---
      if (expr.getKind() === SyntaxKind.Identifier) {
        const name = expr.getText();
        if (["describe", "it", "beforeEach", "afterEach", "before", "after"].includes(name)) {
          console.error(`Found Cypress test block: ${name}`);
          let labelArg = "";
          let bodyNode = null;

          if (args.length === 3 && args[0]?.getKindName() === "ArrayLiteralExpression") {
            labelArg = args[1]?.getText().replace(/^['"]|['"]$/g, "") || "";
            bodyNode = args[2];
          } else {
            labelArg = args[0]?.getText().replace(/^['"]|['"]$/g, "") || "";
            bodyNode = args[1];
          }

          let body = "";
          if (bodyNode && (bodyNode.getKind() === SyntaxKind.FunctionExpression || bodyNode.getKind() === SyntaxKind.ArrowFunction)) {
            const inner = bodyNode.getBody?.();
            if (inner) {
              body = inner.getText().replace(/\s+/g, " ").trim();
            }
          }

          result[filePath].testBlocks.push({
            type: name,
            name: labelArg,
            body
          });
        }
      }

      // --- Cypress Command Detection ---
      if (expr.getKind() === SyntaxKind.PropertyAccessExpression) {
        const objExpr = expr.getExpression();
        const methodName = expr.getName();

        if (objExpr.getText() === "cy") {
          console.error(`Found Cypress command: ${methodName}`);

          // Add logic for utility/wrapped function detection
          if (methodName === "Commands") {
            const addExpression = call.getArguments()[0];
            if (addExpression && addExpression.getKindName() === "StringLiteral") {
              const commandName = addExpression.getText().replace(/^['"]|['"]$/g, "");
              result[filePath].cyCommands.push({
                command: commandName,
                args: [],
                matchLevel: "exact"
              });
            }
          } else {
            // Check if the method is a wrapped function
            if (['getTable', 'clickButton', 'inputText'].includes(methodName)) {
              result[filePath].utilsFunctions.push({
                function: methodName,
                wrappedCommand: methodName, // Here you link it to the Cypress command it wraps
                args: call.getArguments().map(arg => arg.getText())
              });
            } else {
              result[filePath].cyCommands.push({
                command: methodName,
                args: call.getArguments().map(arg => arg.getText())
              });
            }
          }
        }
      }
    }
  }

  if (!Object.keys(result).length) {
    console.error("Warning: No relevant data found. Check your code for missing Cypress test blocks or commands.");
  }

  return result;
}


async function main() {
  console.error("Starting the main function...");

  try {
    // Read input
    const input = JSON.parse(fs.readFileSync(0, "utf-8"));
    console.error("Input parsed:", input);

    // Analyze the files and gather results
    const result = await analyze(input.files);

    // Debug: Check if the result is empty
    if (Object.keys(result).length === 0) {
      console.error("No analysis results. Please check if the files contain valid Cypress test blocks and commands.");
    }

    // Output the final result in a structured way
    console.error("Analysis completed. Returning result:");
    console.log(JSON.stringify(result, null, 2)); // Print the result to stdout for Python

  } catch (error) {
    console.error("Error during analysis:", error);
    process.exit(1);
  }
}

main().catch(e => {
  console.error("Cypress Morph Error:", e);
  process.exit(1);
});
