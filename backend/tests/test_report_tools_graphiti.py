from app import create_app
from app.config import Config
from app.services.graph_backend import GraphBackendEdge, GraphBackendNode
from app.services.zep_tools import ZepToolsService


class RecordingGraphBackend:
    def list_nodes(self, graph_id):
        assert graph_id == "graph-001"
        return [
            GraphBackendNode(
                uuid="node-001",
                name="Alice",
                labels=["Entity", "Person"],
                summary="Student organizer leading campus discussions",
                attributes={"role": "student"},
            ),
            GraphBackendNode(
                uuid="node-002",
                name="Campus Forum",
                labels=["Entity", "Community"],
                summary="Online space for campus meetup coordination",
                attributes={},
            ),
            GraphBackendNode(
                uuid="node-003",
                name="Student Union",
                labels=["Entity", "Organization"],
                summary="Formal student organization",
                attributes={},
            ),
        ]

    def list_edges(self, graph_id):
        assert graph_id == "graph-001"
        return [
            GraphBackendEdge(
                uuid="edge-001",
                name="organizes",
                fact="Alice organizes the campus meetup through Campus Forum",
                source_node_uuid="node-001",
                target_node_uuid="node-002",
                attributes={"valid_at": "2026-03-20T10:00:00Z"},
            ),
            GraphBackendEdge(
                uuid="edge-002",
                name="member_of",
                fact="Alice is an active member of Student Union",
                source_node_uuid="node-001",
                target_node_uuid="node-003",
                attributes={"valid_at": "2026-03-10T10:00:00Z"},
            ),
        ]


class DummyLLMClient:
    def chat_json(self, messages, temperature):
        return {
            "sub_queries": [
                "Alice campus meetup",
                "Campus Forum influence",
            ]
        }


def test_zep_tools_service_search_and_statistics_work_in_graphiti_mode(monkeypatch):
    monkeypatch.setattr(Config, "GRAPH_BACKEND", "graphiti")
    monkeypatch.setattr(Config, "ZEP_API_KEY", None)
    monkeypatch.setattr(Config, "GRAPHITI_SERVICE_URL", "http://127.0.0.1:8011")

    service = ZepToolsService(graph_backend=RecordingGraphBackend())

    result = service.quick_search("graph-001", "Alice campus meetup", limit=5)
    stats = service.get_graph_statistics("graph-001")

    assert result.total_count >= 1
    assert "Alice organizes the campus meetup through Campus Forum" in result.facts
    assert stats == {
        "graph_id": "graph-001",
        "total_nodes": 3,
        "total_edges": 2,
        "entity_types": {
            "Person": 1,
            "Community": 1,
            "Organization": 1,
        },
        "relation_types": {
            "organizes": 1,
            "member_of": 1,
        },
    }


def test_zep_tools_service_insight_forge_uses_graphiti_entities(monkeypatch):
    monkeypatch.setattr(Config, "GRAPH_BACKEND", "graphiti")
    monkeypatch.setattr(Config, "ZEP_API_KEY", None)
    monkeypatch.setattr(Config, "GRAPHITI_SERVICE_URL", "http://127.0.0.1:8011")

    service = ZepToolsService(
        graph_backend=RecordingGraphBackend(),
        llm_client=DummyLLMClient(),
    )

    result = service.insight_forge(
        graph_id="graph-001",
        query="Who is driving the campus meetup momentum?",
        simulation_requirement="Observe how campus communities coordinate around events.",
    )

    assert result.total_facts >= 1
    assert "Alice --[organizes]--> Campus Forum" in result.relationship_chains
    assert any(entity["name"] == "Alice" for entity in result.entity_insights)


def test_report_tool_search_route_allows_graphiti_mode_without_zep_api_key(monkeypatch):
    monkeypatch.setattr(Config, "GRAPH_BACKEND", "graphiti")
    monkeypatch.setattr(Config, "ZEP_API_KEY", None)
    monkeypatch.setattr(Config, "GRAPHITI_SERVICE_URL", "http://127.0.0.1:8011")
    monkeypatch.setattr(
        "app.services.zep_tools.get_graph_backend",
        lambda config=Config, client=None: RecordingGraphBackend(),
    )

    client = create_app().test_client()
    response = client.post(
        "/api/report/tools/search",
        json={
            "graph_id": "graph-001",
            "query": "campus meetup",
            "limit": 5,
        },
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert "Alice organizes the campus meetup through Campus Forum" in response.get_json()["data"]["facts"]
