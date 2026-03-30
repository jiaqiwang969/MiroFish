"""
Graphiti sidecar service implementation.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import Config
from graphiti_core.llm_client.config import DEFAULT_MAX_TOKENS, ModelSize
from graphiti_core.llm_client.openai_generic_client import DEFAULT_MODEL, OpenAIGenericClient
from graphiti_core.prompts.models import Message
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel


logger = logging.getLogger(__name__)


class OpenAICompatibleGraphitiClient(OpenAIGenericClient):
    """OpenAI-compatible client with stricter JSON schema emission."""

    @staticmethod
    def _close_object_schemas(schema: Any) -> Any:
        if isinstance(schema, dict):
            normalized = {
                key: OpenAICompatibleGraphitiClient._close_object_schemas(value)
                for key, value in schema.items()
            }
            if normalized.get("type") == "object":
                normalized.setdefault("additionalProperties", False)
                properties = normalized.get("properties")
                if isinstance(properties, dict):
                    normalized["required"] = list(properties.keys())
            return normalized

        if isinstance(schema, list):
            return [OpenAICompatibleGraphitiClient._close_object_schemas(item) for item in schema]

        return schema

    async def _generate_response(
        self,
        messages: list[Message],
        response_model: type[BaseModel] | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        model_size: ModelSize = ModelSize.medium,
    ) -> dict[str, Any]:
        openai_messages: list[ChatCompletionMessageParam] = []
        for message in messages:
            message.content = self._clean_input(message.content)
            if message.role == "user":
                openai_messages.append({"role": "user", "content": message.content})
            elif message.role == "system":
                openai_messages.append({"role": "system", "content": message.content})

        response_format: dict[str, Any] = {"type": "json_object"}
        if response_model is not None:
            schema_name = getattr(response_model, "__name__", "structured_response")
            json_schema = self._close_object_schemas(response_model.model_json_schema())
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "schema": json_schema,
                    "strict": True,
                },
            }

        response = await self.client.chat.completions.create(
            model=self.model or DEFAULT_MODEL,
            messages=openai_messages,
            temperature=self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            response_format=response_format,
        )
        result = response.choices[0].message.content or ""
        return json.loads(result)


class GraphitiMemoryService:
    """Local Graphiti service wrapper with graph metadata persistence."""

    def __init__(self, config: type[Config] = Config):
        self.config = config
        self._graphiti = None
        self._embedder = None
        self._async_resources: list[Any] = []
        self._graphiti_lock = threading.Lock()
        self._metadata_lock = threading.Lock()
        self._async_runtime_lock = threading.Lock()
        self._async_loop: asyncio.AbstractEventLoop | None = None
        self._async_loop_thread: threading.Thread | None = None

        os.makedirs(os.path.dirname(self.config.GRAPHITI_DB_PATH), exist_ok=True)
        os.makedirs(os.path.dirname(self.config.GRAPHITI_METADATA_PATH), exist_ok=True)
        self._ensure_metadata_file()
        self._recover_stale_wal_if_needed()

    def close(self) -> None:
        loop: asyncio.AbstractEventLoop | None = None
        thread: threading.Thread | None = None

        with self._async_runtime_lock:
            if self._async_loop is not None and self._async_loop_thread is not None:
                loop = self._async_loop
                thread = self._async_loop_thread
            self._async_loop = None
            self._async_loop_thread = None

        try:
            if loop is not None and thread is not None and thread.is_alive():
                try:
                    future = asyncio.run_coroutine_threadsafe(
                        self._close_async_resources(),
                        loop,
                    )
                    future.result(timeout=10)
                finally:
                    loop.call_soon_threadsafe(loop.stop)
                    thread.join(timeout=10)
        finally:
            self._graphiti = None
            self._embedder = None
            self._async_resources = []

    def create_graph(self, name: str, description: str) -> Dict[str, Any]:
        graph_id = f"mirofish_{uuid.uuid4().hex[:16]}"
        metadata = self._load_metadata()
        metadata[graph_id] = {
            "graph_id": graph_id,
            "name": name,
            "description": description,
            "ontology": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save_metadata(metadata)
        return {"graph_id": graph_id}

    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]) -> None:
        metadata = self._load_metadata()
        graph = metadata.get(graph_id)
        if not graph:
            raise KeyError(f"图谱不存在: {graph_id}")
        graph["ontology"] = ontology
        self._save_metadata(metadata)

    def add_episodes(self, graph_id: str, episodes: List[Dict[str, Any]]) -> List[str]:
        metadata = self._load_metadata()
        graph = metadata.get(graph_id)
        if not graph:
            raise KeyError(f"图谱不存在: {graph_id}")

        request_started_at = time.perf_counter()
        graphiti = self._get_graphiti()
        self._bind_graph_driver(graphiti, graph_id)
        ontology = graph.get("ontology") or {}
        entity_types, edge_types, edge_type_map = self._build_ontology_models(ontology)

        episode_ids = []
        previous_episode_uuid = None
        for index, episode in enumerate(episodes, start=1):
            content = (episode.get("content") or "").strip()
            if not content:
                continue

            episode_started_at = time.perf_counter()
            result = self._run_async(
                graphiti.add_episode(
                    name=f"{graph_id}-episode-{index}",
                    episode_body=content,
                    source_description=episode.get("source", "text"),
                    reference_time=datetime.now(timezone.utc),
                    source=self._map_episode_source(episode.get("source")),
                    group_id=graph_id,
                    entity_types=entity_types or None,
                    edge_types=edge_types or None,
                    edge_type_map=edge_type_map or None,
                    previous_episode_uuids=[previous_episode_uuid] if previous_episode_uuid else None,
                )
            )

            logger.info(
                "Graphiti add_episode completed",
                extra={
                    "graph_id": graph_id,
                    "episode_index": index,
                    "elapsed_seconds": round(time.perf_counter() - episode_started_at, 3),
                },
            )
            previous_episode_uuid = result.episode.uuid
            episode_ids.append(result.episode.uuid)

        logger.info(
            "Graphiti add_episodes completed",
            extra={
                "graph_id": graph_id,
                "episode_count": len(episode_ids),
                "elapsed_seconds": round(time.perf_counter() - request_started_at, 3),
            },
        )
        if episode_ids:
            self._checkpoint_graphiti(graphiti)
        return episode_ids

    def get_graph_summary(self, graph_id: str) -> Dict[str, Any]:
        nodes = self.list_nodes(graph_id)
        edges = self.list_edges(graph_id)
        return {
            "graph_id": graph_id,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    def list_nodes(self, graph_id: str) -> List[Dict[str, Any]]:
        graphiti = self._get_graphiti()
        entity_node_cls = self._graphiti_imports()["EntityNode"]
        nodes = self._run_async(entity_node_cls.get_by_group_ids(graphiti.driver, [graph_id]))
        return [self._normalize_node(node) for node in nodes]

    def list_edges(self, graph_id: str) -> List[Dict[str, Any]]:
        graphiti = self._get_graphiti()
        entity_edge_cls = self._graphiti_imports()["EntityEdge"]
        try:
            edges = self._run_async(entity_edge_cls.get_by_group_ids(graphiti.driver, [graph_id]))
        except Exception:
            edges = []
        return [self._normalize_edge(edge) for edge in edges]

    def delete_graph(self, graph_id: str) -> None:
        graphiti = self._get_graphiti()
        imports = self._graphiti_imports()
        self._bind_graph_driver(graphiti, graph_id)
        self._run_async(imports["EntityNode"].delete_by_group_id(graphiti.driver, graph_id))
        self._run_async(imports["EpisodicNode"].delete_by_group_id(graphiti.driver, graph_id))

        metadata = self._load_metadata()
        if graph_id in metadata:
            del metadata[graph_id]
            self._save_metadata(metadata)

    def warmup(self) -> Dict[str, Any]:
        graphiti_started_at = time.perf_counter()
        self._get_graphiti()
        graphiti_elapsed = time.perf_counter() - graphiti_started_at

        embedder_warmed = False
        embedder_elapsed = 0.0
        if self._embedder is not None:
            embedder_started_at = time.perf_counter()
            self._run_async(self._embedder.create("graphiti warmup"))
            embedder_elapsed = time.perf_counter() - embedder_started_at
            embedder_warmed = True

        result = {
            "graphiti_init_seconds": round(graphiti_elapsed, 3),
            "embedder_warmup_seconds": round(embedder_elapsed, 3),
            "embedder_warmed": embedder_warmed,
        }
        logger.info("Graphiti warmup completed", extra=result)
        return result

    def _get_graphiti(self):
        if self._graphiti is not None:
            return self._graphiti

        with self._graphiti_lock:
            if self._graphiti is not None:
                return self._graphiti

            init_started_at = time.perf_counter()
            imports = self._graphiti_imports()
            driver = imports["KuzuDriver"](db=self.config.GRAPHITI_DB_PATH)
            llm_config = imports["LLMConfig"](
                api_key=self.config.LLM_API_KEY,
                base_url=self.config.LLM_BASE_URL,
                model=self.config.LLM_MODEL_NAME,
            )
            llm_client = self._build_llm_client(imports, llm_config)
            reranker = imports["OpenAIRerankerClient"](
                config=llm_config
            )
            embedder = self._build_embedder()
            self._embedder = embedder
            self._async_resources = [
                resource
                for resource in (
                    getattr(llm_client, "client", None),
                    getattr(reranker, "client", None),
                    getattr(driver, "close", None) and driver,
                )
                if resource is not None
            ]
            graphiti = imports["Graphiti"](
                graph_driver=driver,
                llm_client=llm_client,
                embedder=embedder,
                cross_encoder=reranker,
            )
            self._run_async(graphiti.build_indices_and_constraints())
            self._ensure_kuzu_fulltext_indices(graphiti)
            self._graphiti = graphiti
            logger.info(
                "Graphiti initialized",
                extra={
                    "elapsed_seconds": round(time.perf_counter() - init_started_at, 3),
                    "embedding_model": self.config.GRAPHITI_EMBEDDING_MODEL,
                    "llm_model": self.config.LLM_MODEL_NAME,
                },
            )

        return self._graphiti

    @staticmethod
    def _build_llm_client(imports: Dict[str, Any], llm_config: Any):
        client_cls = imports["OpenAIGenericClient"]
        if client_cls is OpenAIGenericClient:
            return OpenAICompatibleGraphitiClient(config=llm_config)
        return client_cls(config=llm_config)

    def _build_embedder(self):
        sentence_transformer_cls = self._sentence_transformer_class()
        embedder_client_cls = self._graphiti_imports()["EmbedderClient"]
        model_name = self.config.GRAPHITI_EMBEDDING_MODEL

        class LocalSentenceTransformerEmbedder(embedder_client_cls):
            def __init__(self):
                self._model = None
                self._lock = threading.Lock()

            def _get_model(self):
                if self._model is not None:
                    return self._model

                with self._lock:
                    if self._model is None:
                        self._model = sentence_transformer_cls(model_name)
                return self._model

            async def create(self, input_data):
                if isinstance(input_data, str):
                    vectors = self._get_model().encode(
                        [input_data],
                        normalize_embeddings=True,
                    )
                    return vectors[0].tolist()

                if isinstance(input_data, list) and all(isinstance(item, str) for item in input_data):
                    vectors = self._get_model().encode(
                        input_data,
                        normalize_embeddings=True,
                    )
                    return vectors[0].tolist()

                raise TypeError("LocalSentenceTransformerEmbedder 仅支持字符串输入")

            async def create_batch(self, input_data_list: list[str]) -> list[list[float]]:
                vectors = self._get_model().encode(
                    input_data_list,
                    normalize_embeddings=True,
                )
                return [vector.tolist() for vector in vectors]

        return LocalSentenceTransformerEmbedder()

    @staticmethod
    def _bind_graph_driver(graphiti: Any, graph_id: str) -> None:
        """
        Graphiti 0.28.2 的 Kuzu 分支会读取 driver._database 来判断是否要 clone driver，
        但内置 KuzuDriver 没有初始化这个属性。这里显式对齐当前 graph_id，避免触发
        不适用于 Kuzu 单库模式的多-database 分支。
        """
        setattr(graphiti.driver, "_database", graph_id)
        if hasattr(graphiti, "clients") and getattr(graphiti.clients, "driver", None) is not None:
            setattr(graphiti.clients.driver, "_database", graph_id)

    def _ensure_kuzu_fulltext_indices(self, graphiti: Any) -> None:
        from graphiti_core.driver.driver import GraphProvider
        from graphiti_core.graph_queries import get_fulltext_indices

        driver = getattr(graphiti, "driver", None)
        if driver is None:
            return

        if getattr(driver, "provider", None) != GraphProvider.KUZU:
            return

        index_specs = [
            ("Episodic", "episode_content"),
            ("Entity", "node_name_and_summary"),
            ("Community", "community_name"),
            ("RelatesToNode_", "edge_name_and_fact"),
        ]

        for (label, index_name), create_query in zip(
            index_specs, get_fulltext_indices(GraphProvider.KUZU)
        ):
            if self._kuzu_fulltext_index_exists(driver, label, index_name):
                continue
            self._run_async(driver.execute_query(create_query))

    def _kuzu_fulltext_index_exists(self, driver: Any, label: str, index_name: str) -> bool:
        probe_query = (
            f"CALL QUERY_FTS_INDEX('{label}', '{index_name}', '__graphiti_init_probe__', TOP := 1)"
            " RETURN *;"
        )
        try:
            self._run_async(driver.execute_query(probe_query))
            return True
        except Exception as exc:
            if "doesn't have an index" in str(exc):
                return False
            raise

    @staticmethod
    def _sentence_transformer_class():
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer

    @staticmethod
    def _graphiti_imports() -> Dict[str, Any]:
        from pydantic import BaseModel, Field, create_model
        from graphiti_core import Graphiti
        from graphiti_core.driver.kuzu_driver import KuzuDriver
        from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
        from graphiti_core.embedder.client import EmbedderClient
        from graphiti_core.edges import EntityEdge
        from graphiti_core.llm_client.config import LLMConfig
        from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
        from graphiti_core.nodes import EntityNode, EpisodicNode, EpisodeType

        return {
            "BaseModel": BaseModel,
            "Field": Field,
            "Graphiti": Graphiti,
            "KuzuDriver": KuzuDriver,
            "OpenAIRerankerClient": OpenAIRerankerClient,
            "EmbedderClient": EmbedderClient,
            "EntityNode": EntityNode,
            "EntityEdge": EntityEdge,
            "EpisodicNode": EpisodicNode,
            "EpisodeType": EpisodeType,
            "LLMConfig": LLMConfig,
            "OpenAIGenericClient": OpenAIGenericClient,
            "create_model": create_model,
        }

    def _build_ontology_models(self, ontology: Dict[str, Any]):
        imports = self._graphiti_imports()
        base_model = imports["BaseModel"]
        field = imports["Field"]
        create_model = imports["create_model"]

        entity_types = {}
        for entity_def in ontology.get("entity_types", []):
            entity_name = entity_def.get("name")
            if not entity_name:
                continue
            entity_types[entity_name] = create_model(
                entity_name,
                __base__=base_model,
                __doc__=entity_def.get("description") or entity_name,
                description=(str, field(default=entity_def.get("description") or entity_name)),
            )

        edge_types = {}
        edge_type_map = {}
        for edge_def in ontology.get("edge_types", []):
            edge_name = edge_def.get("name")
            if not edge_name:
                continue

            edge_types[edge_name] = create_model(
                edge_name,
                __base__=base_model,
                __doc__=edge_def.get("description") or edge_name,
                fact=(str, field(default=edge_def.get("description") or edge_name)),
            )

            for source_target in edge_def.get("source_targets", []):
                key = (
                    source_target.get("source", "Entity"),
                    source_target.get("target", "Entity"),
                )
                edge_type_map.setdefault(key, []).append(edge_name)

        return entity_types, edge_types, edge_type_map

    @staticmethod
    def _map_episode_source(source: Optional[str]):
        episode_type = GraphitiMemoryService._graphiti_imports()["EpisodeType"]
        if source == "text":
            return episode_type.text
        if source == "json":
            return episode_type.json
        return episode_type.message

    @staticmethod
    def _normalize_node(node: Any) -> Dict[str, Any]:
        return {
            "uuid": getattr(node, "uuid", ""),
            "name": getattr(node, "name", "") or "",
            "labels": list(getattr(node, "labels", []) or []),
            "summary": getattr(node, "summary", "") or "",
            "attributes": dict(getattr(node, "attributes", {}) or {}),
        }

    @staticmethod
    def _normalize_edge(edge: Any) -> Dict[str, Any]:
        return {
            "uuid": getattr(edge, "uuid", ""),
            "name": getattr(edge, "name", "") or "",
            "fact": getattr(edge, "fact", "") or "",
            "source_node_uuid": getattr(edge, "source_node_uuid", "") or "",
            "target_node_uuid": getattr(edge, "target_node_uuid", "") or "",
            "attributes": dict(getattr(edge, "attributes", {}) or {}),
        }

    def _run_async(self, coro):
        try:
            loop = self._ensure_async_runtime()
            future = asyncio.run_coroutine_threadsafe(coro, loop)
        except Exception:
            close = getattr(coro, "close", None)
            if callable(close):
                close()
            raise

        return future.result()

    def _ensure_async_runtime(self) -> asyncio.AbstractEventLoop:
        loop = self._async_loop
        thread = self._async_loop_thread
        if loop is not None and thread is not None and thread.is_alive():
            return loop

        with self._async_runtime_lock:
            loop = self._async_loop
            thread = self._async_loop_thread
            if loop is not None and thread is not None and thread.is_alive():
                return loop

            ready = threading.Event()
            holder: dict[str, asyncio.AbstractEventLoop] = {}

            def run_loop() -> None:
                event_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(event_loop)
                holder["loop"] = event_loop
                ready.set()
                event_loop.run_forever()

                pending = asyncio.all_tasks(event_loop)
                for task in pending:
                    task.cancel()
                if pending:
                    event_loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
                event_loop.run_until_complete(event_loop.shutdown_asyncgens())
                event_loop.close()

            thread = threading.Thread(
                target=run_loop,
                name="graphiti-async-runtime",
                daemon=True,
            )
            thread.start()
            if not ready.wait(timeout=5):
                raise RuntimeError("Graphiti async runtime failed to start")

            loop = holder["loop"]
            self._async_loop = loop
            self._async_loop_thread = thread
            return loop

    async def _close_async_resources(self) -> None:
        seen_ids = set()
        for resource in self._async_resources:
            resource_id = id(resource)
            if resource_id in seen_ids:
                continue
            seen_ids.add(resource_id)

            close = getattr(resource, "close", None)
            if not callable(close):
                continue

            result = close()
            if inspect.isawaitable(result):
                await result

    def _checkpoint_graphiti(self, graphiti: Any) -> None:
        if not getattr(self.config, "GRAPHITI_CHECKPOINT_AFTER_WRITE", True):
            return

        driver = getattr(graphiti, "driver", None)
        if driver is None:
            return

        execute_query = getattr(driver, "execute_query", None)
        if not callable(execute_query):
            return

        self._run_async(execute_query("CHECKPOINT;"))

    def _recover_stale_wal_if_needed(self) -> None:
        if not getattr(self.config, "GRAPHITI_RECOVER_STALE_WAL", True):
            return

        wal_path = Path(f"{self.config.GRAPHITI_DB_PATH}.wal")
        if not wal_path.exists():
            return

        recovered_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = wal_path.with_name(f"{wal_path.name}.stale-{recovered_at}")
        wal_path.replace(backup_path)
        logger.warning(
            "Recovered stale Graphiti WAL before Kuzu startup",
            extra={
                "wal_path": str(wal_path),
                "backup_path": str(backup_path),
            },
        )

    def _ensure_metadata_file(self) -> None:
        if not os.path.exists(self.config.GRAPHITI_METADATA_PATH):
            with open(self.config.GRAPHITI_METADATA_PATH, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)

    def _load_metadata(self) -> Dict[str, Any]:
        with self._metadata_lock:
            with open(self.config.GRAPHITI_METADATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)

    def _save_metadata(self, metadata: Dict[str, Any]) -> None:
        with self._metadata_lock:
            with open(self.config.GRAPHITI_METADATA_PATH, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
