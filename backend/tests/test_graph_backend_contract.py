from app.services.graph_backend import (
    GraphBackendEdge,
    GraphBackendNode,
    GraphitiGraphBackend,
    get_graph_backend,
)
from app.services.graphiti_sidecar_client import GraphitiSidecarClient


class DummyConfig:
    GRAPH_BACKEND = "graphiti"
    GRAPHITI_SERVICE_URL = "http://127.0.0.1:8011"


class RecordingClient:
    def __init__(self):
        self.created_graphs = []
        self.ontologies = []
        self.episode_calls = []

    def create_graph(self, name, description):
        self.created_graphs.append((name, description))
        return {"graph_id": "graph-001"}

    def set_ontology(self, graph_id, ontology):
        self.ontologies.append((graph_id, ontology))

    def add_episodes(self, graph_id, episodes):
        self.episode_calls.append((graph_id, episodes))
        return ["episode-001"]

    def get_nodes(self, graph_id):
        assert graph_id == "graph-001"
        return [
            {
                "uuid": "node-001",
                "name": "Alice",
                "labels": ["Entity", "Person"],
                "summary": None,
                "attributes": None,
            }
        ]

    def get_edges(self, graph_id):
        assert graph_id == "graph-001"
        return [
            {
                "uuid": "edge-001",
                "name": "knows",
                "fact": "Alice knows Bob",
                "source_node_uuid": "node-001",
                "target_node_uuid": "node-002",
                "attributes": None,
            }
        ]


def test_get_graph_backend_returns_graphiti_sidecar_backend():
    backend = get_graph_backend(config=DummyConfig, client=RecordingClient())

    assert isinstance(backend, GraphitiGraphBackend)


def test_graphiti_sidecar_client_posts_create_graph_payload():
    calls = []

    def fake_transport(method, url, payload, timeout):
        calls.append(
            {
                "method": method,
                "url": url,
                "payload": payload,
                "timeout": timeout,
            }
        )
        return 200, {"graph_id": "graph-001"}

    client = GraphitiSidecarClient(
        base_url="http://127.0.0.1:8011",
        transport=fake_transport,
        timeout=12.5,
    )

    result = client.create_graph(
        name="Campus Graph",
        description="MiroFish Social Simulation Graph",
    )

    assert result == {"graph_id": "graph-001"}
    assert calls == [
        {
            "method": "POST",
            "url": "http://127.0.0.1:8011/graphs",
            "payload": {
                "name": "Campus Graph",
                "description": "MiroFish Social Simulation Graph",
            },
            "timeout": 12.5,
        }
    ]


def test_graphiti_sidecar_client_uses_configured_default_timeout(monkeypatch):
    calls = []

    def fake_transport(method, url, payload, timeout):
        calls.append(timeout)
        return 200, {"graph_id": "graph-001"}

    monkeypatch.setattr(
        "app.services.graphiti_sidecar_client.Config.GRAPHITI_REQUEST_TIMEOUT_SECONDS",
        88.0,
        raising=False,
    )

    client = GraphitiSidecarClient(
        base_url="http://127.0.0.1:8011",
        transport=fake_transport,
    )

    client.create_graph(
        name="Campus Graph",
        description="MiroFish Social Simulation Graph",
    )

    assert calls == [88.0]


def test_graphiti_backend_normalizes_nodes_and_edges():
    backend = GraphitiGraphBackend(client=RecordingClient())

    nodes = backend.list_nodes("graph-001")
    edges = backend.list_edges("graph-001")

    assert nodes == [
        GraphBackendNode(
            uuid="node-001",
            name="Alice",
            labels=["Entity", "Person"],
            summary="",
            attributes={},
        )
    ]
    assert edges == [
        GraphBackendEdge(
            uuid="edge-001",
            name="knows",
            fact="Alice knows Bob",
            source_node_uuid="node-001",
            target_node_uuid="node-002",
            attributes={},
        )
    ]


def test_graphiti_backend_appends_runtime_episode_through_sidecar():
    client = RecordingClient()
    backend = GraphitiGraphBackend(client=client)

    episode_id = backend.append_episode(
        graph_id="graph-001",
        content="Alice posted a new update about the campus event.",
        source="simulation_runtime",
        metadata={"agent_id": "alice"},
    )

    assert episode_id == "episode-001"
    assert client.episode_calls == [
        (
            "graph-001",
            [
                {
                    "content": "Alice posted a new update about the campus event.",
                    "source": "simulation_runtime",
                    "metadata": {"agent_id": "alice"},
                }
            ],
        )
    ]
