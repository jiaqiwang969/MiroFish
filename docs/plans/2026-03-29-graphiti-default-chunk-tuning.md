# Graphiti Default Chunk Tuning Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make Graphiti graph builds faster by changing the default chunk settings from `500/50` to `1000/100` everywhere the backend persists or consumes project defaults.

**Architecture:** Keep the current `Flask -> Graphiti sidecar -> Kuzu` flow unchanged and only tune the backend's default chunk sizing. The implementation must keep config defaults, project persistence defaults, and API behavior aligned so new builds consistently use the faster settings without requiring request overrides.

**Tech Stack:** Python, Flask, pytest, dataclasses

---

### Task 1: Lock the new defaults with failing tests

**Files:**
- Modify: `backend/tests/test_config_graph_backend.py`
- Modify: `backend/tests/test_graph_api_graphiti.py`
- Create: `backend/tests/test_project_defaults.py`

**Step 1: Write the failing test**

Add tests that assert:

- `Config.DEFAULT_CHUNK_SIZE == 1000`
- `Config.DEFAULT_CHUNK_OVERLAP == 100`
- `ProjectManager.create_project()` persists `1000/100`
- `/api/graph/build` without explicit chunk params stores `1000/100` on the project

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_config_graph_backend.py tests/test_graph_api_graphiti.py tests/test_project_defaults.py -q`

Expected: FAIL because the code still hard-codes `500/50`.

**Step 3: Write minimal implementation**

Update config and project defaults to use the new values.

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_config_graph_backend.py tests/test_graph_api_graphiti.py tests/test_project_defaults.py -q`

Expected: PASS

### Task 2: Align code-level defaults and docs

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/models/project.py`
- Modify: `backend/app/services/text_processor.py`
- Modify: `backend/app/services/graph_builder.py`
- Modify: `backend/app/utils/file_parser.py`
- Modify: `backend/app/api/graph.py`

**Step 1: Write the failing test**

Reuse the red tests from Task 1 as the guardrail for any lingering `500/50` usage that affects runtime behavior.

**Step 2: Run test to verify it still fails if only part of the defaults are changed**

Run: `cd backend && uv run pytest tests/test_config_graph_backend.py tests/test_graph_api_graphiti.py tests/test_project_defaults.py -q`

Expected: FAIL until config, persisted project defaults, and API path are all aligned.

**Step 3: Write minimal implementation**

Change remaining default parameters and API docstrings from `500/50` to `1000/100`.

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_config_graph_backend.py tests/test_graph_api_graphiti.py tests/test_project_defaults.py -q`

Expected: PASS

### Task 3: Verify the wider Graphiti backend surface

**Files:**
- Test: `backend/tests/test_graphiti_graph_builder.py`

**Step 1: Run targeted regression verification**

Run: `cd backend && uv run pytest tests/test_graphiti_graph_builder.py tests/test_graph_api_graphiti.py tests/test_project_defaults.py tests/test_config_graph_backend.py -q`

Expected: PASS

**Step 2: Run sidecar/backend integration smoke verification**

Run: `curl -sS http://127.0.0.1:5001/api/graph/project/proj_bd74486197c2`

Expected: response shows persisted `chunk_size` and `chunk_overlap` matching the last build configuration.

