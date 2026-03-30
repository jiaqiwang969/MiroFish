# Graphiti WAL Recovery Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prevent Graphiti sidecar from leaving crash-prone Kuzu WAL files behind, and automatically back up stale WAL files on startup so the sidecar can recover availability.

**Architecture:** Add one write-side safeguard and one startup safeguard. After successful Graphiti writes, explicitly issue `CHECKPOINT` so Kuzu folds the WAL into the main database file. Before opening the database, detect an existing `graphiti.kuzu.wal`, rename it to a timestamped backup, and continue on the base DB file.

**Tech Stack:** Python 3.11, asyncio, Kuzu, Graphiti, pytest

---

### Task 1: Lock Down Recovery Behavior

**Files:**
- Modify: `graphiti_service/tests/test_service.py`

**Step 1: Write the failing tests**

Add:
- a test asserting `add_episodes(...)` issues `CHECKPOINT;` after successful writes
- a test asserting service startup moves an existing `graphiti.kuzu.wal` to a timestamped backup path

**Step 2: Run tests to verify they fail**

Run: `cd graphiti_service && .venv/bin/pytest tests/test_service.py::test_add_episodes_checkpoints_after_successful_batch tests/test_service.py::test_service_backs_up_stale_wal_before_open -q`
Expected: FAIL because the current service neither checkpoints writes nor rotates stale WAL files.

### Task 2: Implement Minimal WAL Safeguards

**Files:**
- Modify: `graphiti_service/config.py`
- Modify: `graphiti_service/service.py`
- Modify: `graphiti_service/tests/test_service.py`
- Modify: `graphiti_service/.env.example`
- Modify: `README.md`

**Step 1: Add config switches**

Add default-on config flags for post-write checkpointing and stale WAL recovery.

**Step 2: Implement startup WAL backup**

Before Kuzu opens the DB, rename any existing `*.wal` file to a timestamped backup and log the recovery action.

**Step 3: Implement post-write checkpoint**

After successful `add_episodes(...)` writes, run `CHECKPOINT;` against the Kuzu driver.

**Step 4: Run focused tests**

Run: `cd graphiti_service && .venv/bin/pytest tests/test_service.py::test_add_episodes_checkpoints_after_successful_batch tests/test_service.py::test_service_backs_up_stale_wal_before_open -q`
Expected: PASS

**Step 5: Run full verification**

Run: `cd graphiti_service && .venv/bin/pytest tests/test_service.py tests/test_app.py -q`
Expected: PASS

**Step 6: Run a real recovery validation**

Use a copied broken DB+WAL pair and confirm warmup succeeds, the original `.wal` disappears, and a backup file remains beside the DB.
