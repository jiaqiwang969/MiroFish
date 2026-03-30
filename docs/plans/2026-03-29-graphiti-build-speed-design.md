# Graphiti Build Speed Design

**Date:** 2026-03-29

**Goal:** Reduce Graphiti graph-build latency enough to avoid backend timeouts and make local graph construction feel responsive, while keeping the current `Flask -> Graphiti sidecar -> Kuzu` architecture intact.

## Current Problem

The current graph build path is slow for three concrete reasons:

1. The backend waits only 30 seconds for a sidecar request, which is too short for real Graphiti ingestion workloads.
2. The sidecar cold-starts both Graphiti and the local `BAAI/bge-m3` embedding model on demand.
3. The sidecar currently uses `gpt-5.4`, which is functional but slower than necessary for extraction-heavy graph building.

The result is misleading failure behavior: the backend reports `timed out`, while the sidecar may still continue writing partial graph data.

## Constraints

- Keep the existing local deployment model.
- Keep `bge-m3` as the local embedding model.
- Do not redesign Graphiti ingestion internals in this pass.
- Optimize for speed first, accepting small quality loss.
- Avoid risky concurrency changes in the sidecar for now.

## Options Considered

### Option A: Minimal runtime optimization

- Switch sidecar extraction model to `gpt-5.4-mini`
- Make backend-to-sidecar timeout configurable and longer
- Add sidecar prewarm at startup
- Add timing logs and a repeatable benchmark script

**Pros:** Fastest path to measurable improvement with low code risk.

**Cons:** Does not fundamentally change Graphiti's serial ingestion model.

### Option B: Aggressive quality-for-speed tradeoff

Everything in Option A, plus disable reranking / cross-encoder work inside Graphiti initialization.

**Pros:** Likely faster search and possibly lower sidecar overhead.

**Cons:** Larger retrieval-quality regression and less confidence about side effects on downstream graph usage.

### Option C: Architectural rewrite

Move ingestion off the request path or redesign batching / concurrency.

**Pros:** Best long-term scalability.

**Cons:** Too large for the current objective and unnecessary before measuring simpler fixes.

## Chosen Approach

Use **Option A**.

This is the highest-value change set because it directly addresses the observed timeout failure mode, removes cold-start penalties, and gives us the measurement needed to distinguish between LLM latency, embedding latency, and Graphiti orchestration latency.

## Design

### 1. Faster default extraction model

Change the local Graphiti sidecar default runtime recommendation from `gpt-5.4` to `gpt-5.4-mini`.

This change should affect:

- `graphiti_service` runtime defaults
- local example configuration
- local checked-in dev env files in this worktree, without exposing secrets

The model must remain configurable through `LLM_MODEL_NAME`.

### 2. Configurable backend timeout

Add a backend config value such as `GRAPHITI_REQUEST_TIMEOUT_SECONDS`.

This timeout applies to the backend HTTP client talking to the local Graphiti sidecar. It should default to a value suitable for graph ingestion workloads rather than generic API calls.

This ensures slow-but-valid graph builds are treated as long-running work instead of immediate failure.

### 3. Sidecar prewarm

Add a `warmup()` method to `GraphitiMemoryService` that:

- initializes the Graphiti stack
- triggers the local sentence-transformer model to load once

Call this warmup during sidecar startup when enabled by config. If warmup fails, log the failure but keep the service bootable so the error is visible without crashing the process unnecessarily.

### 4. Timing instrumentation

Add lightweight timing logs around:

- sidecar Graphiti initialization
- embedding model warmup
- each `add_episode` call
- total `add_episodes` request duration

This is enough to tell whether the dominant latency comes from remote LLM calls, embedding, or Graphiti orchestration / storage.

### 5. Benchmark path

Add a small benchmark script that can measure:

- raw chat-completion latency for `gpt-5.4`
- raw chat-completion latency for `gpt-5.4-mini`
- local `bge-m3` embedding latency
- sidecar `/episodes` request latency against the current sample project

The benchmark does not need to be production-grade. It only needs to be repeatable and safe to run locally.

## Error Handling

- A slow sidecar call should no longer fail at 30 seconds by default.
- Warmup errors should be logged clearly and surfaced in benchmark / test runs.
- Timing logs must not include API keys or sensitive payloads.

## Testing Strategy

- Backend unit test for configurable timeout propagation.
- Sidecar service unit test for warmup behavior.
- Sidecar app test proving startup warmup is triggered only when enabled.
- Focused benchmark runs after implementation:
  - `gpt-5.4`
  - `gpt-5.4-mini`
  - local embedding
  - sidecar ingestion

## Expected Outcome

- The backend stops falsely marking valid builds as failed due to a 30-second client timeout.
- First graph build becomes noticeably faster after sidecar startup.
- `gpt-5.4-mini` should reduce extraction latency enough that the remaining bottleneck becomes observable rather than guessed.
