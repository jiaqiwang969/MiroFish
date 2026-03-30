# Graphiti Local Migration Design

**Date:** 2026-03-29

**Goal:** Replace the current `zep-cloud` dependency with a local `Graphiti sidecar + Kuzu + bge-m3` stack while keeping the existing Flask API and Vue UI behavior as stable as possible.

## Scope

- Keep the current frontend and HTTP API flow.
- Replace Zep-backed graph build, entity read, report retrieval, and simulation memory write-back with Graphiti-backed implementations exposed through a local sidecar service.
- Keep the LLM provider remote via the user's OpenAI-compatible endpoint and model `gpt-5.4`.
- Use a local embedded graph database inside the sidecar to avoid requiring Neo4j or a hosted graph service.

## Non-Goals

- Do not make the system fully offline in this migration. The primary LLM remains a remote API.
- Do not redesign the frontend workflow or report-writing prompts.
- Do not preserve exact Zep internals where Graphiti uses different primitives. The goal is feature parity at the app level, not SDK-level compatibility.
- Do not force `graphiti-core` into the same Python environment as the main Flask backend.

## Target Architecture

- **LLM provider:** OpenAI-compatible endpoint from environment variables.
- **Main backend:** existing Flask app, still running with `camel-oasis` and current backend dependencies.
- **Graph engine:** Graphiti Python library running in a separate local Python service.
- **Graph store:** local Kuzu database files owned by the sidecar service.
- **Embedding model:** local `bge-m3`, loaded by the sidecar service.
- **Application boundary:** a new internal graph backend abstraction in Flask that hides Zep/Graphiti specifics from routes and higher-level services and talks to the sidecar over HTTP.

## Constraint That Changed The Design

The original idea was to embed Graphiti directly into the current backend. That is not viable in this repository because:

- `camel-oasis` pins `neo4j==5.23.0`
- `graphiti-core` requires `neo4j>=5.26.0`

That dependency conflict makes a single shared Python environment unsatisfiable. The migration therefore uses two Python environments:

- the main app environment for Flask and OASIS
- a sidecar environment for Graphiti and Kuzu

## Design Decisions

### 1. Add an internal graph backend adapter

Current services import `zep_cloud` directly, which couples routes and report logic to one vendor SDK. The migration will add a narrow internal adapter layer in the main backend responsible for:

- graph creation and initialization
- ontology registration / label mapping
- document and episode ingestion
- node / edge enumeration
- search and fact retrieval
- runtime memory write-back

The rest of the backend will talk to this adapter instead of directly importing Zep or Graphiti. The adapter implementation for Graphiti will call the local sidecar API.

### 2. Keep current API contracts stable

The UI and most Flask routes should keep the same request/response shapes. Where Graphiti cannot reproduce a Zep field exactly, responses should be normalized into the current app-level DTOs such as `GraphInfo`, `EntityNode`, `SearchResult`, and related report payloads.

### 3. Use a local Graphiti sidecar with Kuzu for the first deployment target

Kuzu is embedded and avoids a separate database container. Running it inside a dedicated Graphiti sidecar keeps setup simple while isolating the incompatible dependency set from the main backend.

### 4. Use local embeddings without Ollama

The embedder will be local and lightweight enough to avoid Ollama. `bge-m3` is chosen because retrieval quality matters more here than the smallest possible footprint.

### 5. Keep a compatibility-oriented environment model

Current startup requires `ZEP_API_KEY`. Under the new split architecture:

- the main backend should validate:
  - `GRAPH_BACKEND=graphiti`
  - `GRAPHITI_SERVICE_URL`
  - `LLM_API_KEY`
  - `LLM_BASE_URL`
  - `LLM_MODEL_NAME=gpt-5.4`
- the Graphiti sidecar should validate:
  - `GRAPHITI_DB_PATH`
  - `GRAPHITI_EMBEDDING_MODEL=BAAI/bge-m3`
  - `LLM_API_KEY`
  - `LLM_BASE_URL`
  - `LLM_MODEL_NAME=gpt-5.4`

## Data Flow

### Graph build

1. Upload text and generate ontology as before.
2. Flask calls the sidecar to create a local Graphiti graph/session for the project.
3. Flask chunks text and sends batches to the sidecar as episodes/documents.
4. The sidecar writes into Kuzu and waits for Graphiti processing/indexing where required.
5. Flask reads graph stats from the sidecar and persists the graph identifier into project state.

### Simulation preparation

1. Read normalized nodes and edges from the graph backend.
2. Filter entities by labels/type exactly as the current app expects.
3. Feed the resulting entities into the OASIS profile/environment setup path.

### Simulation runtime memory update

1. Convert actions into natural-language activity descriptions as today.
2. Append them through the sidecar into Graphiti as new episodes.
3. Let Graphiti update graph memory incrementally.

### Report retrieval

1. Translate existing report tool calls into Graphiti search/traversal calls.
2. Normalize returned facts, nodes, and relationships into current result objects.
3. Keep the report agent prompts and multi-step tool workflow stable.

## Sidecar API Surface

The first sidecar version only needs a narrow internal API:

- `POST /graphs` create graph
- `POST /graphs/{graph_id}/ontology` register ontology metadata needed by the adapter
- `POST /graphs/{graph_id}/episodes` ingest document or runtime episodes
- `GET /graphs/{graph_id}` return graph statistics
- `GET /graphs/{graph_id}/nodes` list normalized nodes
- `GET /graphs/{graph_id}/edges` list normalized edges
- `POST /graphs/{graph_id}/search` run report-time retrieval
- `DELETE /graphs/{graph_id}` delete graph data

## Error Handling

- Configuration errors must fail fast at startup with actionable messages.
- Sidecar unavailability should fail fast with an explicit local-service error.
- Graphiti backend failures should be surfaced through current task status/reporting mechanisms instead of raw stack traces where possible.
- Missing local model/database state should produce explicit setup instructions.
- Search and traversal failures in report generation should degrade gracefully to partial context instead of aborting the whole report.

## Testing Strategy

- Add backend unit/integration tests around the new graph backend abstraction.
- Cover config validation changes for both the main backend and the sidecar.
- Cover sidecar HTTP client error mapping.
- Cover graph build ingestion with a small fixture text.
- Cover entity listing normalization.
- Cover runtime memory update ingestion.
- Cover report retrieval normalization on a small local graph.

## Risks

- Graphiti's Python API is not shaped like `zep-cloud`, so some service logic will need real refactoring, not a thin import swap.
- The sidecar adds one more local process to manage, so startup scripts and docs must be explicit.
- Local `bge-m3` embeddings increase first-run setup time and disk usage.
- Search quality may differ from Zep Cloud; report prompts may need small follow-up tuning after parity is reached.

## Rollout

1. Introduce the graph backend abstraction and sidecar client configuration.
2. Create the Graphiti sidecar project with its own environment and Kuzu storage.
3. Migrate graph build and entity read paths first.
4. Migrate simulation write-back.
5. Migrate report tools last.
6. Remove `zep-cloud` dependency only after Graphiti paths pass verification.
