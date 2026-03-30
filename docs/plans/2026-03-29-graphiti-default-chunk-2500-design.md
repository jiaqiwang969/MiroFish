# Graphiti Default Chunk 2500 Design

**Date:** 2026-03-29

**Goal:** Reduce Graphiti graph-build wall time further by raising the default chunk settings from `1000/100` to `2500/250` for new builds.

## Context

The current local Graphiti path is bottlenecked by LLM extraction inside the sidecar `POST /episodes` flow. Real A/B runs on the same project showed:

- `1000/100`: about `658s`, `9` chunks, `205` nodes, `249` edges
- `1500/150`: about `361s`, `5` chunks, `128` nodes, `154` edges
- `2000/200`: about `352s`, `4` chunks, `140` nodes, `144` edges
- `2500/250`: about `196s`, `3` chunks, `73` nodes, `84` edges

This is a speed-first tradeoff. The graph becomes sparser, but the build time drops by about `70%` relative to `1000/100`.

## Options

### Option A: Keep `1000/100`

- Pros: Better graph density
- Cons: Too slow for the user's priority

### Option B: Change defaults to `2000/200`

- Pros: Similar runtime to `1500/150` while preserving a denser graph
- Cons: Not a large enough speed jump for a speed-first target

### Option C: Change defaults to `2500/250`

- Pros: Largest measured runtime win without changing the architecture
- Cons: Stronger graph sparsity tradeoff

### Option D: Keep defaults and require manual overrides

- Pros: No behavior change for existing users
- Cons: Speed benefit is hidden behind per-run tuning

## Chosen Approach

Use **Option C**.

The user explicitly prioritized speed over graph richness, and the measured runtime gain is large enough to justify making `2500/250` the new default for fresh Graphiti builds.

## Design

### 1. Default values

Update the backend defaults from `1000/100` to `2500/250` in the config layer and in any remaining hard-coded text splitting helpers.

### 2. Persistence and API behavior

Keep the existing request format unchanged. `/api/graph/build` should continue to accept explicit `chunk_size` and `chunk_overlap`, while new projects and builds without overrides should persist the new defaults automatically.

### 3. Documentation

Document the new defaults in a fresh plan file for this tuning step. Historical plan files for the earlier `1000/100` move can stay as historical records.

### 4. Testing

Lock the new defaults with focused backend tests:

- config defaults
- project default persistence
- graph build API default persistence
- Graphiti builder regression surface
