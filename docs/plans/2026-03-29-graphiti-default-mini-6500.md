# Graphiti Default Mini 6500 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Move the local speed-first Graphiti default from `gpt-5.4-mini + 4000/400` to the faster turbo profile `gpt-5.4-mini + 6500/650`.

**Architecture:** Keep the current backend and sidecar flow unchanged. Only retune backend defaults and aligned tests so fresh local graph builds inherit the fastest proven profile automatically.

**Tech Stack:** Flask, pytest, local Graphiti sidecar, Kuzu, OpenAI-compatible API

---

### Task 1: Update the default-value tests first

**Files:**
- Modify: `backend/tests/test_config_graph_backend.py`
- Modify: `backend/tests/test_file_parser_defaults.py`

**Step 1: Change the expected defaults**

- Assert `Config.DEFAULT_CHUNK_SIZE == 6500`
- Assert `Config.DEFAULT_CHUNK_OVERLAP == 650`
- Make the file-parser default test prove a `6400`-char string stays as one chunk

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_config_graph_backend.py tests/test_file_parser_defaults.py -q`

Expected: failures showing the implementation still uses `4000/400`

### Task 2: Update the backend defaults

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/utils/file_parser.py`
- Modify: `backend/app/api/graph.py`

**Step 1: Change config defaults to `6500/650`**

**Step 2: Change file-parser helper defaults to `6500/650`**

**Step 3: Update `/api/graph/build` example comments to `6500/650`**

### Task 3: Run focused regression tests

**Files:**
- Test: `backend/tests/test_graphiti_graph_builder.py`
- Test: `backend/tests/test_graph_api_graphiti.py`
- Test: `backend/tests/test_project_defaults.py`
- Test: `backend/tests/test_config_graph_backend.py`
- Test: `backend/tests/test_file_parser_defaults.py`

**Step 1: Run the focused suite**

Run: `cd backend && uv run pytest tests/test_graphiti_graph_builder.py tests/test_graph_api_graphiti.py tests/test_project_defaults.py tests/test_config_graph_backend.py tests/test_file_parser_defaults.py -q`

Expected: all tests pass

### Task 4: Refresh the live backend process

**Files:**
- Runtime only

**Step 1: Restart backend**

**Step 2: Verify health and loaded defaults**

Run: `curl -sS http://127.0.0.1:5001/health`

Expected: `status=ok`
