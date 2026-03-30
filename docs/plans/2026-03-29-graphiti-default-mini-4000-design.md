# Graphiti Default Mini 4000 Design

**Date:** 2026-03-29

**Goal:** Make the local Graphiti stack default to the speed-first profile the user validated in real runs: `gpt-5.4-mini` plus `4000/400` chunking.

## Context

The current local runtime is already switched to `gpt-5.4-mini`, but backend code still persists `2500/250` as the default chunk settings for fresh projects and builds.

Measured speed-first results on the same sample project:

- `gpt-5.4 + 2500/250`: about `280s`, `120` nodes, `133` edges
- `gpt-5.4 + 4000/400`: about `145s`, `54` nodes, `64` edges
- `gpt-5.4-mini + 4000/400`: about `65s`, `54` nodes, `46` edges

The user explicitly prioritized speed over graph richness, so the fastest stable profile should become the default.

## Options

### Option A: Keep code defaults at `2500/250`, use request overrides

- Pros: no code default change
- Cons: every new project or manual rebuild has to remember the faster settings

### Option B: Switch only the model default to `gpt-5.4-mini`

- Pros: lower risk than changing chunk defaults
- Cons: backend still creates new projects with slower `2500/250`

### Option C: Make `gpt-5.4-mini + 4000/400` the default

- Pros: fastest path becomes the normal path for fresh local runs
- Cons: graph density drops versus smaller chunks

## Decision

Choose Option C.

Keep the architecture unchanged. Only retune defaults and tests:

- runtime model defaults stay on `gpt-5.4-mini`
- backend chunk defaults move from `2500/250` to `4000/400`
- API examples and tests align with the new defaults

## Validation

Verification should confirm:

- config defaults expose `4000/400`
- text splitting helper defaults expose `4000/400`
- project creation and `/api/graph/build` inherit the new defaults
- the live backend still completes a real graph build with the mini runtime
