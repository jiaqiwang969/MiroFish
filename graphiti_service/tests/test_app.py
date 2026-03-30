from app import create_app


class RecordingService:
    def __init__(self):
        self.created = []
        self.ontologies = []
        self.episodes = []
        self.deleted = []
        self.warmup_calls = 0

    def create_graph(self, name, description):
        self.created.append((name, description))
        return {"graph_id": "graph-001"}

    def set_ontology(self, graph_id, ontology):
        self.ontologies.append((graph_id, ontology))

    def add_episodes(self, graph_id, episodes):
        self.episodes.append((graph_id, episodes))
        return ["episode-001", "episode-002"]

    def get_graph_summary(self, graph_id):
        return {"graph_id": graph_id, "node_count": 2, "edge_count": 1}

    def list_nodes(self, graph_id):
        return [{"uuid": "node-001", "name": "Alice", "labels": ["Entity", "Person"]}]

    def list_edges(self, graph_id):
        return [
            {
                "uuid": "edge-001",
                "name": "knows",
                "fact": "Alice knows Bob",
                "source_node_uuid": "node-001",
                "target_node_uuid": "node-002",
            }
        ]

    def delete_graph(self, graph_id):
        self.deleted.append(graph_id)

    def warmup(self):
        self.warmup_calls += 1
        return {"status": "ok"}


def make_client():
    service = RecordingService()
    app = create_app(service=service)
    app.config["TESTING"] = True
    return app.test_client(), service


def test_create_graph_endpoint_returns_graph_id():
    client, service = make_client()

    response = client.post(
        "/graphs",
        json={
            "name": "Campus Graph",
            "description": "MiroFish Social Simulation Graph",
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "success": True,
        "data": {"graph_id": "graph-001"},
    }
    assert service.created == [
        ("Campus Graph", "MiroFish Social Simulation Graph")
    ]


def test_set_ontology_endpoint_passes_graph_metadata_to_service():
    client, service = make_client()

    response = client.post(
        "/graphs/graph-001/ontology",
        json={"ontology": {"entity_types": [{"name": "Person"}], "edge_types": []}},
    )

    assert response.status_code == 200
    assert response.get_json() == {"success": True, "data": {"graph_id": "graph-001"}}
    assert service.ontologies == [
        ("graph-001", {"entity_types": [{"name": "Person"}], "edge_types": []})
    ]


def test_add_episodes_endpoint_returns_episode_ids():
    client, service = make_client()

    response = client.post(
        "/graphs/graph-001/episodes",
        json={
            "episodes": [
                {"content": "Alice joined the campus forum.", "source": "text"},
                {"content": "Bob replied to Alice.", "source": "simulation_runtime"},
            ]
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "success": True,
        "data": {"episode_ids": ["episode-001", "episode-002"]},
    }
    assert service.episodes == [
        (
            "graph-001",
            [
                {"content": "Alice joined the campus forum.", "source": "text"},
                {"content": "Bob replied to Alice.", "source": "simulation_runtime"},
            ],
        )
    ]


def test_nodes_and_edges_endpoints_return_service_payloads():
    client, _ = make_client()

    nodes_response = client.get("/graphs/graph-001/nodes")
    edges_response = client.get("/graphs/graph-001/edges")
    summary_response = client.get("/graphs/graph-001")

    assert nodes_response.status_code == 200
    assert nodes_response.get_json() == {
        "success": True,
        "data": {
            "nodes": [
                {"uuid": "node-001", "name": "Alice", "labels": ["Entity", "Person"]}
            ]
        },
    }

    assert edges_response.status_code == 200
    assert edges_response.get_json() == {
        "success": True,
        "data": {
            "edges": [
                {
                    "uuid": "edge-001",
                    "name": "knows",
                    "fact": "Alice knows Bob",
                    "source_node_uuid": "node-001",
                    "target_node_uuid": "node-002",
                }
            ]
        },
    }

    assert summary_response.status_code == 200
    assert summary_response.get_json() == {
        "success": True,
        "data": {"graph_id": "graph-001", "node_count": 2, "edge_count": 1},
    }


def test_delete_graph_endpoint_invokes_service():
    client, service = make_client()

    response = client.delete("/graphs/graph-001")

    assert response.status_code == 200
    assert response.get_json() == {
        "success": True,
        "data": {"graph_id": "graph-001"},
    }
    assert service.deleted == ["graph-001"]


def test_create_app_warms_service_when_enabled():
    class WarmConfig:
        GRAPHITI_PREWARM = True

    service = RecordingService()
    app = create_app(service=service, config_class=WarmConfig)

    assert app is not None
    assert service.warmup_calls == 1


def test_create_app_skips_warmup_when_disabled():
    class WarmConfig:
        GRAPHITI_PREWARM = False

    service = RecordingService()
    app = create_app(service=service, config_class=WarmConfig)

    assert app is not None
    assert service.warmup_calls == 0
