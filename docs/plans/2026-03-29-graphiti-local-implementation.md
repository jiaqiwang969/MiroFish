# Graphiti Local Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace `zep-cloud` usage in the backend with a local `Graphiti sidecar + Kuzu + bge-m3` implementation while preserving the current HTTP API and user workflow.

**Architecture:** Introduce a local graph backend abstraction in Flask, implement a separate local Graphiti sidecar service with its own Python environment, migrate config and service call sites to the abstraction, and keep app-level DTOs stable so routes and frontend code need minimal change.

**Tech Stack:** Flask, Python 3.11+, Graphiti, Kuzu, OpenAI-compatible chat API, local `bge-m3` embeddings, pytest

## Critical Constraint

This plan replaces the earlier embedded-Graphiti assumption. The main backend cannot install `graphiti-core` in the same environment because `camel-oasis` pins `neo4j==5.23.0` while `graphiti-core` requires `neo4j>=5.26.0`. All Graphiti code therefore lives in a separate sidecar project and environment.

---

### Task 1: Add migration scaffolding and config tests

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/run.py`
- Modify: `.env.example`
- Create: `backend/tests/test_config_graph_backend.py`

**Step 1: Write the failing test**

Add tests that prove:
- Graphiti mode does not require `ZEP_API_KEY`
- Graphiti mode requires `GRAPHITI_SERVICE_URL` in the main backend
- Existing LLM config is still required

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_config_graph_backend.py -v`
Expected: FAIL because current config still validates embedded Graphiti settings instead of sidecar settings

**Step 3: Write minimal implementation**

- Add graph backend config fields.
- Update validation logic for sidecar mode.
- Update `.env.example` so backend and sidecar config are clearly separated.

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_config_graph_backend.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/config.py backend/run.py backend/pyproject.toml .env.example backend/tests/test_config_graph_backend.py
git commit -m "feat: add graphiti backend configuration"
```

### Task 2: Introduce graph backend abstraction

**Files:**
- Create: `backend/app/services/graph_backend.py`
- Create: `backend/app/services/graphiti_sidecar_client.py`
- Create: `backend/tests/test_graph_backend_contract.py`

**Step 1: Write the failing test**

Add contract tests for:
- selecting the correct backend implementation from config
- creating a graph through the adapter
- ingesting text episodes through the adapter
- listing normalized nodes and edges through the adapter
- appending runtime activity episodes through the adapter

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_graph_backend_contract.py -v`
Expected: FAIL because abstraction does not exist

**Step 3: Write minimal implementation**

- Define backend protocol / interface.
- Define normalized DTO helpers and mapping helpers.
- Add a minimal HTTP sidecar client and backend factory.

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_graph_backend_contract.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/graph_backend.py backend/tests/test_graph_backend_contract.py
git commit -m "feat: add graph backend abstraction"
```

### Task 3: Create Graphiti sidecar service skeleton and graph build path

**Files:**
- Create: `graphiti_service/pyproject.toml`
- Create: `graphiti_service/app.py`
- Create: `graphiti_service/config.py`
- Create: `graphiti_service/tests/test_graphiti_service_graphs.py`
- Modify: `backend/app/services/graph_builder.py`
- Create: `backend/tests/test_graphiti_graph_builder.py`

**Step 1: Write the failing test**

Add tests that verify a small fixture text can:
- create a local graph through the sidecar API
- ingest chunks through the adapter
- produce a persisted graph id in the main backend flow

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_graphiti_graph_builder.py -v`
Expected: FAIL because sidecar API and GraphBuilder integration are not implemented

**Step 3: Write minimal implementation**

- Implement sidecar config and Graphiti/Kuzu initialization.
- Implement sidecar endpoints for graph creation and ingestion.
- Update `GraphBuilderService` to use the adapter instead of Zep directly.

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_graphiti_graph_builder.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add graphiti_service backend/app/services/graph_builder.py backend/tests/test_graphiti_graph_builder.py
git commit -m "feat: migrate graph building to graphiti"
```

### Task 4: Migrate entity reader and simulation prep

**Files:**
- Modify: `backend/app/services/zep_entity_reader.py`
- Modify: `backend/app/api/simulation.py`
- Create: `backend/tests/test_entity_reader_graphiti.py`

**Step 1: Write the failing test**

Add tests that verify:
- all nodes are normalized from Graphiti
- entity filtering still excludes default-only labels
- related edges/nodes enrichment still works

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_entity_reader_graphiti.py -v`
Expected: FAIL because reader still depends on `zep-cloud`

**Step 3: Write minimal implementation**

- Switch the entity reader to the backend abstraction.
- Keep the API response shape stable.

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_entity_reader_graphiti.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/zep_entity_reader.py backend/app/api/simulation.py backend/tests/test_entity_reader_graphiti.py
git commit -m "feat: migrate entity reading to graphiti"
```

### Task 5: Migrate runtime memory update path

**Files:**
- Modify: `backend/app/services/zep_graph_memory_updater.py`
- Create: `backend/tests/test_graph_memory_updater_graphiti.py`

**Step 1: Write the failing test**

Add tests that verify runtime action descriptions are appended into the local graph backend and non-meaningful actions are still skipped.

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_graph_memory_updater_graphiti.py -v`
Expected: FAIL because updater still depends on Zep

**Step 3: Write minimal implementation**

- Replace direct Zep writes with Graphiti ingestion calls.
- Preserve batching and action-to-text behavior.

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_graph_memory_updater_graphiti.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/zep_graph_memory_updater.py backend/tests/test_graph_memory_updater_graphiti.py
git commit -m "feat: migrate runtime graph memory updates"
```

### Task 6: Migrate report retrieval tools

**Files:**
- Modify: `backend/app/services/zep_tools.py`
- Modify: `backend/app/services/report_agent.py`
- Create: `backend/tests/test_report_tools_graphiti.py`

**Step 1: Write the failing test**

Add tests that verify report retrieval still returns normalized facts, edges, and node information from the local backend.

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_report_tools_graphiti.py -v`
Expected: FAIL because report tools still depend on Zep-specific search

**Step 3: Write minimal implementation**

- Translate report search paths to Graphiti.
- Normalize results into current DTOs.

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_report_tools_graphiti.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/zep_tools.py backend/app/services/report_agent.py backend/tests/test_report_tools_graphiti.py
git commit -m "feat: migrate report retrieval to graphiti"
```

### Task 7: Remove remaining Zep coupling and run full verification

**Files:**
- Modify: `backend/app/api/graph.py`
- Modify: `docker-compose.yml`
- Modify: `Dockerfile`
- Modify: `README.md`
- Modify: `README-EN.md`
- Create: `graphiti_service/.env.example`

**Step 1: Write the failing test**

Add or extend an end-to-end backend smoke test that boots the app in Graphiti mode and verifies startup no longer requires `ZEP_API_KEY` and instead expects a reachable `GRAPHITI_SERVICE_URL`.

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests -v`
Expected: FAIL because there are remaining Zep couplings

**Step 3: Write minimal implementation**

- Remove remaining `zep-cloud` assumptions from routes/docs/runtime packaging.
- Update deployment docs for the new two-process local stack.

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/api/graph.py README.md README-EN.md docker-compose.yml Dockerfile backend/tests
git commit -m "feat: complete local graphiti migration"
```
