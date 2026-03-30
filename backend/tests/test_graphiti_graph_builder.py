from app.config import Config
from app.services.graph_builder import GraphBuilderService


class RecordingGraphBackend:
    def __init__(self):
        self.created = []
        self.ontologies = []
        self.episodes = []
        self.deleted = []

    def create_graph(self, name, description="MiroFish Social Simulation Graph"):
        self.created.append((name, description))
        return "graph-001"

    def set_ontology(self, graph_id, ontology):
        self.ontologies.append((graph_id, ontology))

    def add_episodes(self, graph_id, episodes):
        self.episodes.append((graph_id, episodes))
        return ["episode-001", "episode-002"]

    def get_graph_data(self, graph_id):
        return {
            "graph_id": graph_id,
            "nodes": [{"uuid": "node-001", "name": "Alice", "labels": ["Entity", "Person"]}],
            "edges": [],
            "node_count": 1,
            "edge_count": 0,
        }

    def delete_graph(self, graph_id):
        self.deleted.append(graph_id)


def test_graph_builder_accepts_graphiti_mode_without_zep_api_key(monkeypatch):
    monkeypatch.setattr(Config, "GRAPH_BACKEND", "graphiti")
    monkeypatch.setattr(Config, "ZEP_API_KEY", None)

    service = GraphBuilderService(graph_backend=RecordingGraphBackend())

    graph_id = service.create_graph("Campus Graph")
    service.set_ontology(graph_id, {"entity_types": [{"name": "Person"}], "edge_types": []})

    assert graph_id == "graph-001"
    assert service.graph_backend.created == [
        ("Campus Graph", "MiroFish Social Simulation Graph")
    ]
    assert service.graph_backend.ontologies == [
        ("graph-001", {"entity_types": [{"name": "Person"}], "edge_types": []})
    ]


def test_graph_builder_add_text_batches_uses_graph_backend_episodes(monkeypatch):
    monkeypatch.setattr(Config, "GRAPH_BACKEND", "graphiti")
    backend = RecordingGraphBackend()
    service = GraphBuilderService(graph_backend=backend)

    episode_ids = service.add_text_batches(
        "graph-001",
        ["Alice joined the campus forum.", "Bob replied to Alice."],
        batch_size=2,
    )

    assert episode_ids == ["episode-001", "episode-002"]
    assert backend.episodes == [
        (
            "graph-001",
            [
                {"content": "Alice joined the campus forum.", "source": "text"},
                {"content": "Bob replied to Alice.", "source": "text"},
            ],
        )
    ]


def test_graph_builder_graph_data_and_delete_delegate_to_graph_backend(monkeypatch):
    monkeypatch.setattr(Config, "GRAPH_BACKEND", "graphiti")
    backend = RecordingGraphBackend()
    service = GraphBuilderService(graph_backend=backend)

    graph_data = service.get_graph_data("graph-001")
    service.delete_graph("graph-001")

    assert graph_data["graph_id"] == "graph-001"
    assert graph_data["node_count"] == 1
    assert backend.deleted == ["graph-001"]
