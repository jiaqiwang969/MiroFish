# Graphiti Default Chunk 2500 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Change the Graphiti default chunk settings from `1000/100` to `2500/250` everywhere new backend builds consume or persist chunk defaults.

**Architecture:** Keep the current `Flask -> Graphiti sidecar -> Kuzu` flow unchanged and only retune the backend defaults. The change must keep config defaults, project persistence, and `/api/graph/build` behavior aligned so new builds pick up `2500/250` without explicit request overrides.

**Tech Stack:** Python, Flask, pytest, dataclasses

---

### Task 1: Lock the new defaults with a failing test

**Files:**
- Modify: `backend/tests/test_config_graph_backend.py`

**Step 1: Write the failing test**

Change the Graphiti default assertions to:

- `Config.DEFAULT_CHUNK_SIZE == 2500`
- `Config.DEFAULT_CHUNK_OVERLAP == 250`

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_config_graph_backend.py::test_chunk_defaults_are_tuned_for_graphiti_build_speed -q`

Expected: FAIL because the code still returns `1000/100`.

**Step 3: Write minimal implementation**

Update the config defaults to `2500/250`.

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_config_graph_backend.py::test_chunk_defaults_are_tuned_for_graphiti_build_speed -q`

Expected: PASS

### Task 2: Align persistence and helper defaults

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/utils/file_parser.py`
- Modify: `backend/app/api/graph.py`
- Modify: `backend/tests/test_project_defaults.py`
- Modify: `backend/tests/test_graph_api_graphiti.py`

**Step 1: Write failing assertions**

Ensure project creation and `/api/graph/build` persist `Config.DEFAULT_CHUNK_SIZE` and `Config.DEFAULT_CHUNK_OVERLAP` with the new values.

**Step 2: Run focused tests**

Run: `cd backend && uv run pytest tests/test_graph_api_graphiti.py tests/test_project_defaults.py -q`

Expected: PASS once config and helper defaults are aligned.

**Step 3: Write minimal implementation**

Update any remaining hard-coded `1000/100` defaults or doc examples to `2500/250`.

**Step 4: Re-run focused tests**

Run: `cd backend && uv run pytest tests/test_graph_api_graphiti.py tests/test_project_defaults.py -q`

Expected: PASS

### Task 3: Run regression verification

**Files:**
- Test: `backend/tests/test_graphiti_graph_builder.py`
- Test: `backend/tests/test_graph_api_graphiti.py`
- Test: `backend/tests/test_project_defaults.py`
- Test: `backend/tests/test_config_graph_backend.py`

**Step 1: Run targeted regression suite**

Run: `cd backend && uv run pytest tests/test_graphiti_graph_builder.py tests/test_graph_api_graphiti.py tests/test_project_defaults.py tests/test_config_graph_backend.py -q`

Expected: PASS

**Step 2: Confirm the change in a live project**

Run: `curl -sS http://127.0.0.1:5001/api/graph/project/proj_c71979d2c57a`

Expected: response shows the project now stores `chunk_size=2500` and `chunk_overlap=250` after the last rebuild.
