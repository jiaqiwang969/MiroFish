# Graphiti Event Loop Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Keep Graphiti sidecar requests on one long-lived asyncio event loop so repeated batch ingestion no longer breaks with `Event loop is closed` and `APIConnectionError`.

**Architecture:** Replace per-call `asyncio.run(...)` with a dedicated background loop owned by `GraphitiMemoryService`, and submit coroutines with `asyncio.run_coroutine_threadsafe(...)`. Add a regression test that proves repeated `_run_async(...)` calls reuse the same loop and that shutdown is explicit.

**Tech Stack:** Python 3.11, asyncio, threading, pytest, Flask sidecar service

---

### Task 1: Lock Down The Regression

**Files:**
- Modify: `graphiti_service/tests/test_service.py`

**Step 1: Write the failing test**

Add a test that calls `GraphitiMemoryService._run_async(...)` twice with a coroutine returning the current running loop object, then asserts both calls used the same loop and that the loop is still running before explicit shutdown.

**Step 2: Run test to verify it fails**

Run: `cd graphiti_service && .venv/bin/pytest tests/test_service.py::test_run_async_reuses_single_background_event_loop -q`
Expected: FAIL because the current implementation uses `asyncio.run(...)`, which creates and closes a fresh loop for every call.

### Task 2: Implement The Minimal Runtime Fix

**Files:**
- Modify: `graphiti_service/service.py`
- Modify: `graphiti_service/tests/test_service.py`

**Step 1: Add a persistent async runtime**

Create a dedicated background event loop thread inside `GraphitiMemoryService`, plus an idempotent `close()` method that shuts down async clients and the Kuzu driver cleanly.

**Step 2: Route `_run_async(...)` through that runtime**

Use `asyncio.run_coroutine_threadsafe(...)` so all Graphiti/OpenAI async work runs on the same loop across batches.

**Step 3: Run targeted tests**

Run: `cd graphiti_service && .venv/bin/pytest tests/test_service.py::test_run_async_reuses_single_background_event_loop tests/test_service.py::test_get_graphiti_creates_kuzu_fulltext_indexes tests/test_service.py::test_warmup_initializes_graphiti_and_embedding tests/test_app.py -q`
Expected: PASS

**Step 4: Run the full sidecar unit suite**

Run: `cd graphiti_service && .venv/bin/pytest tests/test_service.py tests/test_app.py -q`
Expected: PASS

**Step 5: Re-run the real local validation**

Use a fresh Graphiti DB path and confirm multi-batch ingestion gets past the third batch without `Event loop is closed`.
