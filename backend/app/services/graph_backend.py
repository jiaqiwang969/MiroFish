"""
Graph backend abstraction for Zep/Graphiti migration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol

from ..config import Config
from .graphiti_sidecar_client import GraphitiSidecarClient


@dataclass(eq=True)
class GraphBackendNode:
    uuid: str
    name: str
    labels: List[str]
    summary: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "labels": self.labels,
            "summary": self.summary,
            "attributes": self.attributes,
        }


@dataclass(eq=True)
class GraphBackendEdge:
    uuid: str
    name: str
    fact: str
    source_node_uuid: str
    target_node_uuid: str
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "fact": self.fact,
            "source_node_uuid": self.source_node_uuid,
            "target_node_uuid": self.target_node_uuid,
            "attributes": self.attributes,
        }


class GraphBackend(Protocol):
    def create_graph(self, name: str, description: str = "MiroFish Social Simulation Graph") -> str:
        ...

    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]) -> None:
        ...

    def add_episodes(self, graph_id: str, episodes: List[Dict[str, Any]]) -> List[str]:
        ...

    def append_episode(
        self,
        graph_id: str,
        content: str,
        source: str = "text",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        ...

    def list_nodes(self, graph_id: str) -> List[GraphBackendNode]:
        ...

    def list_edges(self, graph_id: str) -> List[GraphBackendEdge]:
        ...

    def get_graph_data(self, graph_id: str) -> Dict[str, Any]:
        ...

    def delete_graph(self, graph_id: str) -> None:
        ...


class GraphitiGraphBackend:
    """Graph backend implementation backed by the local Graphiti sidecar."""

    DEFAULT_DESCRIPTION = "MiroFish Social Simulation Graph"

    def __init__(
        self,
        client: Optional[GraphitiSidecarClient] = None,
        base_url: Optional[str] = None,
    ):
        self.client = client or GraphitiSidecarClient(base_url=base_url or Config.GRAPHITI_SERVICE_URL)

    def create_graph(
        self,
        name: str,
        description: str = DEFAULT_DESCRIPTION,
    ) -> str:
        response = self.client.create_graph(name=name, description=description)
        graph_id = response.get("graph_id")
        if not graph_id:
            raise ValueError("Graphiti sidecar 未返回 graph_id")
        return graph_id

    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]) -> None:
        self.client.set_ontology(graph_id=graph_id, ontology=ontology)

    def add_episodes(self, graph_id: str, episodes: List[Dict[str, Any]]) -> List[str]:
        return self.client.add_episodes(graph_id=graph_id, episodes=episodes)

    def append_episode(
        self,
        graph_id: str,
        content: str,
        source: str = "text",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        episode_ids = self.add_episodes(
            graph_id=graph_id,
            episodes=[
                {
                    "content": content,
                    "source": source,
                    "metadata": metadata or {},
                }
            ],
        )
        return episode_ids[0] if episode_ids else None

    def list_nodes(self, graph_id: str) -> List[GraphBackendNode]:
        return [self._normalize_node(node) for node in self.client.get_nodes(graph_id)]

    def list_edges(self, graph_id: str) -> List[GraphBackendEdge]:
        return [self._normalize_edge(edge) for edge in self.client.get_edges(graph_id)]

    def get_graph_data(self, graph_id: str) -> Dict[str, Any]:
        nodes = [node.to_dict() for node in self.list_nodes(graph_id)]
        node_names = {node["uuid"]: node["name"] for node in nodes}

        edges = []
        for edge in self.list_edges(graph_id):
            edge_data = edge.to_dict()
            edge_data["source_node_name"] = node_names.get(edge.source_node_uuid, "")
            edge_data["target_node_name"] = node_names.get(edge.target_node_uuid, "")
            edges.append(edge_data)

        return {
            "graph_id": graph_id,
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    def delete_graph(self, graph_id: str) -> None:
        self.client.delete_graph(graph_id)

    @staticmethod
    def _normalize_node(node: Dict[str, Any]) -> GraphBackendNode:
        return GraphBackendNode(
            uuid=node.get("uuid", ""),
            name=node.get("name", ""),
            labels=list(node.get("labels") or []),
            summary=node.get("summary") or "",
            attributes=dict(node.get("attributes") or {}),
        )

    @staticmethod
    def _normalize_edge(edge: Dict[str, Any]) -> GraphBackendEdge:
        return GraphBackendEdge(
            uuid=edge.get("uuid", ""),
            name=edge.get("name", ""),
            fact=edge.get("fact", ""),
            source_node_uuid=edge.get("source_node_uuid", ""),
            target_node_uuid=edge.get("target_node_uuid", ""),
            attributes=dict(edge.get("attributes") or {}),
        )


def get_graph_backend(
    config: Any = Config,
    client: Optional[GraphitiSidecarClient] = None,
) -> GraphBackend:
    backend_name = getattr(config, "GRAPH_BACKEND", "graphiti").lower()

    if backend_name == "graphiti":
        if client is not None:
            return GraphitiGraphBackend(client=client)
        return GraphitiGraphBackend(base_url=getattr(config, "GRAPHITI_SERVICE_URL", None))

    raise ValueError(f"GRAPH_BACKEND 不支持: {backend_name}")
