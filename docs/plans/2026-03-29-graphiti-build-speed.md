# Graphiti Build Speed Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Speed up local Graphiti graph construction by switching to `gpt-5.4-mini`, making sidecar request timeout configurable, prewarming the sidecar, and adding benchmark-grade timing visibility.

**Architecture:** Keep the existing `backend -> Graphiti sidecar -> Kuzu` structure. Make latency behavior explicit rather than hidden by the current 30-second timeout, and reduce cold-start cost by warming the Graphiti stack and embedding model at service startup.

**Tech Stack:** Flask, Python, Graphiti, Kuzu, sentence-transformers (`BAAI/bge-m3`), OpenAI-compatible API, pytest

---

### Task 1: Document the new speed-oriented runtime defaults

**Files:**
- Modify: `README.md`
- Modify: `.env.example`
- Modify: `graphiti_service/.env`
- Modify: `.env`

**Step 1: Write the failing test**

No automated test. This is configuration and documentation prep for the runtime benchmark.

**Step 2: Verify current values are still speed-suboptimal**

Run: `rg -n "LLM_MODEL_NAME=.*gpt-5.4|GRAPHITI_REQUEST_TIMEOUT_SECONDS|GRAPHITI_PREWARM" .env .env.example graphiti_service/.env README.md`

Expected: `gpt-5.4` present, new timeout / prewarm settings absent.

**Step 3: Write minimal implementation**

- Change Graphiti-focused examples and local dev env files to `LLM_MODEL_NAME=gpt-5.4-mini`
- Add documented env vars for timeout and prewarm

**Step 4: Verify**

Run: `rg -n "LLM_MODEL_NAME=.*gpt-5.4-mini|GRAPHITI_REQUEST_TIMEOUT_SECONDS|GRAPHITI_PREWARM" .env .env.example graphiti_service/.env README.md`

Expected: new speed-oriented values present.

**Step 5: Commit**

```bash
git add README.md .env.example .env graphiti_service/.env
git commit -m "docs: update graphiti speed defaults"
```

### Task 2: Add backend timeout configuration with a failing test first

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/services/graphiti_sidecar_client.py`
- Test: `backend/tests/test_graph_backend_contract.py`

**Step 1: Write the failing test**

Add a test proving `GraphitiSidecarClient()` uses `Config.GRAPHITI_REQUEST_TIMEOUT_SECONDS` when no explicit timeout argument is passed.

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_graph_backend_contract.py -q`

Expected: FAIL because the client still hardcodes `30.0`.

**Step 3: Write minimal implementation**

- Add `GRAPHITI_REQUEST_TIMEOUT_SECONDS` to backend config
- Use that config value as the client default timeout

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_graph_backend_contract.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/config.py backend/app/services/graphiti_sidecar_client.py backend/tests/test_graph_backend_contract.py
git commit -m "feat: configure graphiti request timeout"
```

### Task 3: Add sidecar warmup with tests

**Files:**
- Modify: `graphiti_service/config.py`
- Modify: `graphiti_service/service.py`
- Modify: `graphiti_service/app.py`
- Test: `graphiti_service/tests/test_service.py`
- Test: `graphiti_service/tests/test_app.py`

**Step 1: Write the failing tests**

- Add a service test proving `warmup()` initializes Graphiti and forces a one-time embedding call
- Add an app test proving startup warmup runs only when `GRAPHITI_PREWARM` is enabled

**Step 2: Run tests to verify they fail**

Run: `cd graphiti_service && pytest tests/test_service.py tests/test_app.py -q`

Expected: FAIL because no warmup path exists yet.

**Step 3: Write minimal implementation**

- Add `GRAPHITI_PREWARM` config
- Add `GraphitiMemoryService.warmup()`
- Call warmup from app startup when enabled
- Log warmup failures without leaking secrets

**Step 4: Run tests to verify they pass**

Run: `cd graphiti_service && pytest tests/test_service.py tests/test_app.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add graphiti_service/config.py graphiti_service/service.py graphiti_service/app.py graphiti_service/tests/test_service.py graphiti_service/tests/test_app.py
git commit -m "feat: prewarm graphiti sidecar on startup"
```

### Task 4: Add lightweight timing instrumentation

**Files:**
- Modify: `graphiti_service/service.py`

**Step 1: Write the failing test**

No dedicated test required if the warmup and build-path tests stay green. This is logging-only behavior.

**Step 2: Verify current behavior lacks timing visibility**

Run: `rg -n "perf_counter|elapsed|duration|warmup complete|add_episodes completed" graphiti_service/service.py`

Expected: no relevant timing instrumentation.

**Step 3: Write minimal implementation**

Add timing logs for:

- Graphiti initialization
- embedding warmup
- per-episode ingestion
- whole `add_episodes` request

**Step 4: Verify**

Run: `rg -n "perf_counter|elapsed|duration|warmup complete|add_episodes completed" graphiti_service/service.py`

Expected: timing instrumentation present.

**Step 5: Commit**

```bash
git add graphiti_service/service.py
git commit -m "feat: instrument graphiti build latency"
```

### Task 5: Add a repeatable local benchmark script

**Files:**
- Create: `scripts/benchmark_graphiti_speed.py`
- Modify: `README.md`

**Step 1: Write the failing test**

No automated test. This is a local diagnostic utility.

**Step 2: Verify benchmark utility does not yet exist**

Run: `test -f scripts/benchmark_graphiti_speed.py`

Expected: exit code 1

**Step 3: Write minimal implementation**

Add a script that can:

- benchmark raw chat-completion latency for one or more models
- benchmark local `bge-m3` embedding latency
- benchmark sidecar graph ingestion latency using a text sample and ontology file

**Step 4: Verify**

Run: `python scripts/benchmark_graphiti_speed.py --help`

Expected: usage text prints successfully

**Step 5: Commit**

```bash
git add scripts/benchmark_graphiti_speed.py README.md
git commit -m "feat: add graphiti speed benchmark script"
```

### Task 6: Run verification and compare bottlenecks

**Files:**
- Use: `.env`
- Use: `graphiti_service/.env`
- Use: `backend/uploads/projects/proj_bd74486197c2/extracted_text.txt`
- Use: `backend/uploads/projects/proj_bd74486197c2/project.json`

**Step 1: Run focused automated tests**

Run: `cd backend && pytest tests/test_graph_backend_contract.py -q`

Expected: PASS

Run: `cd graphiti_service && pytest tests/test_service.py tests/test_app.py -q`

Expected: PASS

**Step 2: Run benchmark against both models**

Run: `python scripts/benchmark_graphiti_speed.py --models gpt-5.4 gpt-5.4-mini --text-file backend/uploads/projects/proj_bd74486197c2/extracted_text.txt --project-file backend/uploads/projects/proj_bd74486197c2/project.json`

Expected: structured output with direct LLM, embedding, and sidecar ingestion timings.

**Step 3: Record conclusion**

Summarize:

- model-to-model latency difference
- embedding latency
- sidecar ingestion latency
- whether the timeout fix alone solved the failure mode

**Step 4: Final verification**

Run any full targeted suites needed for changed files and report exact results before claiming success.
