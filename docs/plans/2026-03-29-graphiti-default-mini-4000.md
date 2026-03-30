# Graphiti Default Mini 4000 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the local Graphiti speed-first profile the default for fresh runs by keeping `gpt-5.4-mini` as the runtime model and changing backend chunk defaults to `4000/400`.

**Architecture:** Keep the existing `Flask backend -> Graphiti sidecar -> Kuzu` flow unchanged. Only retune config defaults, helper defaults, API examples, and tests so new projects inherit the faster profile without request overrides.

**Tech Stack:** Flask, pytest, local Graphiti sidecar, Kuzu, OpenAI-compatible API

---

### Task 1: Update default-value tests first

**Files:**
- Modify: `backend/tests/test_config_graph_backend.py`
- Modify: `backend/tests/test_file_parser_defaults.py`

**Step 1: Write the failing expectations**

- Change config-default assertions from `2500/250` to `4000/400`
- Change the file-parser default test to prove text shorter than `4000` stays as one chunk

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_config_graph_backend.py tests/test_file_parser_defaults.py -q`

Expected: failures showing the implementation still uses `2500/250`

### Task 2: Update backend defaults

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/utils/file_parser.py`
- Modify: `backend/app/api/graph.py`

**Step 1: Change the config defaults**

- Set `Config.DEFAULT_CHUNK_SIZE = 4000`
- Set `Config.DEFAULT_CHUNK_OVERLAP = 400`

**Step 2: Change the file-parser helper defaults**

- Set `split_text_into_chunks(..., chunk_size=4000, overlap=400)`

**Step 3: Align API examples**

- Update `/api/graph/build` example comments to show `4000/400`

### Task 3: Run focused regression tests

**Files:**
- Test: `backend/tests/test_graph_api_graphiti.py`
- Test: `backend/tests/test_project_defaults.py`
- Test: `backend/tests/test_config_graph_backend.py`
- Test: `backend/tests/test_file_parser_defaults.py`

**Step 1: Run the focused suite**

Run: `cd backend && uv run pytest tests/test_graphiti_graph_builder.py tests/test_graph_api_graphiti.py tests/test_project_defaults.py tests/test_config_graph_backend.py tests/test_file_parser_defaults.py -q`

Expected: all tests pass

### Task 4: Refresh the live backend default behavior

**Files:**
- Runtime only

**Step 1: Restart backend**

Run the backend again so new `Config.DEFAULT_*` values apply.

**Step 2: Verify service health**

Run: `curl -sS http://127.0.0.1:5001/health`

Expected: `status=ok`
