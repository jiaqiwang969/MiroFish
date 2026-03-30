import fs from "node:fs";

const packageJsonPath = new URL("../package.json", import.meta.url);
const pkg = JSON.parse(fs.readFileSync(packageJsonPath, "utf8"));
const scripts = pkg.scripts || {};

const requiredScripts = {
  "setup:graphiti": "cd graphiti_service && uv sync",
  graphiti: "cd graphiti_service && uv run python app.py",
};

for (const [name, command] of Object.entries(requiredScripts)) {
  if (scripts[name] !== command) {
    throw new Error(`Expected script ${name} to equal "${command}", got "${scripts[name]}"`);
  }
}

const devGraphiti = scripts["dev:graphiti"];
if (typeof devGraphiti !== "string") {
  throw new Error("Expected script dev:graphiti to exist");
}

for (const expected of ["npm run graphiti", "npm run backend", "npm run frontend"]) {
  if (!devGraphiti.includes(expected)) {
    throw new Error(`Expected dev:graphiti to include "${expected}"`);
  }
}

if (!scripts["setup:all"]?.includes("npm run setup:graphiti")) {
  throw new Error('Expected setup:all to include "npm run setup:graphiti"');
}

if (scripts.dev !== 'concurrently --kill-others -n "backend,frontend" -c "green,cyan" "npm run backend" "npm run frontend"') {
  throw new Error("Expected legacy dev script to remain unchanged");
}
