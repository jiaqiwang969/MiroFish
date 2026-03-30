# Graphiti Local Startup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a one-command local startup path for `graphiti_service + backend + frontend` while keeping the existing `npm run dev` behavior unchanged.

**Architecture:** Keep the current root npm-based process orchestration and extend it additively. The new Graphiti path is expressed as extra root scripts so local developers can install and start the sidecar through the same entrypoint they already use for backend and frontend. Documentation is updated to make `dev:graphiti` the recommended local path.

**Tech Stack:** npm scripts, `concurrently`, `uv`, Flask backend, Flask Graphiti sidecar, Vite frontend

---

### Task 1: Add a failing script-contract test

**Files:**
- Create: `scripts/test_graphiti_dev_scripts.mjs`
- Modify: `package.json`

**Step 1: Write the failing test**

```js
import fs from "node:fs";

const pkg = JSON.parse(fs.readFileSync(new URL("../package.json", import.meta.url), "utf8"));
const scripts = pkg.scripts || {};

const required = {
  "setup:graphiti": "cd graphiti_service && uv sync",
  "graphiti": "cd graphiti_service && uv run python app.py",
};

for (const [name, command] of Object.entries(required)) {
  if (scripts[name] !== command) {
    throw new Error(`Expected ${name} to equal ${command}, got ${scripts[name]}`);
  }
}

if (!scripts["dev:graphiti"]?.includes('npm run graphiti')) {
  throw new Error("Expected dev:graphiti to start the graphiti service");
}

if (!scripts["dev:graphiti"]?.includes('npm run backend')) {
  throw new Error("Expected dev:graphiti to start the backend");
}

if (!scripts["dev:graphiti"]?.includes('npm run frontend')) {
  throw new Error("Expected dev:graphiti to start the frontend");
}

if (!scripts["setup:all"]?.includes("npm run setup:graphiti")) {
  throw new Error("Expected setup:all to include setup:graphiti");
}
```

**Step 2: Run test to verify it fails**

Run: `node scripts/test_graphiti_dev_scripts.mjs`
Expected: FAIL because the new scripts are not present yet

**Step 3: Commit**

```bash
git add scripts/test_graphiti_dev_scripts.mjs
git commit -m "test: add graphiti startup script contract"
```

### Task 2: Add minimal root npm scripts

**Files:**
- Modify: `package.json`
- Test: `scripts/test_graphiti_dev_scripts.mjs`

**Step 1: Write minimal implementation**

Add these scripts while keeping `dev` unchanged:

```json
{
  "setup:graphiti": "cd graphiti_service && uv sync",
  "setup:all": "npm run setup && npm run setup:backend && npm run setup:graphiti",
  "graphiti": "cd graphiti_service && uv run python app.py",
  "dev:graphiti": "concurrently --kill-others -n \"graphiti,backend,frontend\" -c \"magenta,green,cyan\" \"npm run graphiti\" \"npm run backend\" \"npm run frontend\""
}
```

**Step 2: Run test to verify it passes**

Run: `node scripts/test_graphiti_dev_scripts.mjs`
Expected: PASS

**Step 3: Commit**

```bash
git add package.json scripts/test_graphiti_dev_scripts.mjs
git commit -m "feat: add graphiti local startup scripts"
```

### Task 3: Update README to match the actual Graphiti local workflow

**Files:**
- Modify: `README.md`

**Step 1: Update startup examples**

Ensure README:

- recommends `npm run setup:all`
- mentions `setup:graphiti` as part of all-in-one setup
- recommends `npm run dev:graphiti` for local Graphiti mode
- explicitly states `npm run dev` keeps the legacy path

**Step 2: Verify documentation references**

Run: `rg -n "dev:graphiti|setup:graphiti|npm run dev" README.md`
Expected: README shows the new Graphiti command and preserves the legacy command context

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document graphiti local startup flow"
```

### Task 4: Verify end-to-end local startup flow

**Files:**
- Modify: none

**Step 1: Verify script contract test**

Run: `node scripts/test_graphiti_dev_scripts.mjs`
Expected: PASS

**Step 2: Verify backend tests still pass**

Run: `cd backend && uv run pytest tests -q`
Expected: PASS

**Step 3: Verify sidecar tests still pass**

Run: `cd graphiti_service && uv run pytest tests/test_service.py tests/test_app.py -q`
Expected: PASS

**Step 4: Verify services can still start**

Run:

```bash
npm run graphiti
```

Expected: sidecar starts on `http://127.0.0.1:8011`

**Step 5: Commit**

```bash
git add package.json README.md scripts/test_graphiti_dev_scripts.mjs
git commit -m "chore: verify graphiti local startup workflow"
```
