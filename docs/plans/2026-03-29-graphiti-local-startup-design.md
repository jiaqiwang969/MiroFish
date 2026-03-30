# Graphiti Local Startup Design

**Date:** 2026-03-29

**Goal:** Add a one-command local startup path for the new `Graphiti sidecar + backend + frontend` development workflow without breaking the existing `dev` script used by legacy Zep users.

## Scope

- Add a dedicated local setup command for the `graphiti_service` Python environment.
- Add a dedicated one-command startup entrypoint for Graphiti local mode.
- Keep the current `npm run dev` behavior unchanged.
- Update docs so the default local path matches the real process requirements.

## Non-Goals

- Do not redesign Docker deployment in this change.
- Do not remove Zep compatibility scripts.
- Do not change backend or sidecar runtime behavior.
- Do not bundle process supervision beyond the existing `concurrently`-based local workflow.

## Current Problem

The repository now supports local Graphiti mode, but the developer ergonomics are still inconsistent:

- `npm run dev` only starts backend and frontend.
- `graphiti_service` must currently be started in a separate terminal.
- `npm run setup:all` does not install the Graphiti sidecar environment.
- README already recommends Graphiti local mode, so the scripts should support that recommendation directly.

## Recommended Approach

Use additive npm scripts at the repository root:

- `setup:graphiti` installs the Graphiti sidecar dependencies with `uv sync`.
- `graphiti` starts the sidecar service.
- `dev:graphiti` starts sidecar, backend, and frontend together through `concurrently`.

This keeps legacy behavior stable:

- `dev` remains the old backend + frontend path.
- Graphiti local users opt into `dev:graphiti`.

## Alternatives Considered

### 1. Replace `npm run dev` directly

This would make the default local path simpler, but it risks breaking any existing Zep-based workflow or documentation that still expects the old two-process startup behavior.

### 2. Add shell scripts instead of npm scripts

This would work, but it adds one more tool surface to remember and duplicates process management logic that already exists in `package.json`.

### 3. Add only docs, not scripts

This is the lowest-risk option but leaves the actual usability problem unsolved.

## Target Developer Experience

After this change, the expected Graphiti local workflow becomes:

1. `cp .env.example .env`
2. `cp graphiti_service/.env.example graphiti_service/.env`
3. `npm run setup:all`
4. `npm run dev:graphiti`

## Files To Change

- Modify `package.json`
- Modify `README.md`

## Validation

- Verify root `package.json` exposes `setup:graphiti`, `graphiti`, and `dev:graphiti`.
- Verify `setup:all` now includes the Graphiti sidecar environment.
- Verify `npm run dev:graphiti` starts all three local services successfully.
- Verify README examples match the script names and real startup order.
