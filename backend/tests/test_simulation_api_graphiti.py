from app import create_app
from app.config import Config


class DummyEntityReader:
    def __init__(self, api_key=None):
        self.api_key = api_key

    def filter_defined_entities(self, graph_id, defined_entity_types=None, enrich_with_edges=True):
        class Result:
            def to_dict(self):
                return {
                    "entities": [
                        {
                            "uuid": "node-001",
                            "name": "Alice",
                            "labels": ["Entity", "Person"],
                            "summary": "Student leader",
                            "attributes": {},
                            "related_edges": [],
                            "related_nodes": [],
                        }
                    ],
                    "entity_types": ["Person"],
                    "total_count": 1,
                    "filtered_count": 1,
                }

        return Result()

    def get_entity_with_context(self, graph_id, entity_uuid):
        class Entity:
            def to_dict(self):
                return {
                    "uuid": entity_uuid,
                    "name": "Alice",
                    "labels": ["Entity", "Person"],
                    "summary": "Student leader",
                    "attributes": {},
                    "related_edges": [],
                    "related_nodes": [],
                }

        return Entity()


def test_simulation_entities_route_allows_graphiti_mode_without_zep_api_key(monkeypatch):
    monkeypatch.setattr(Config, "GRAPH_BACKEND", "graphiti")
    monkeypatch.setattr(Config, "ZEP_API_KEY", None)
    monkeypatch.setattr(Config, "GRAPHITI_SERVICE_URL", "http://127.0.0.1:8011")
    monkeypatch.setattr("app.api.simulation.ZepEntityReader", DummyEntityReader)

    client = create_app().test_client()
    response = client.get("/api/simulation/entities/graph-001")

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert response.get_json()["data"]["filtered_count"] == 1


def test_simulation_entity_detail_route_allows_graphiti_mode_without_zep_api_key(monkeypatch):
    monkeypatch.setattr(Config, "GRAPH_BACKEND", "graphiti")
    monkeypatch.setattr(Config, "ZEP_API_KEY", None)
    monkeypatch.setattr(Config, "GRAPHITI_SERVICE_URL", "http://127.0.0.1:8011")
    monkeypatch.setattr("app.api.simulation.ZepEntityReader", DummyEntityReader)

    client = create_app().test_client()
    response = client.get("/api/simulation/entities/graph-001/node-001")

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert response.get_json()["data"]["uuid"] == "node-001"
