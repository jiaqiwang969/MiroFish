# Graphiti Default Mini 6500 Design

**Date:** 2026-03-29

**Goal:** Push the local Graphiti stack into a true speed-first "turbo" profile by making `gpt-5.4-mini + 6500/650` the default for fresh local builds.

## Context

The current default was already moved to `gpt-5.4-mini + 4000/400`, which produced a real end-to-end build time of about `65s` on the sample project.

The next speed test on the same runtime showed:

- `gpt-5.4-mini + 4000/400`: about `65s`, `54` nodes, `46` edges
- `gpt-5.4-mini + 6500/650`: about `20s`, `12` nodes, `12` edges

This is a very large latency win, but it also materially compresses graph density.

## Options

### Option A: Keep `4000/400` as the default

- Pros: better graph density than the turbo setting
- Cons: about 3x slower than the fastest measured path

### Option B: Move the default to `6500/650`

- Pros: fastest real local build path measured so far
- Cons: graph richness drops sharply

### Option C: Add a separate preset system

- Pros: explicit mode switching
- Cons: more product and API surface, not needed for the current speed-first goal

## Decision

Choose Option B.

The user repeatedly prioritized speed over graph richness. For this local workflow, the default should match the user's stated optimization target rather than the balanced tradeoff.

## Scope

Keep architecture unchanged. Only retune:

- backend chunk defaults from `4000/400` to `6500/650`
- file parser helper defaults
- API example comments
- tests and plan docs so the new turbo default is explicit
