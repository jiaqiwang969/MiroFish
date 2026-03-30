from app import create_app
from app.config import Config
from app.models.project import ProjectManager, ProjectStatus


class ImmediateThread:
    def __init__(self, target, args=(), kwargs=None, daemon=None):
        self.target = target
        self.args = args
        self.kwargs = kwargs or {}
        self.daemon = daemon

    def start(self):
        self.target(*self.args, **self.kwargs)


class DummyGraphBuilderService:
    deleted_graph_ids = []
    last_batch_size = None

    def __init__(self, api_key=None):
        self.api_key = api_key

    def create_graph(self, name):
        return "graph-001"

    def set_ontology(self, graph_id, ontology):
        self.last_ontology = (graph_id, ontology)

    def add_text_batches(self, graph_id, chunks, batch_size=3, progress_callback=None):
        DummyGraphBuilderService.last_batch_size = batch_size
        if progress_callback:
            progress_callback("ok", 1.0)
        return ["episode-001"]

    def _wait_for_episodes(self, episode_uuids, progress_callback=None):
        if progress_callback:
            progress_callback("ok", 1.0)

    def get_graph_data(self, graph_id):
        return {
            "graph_id": graph_id,
            "nodes": [{"uuid": "node-001", "name": "Alice", "labels": ["Entity", "Person"]}],
            "edges": [],
            "node_count": 1,
            "edge_count": 0,
        }

    def delete_graph(self, graph_id):
        self.deleted_graph_ids.append(graph_id)


def setup_project(tmp_path, monkeypatch):
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path / "projects"))

    project = ProjectManager.create_project(name="Campus Graph")
    project.status = ProjectStatus.ONTOLOGY_GENERATED
    project.ontology = {
        "entity_types": [{"name": "Person"}],
        "edge_types": [],
    }
    ProjectManager.save_project(project)
    ProjectManager.save_extracted_text(project.project_id, "Alice joined the campus forum.")
    return project


def test_build_graph_route_allows_graphiti_mode_without_zep_api_key(tmp_path, monkeypatch):
    DummyGraphBuilderService.last_batch_size = None
    monkeypatch.setattr(Config, "GRAPH_BACKEND", "graphiti")
    monkeypatch.setattr(Config, "ZEP_API_KEY", None)
    monkeypatch.setattr(Config, "GRAPHITI_SERVICE_URL", "http://127.0.0.1:8011")
    monkeypatch.setattr("app.api.graph.GraphBuilderService", DummyGraphBuilderService)
    monkeypatch.setattr("app.api.graph.threading.Thread", ImmediateThread)

    project = setup_project(tmp_path, monkeypatch)
    client = create_app().test_client()

    response = client.post(
        "/api/graph/build",
        json={"project_id": project.project_id},
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True

    refreshed = ProjectManager.get_project(project.project_id)
    assert refreshed.graph_id == "graph-001"
    assert refreshed.status == ProjectStatus.GRAPH_COMPLETED
    assert refreshed.chunk_size == Config.DEFAULT_CHUNK_SIZE
    assert refreshed.chunk_overlap == Config.DEFAULT_CHUNK_OVERLAP
    assert DummyGraphBuilderService.last_batch_size == 2


def test_get_graph_data_route_uses_graph_builder_in_graphiti_mode(monkeypatch):
    monkeypatch.setattr(Config, "GRAPH_BACKEND", "graphiti")
    monkeypatch.setattr(Config, "ZEP_API_KEY", None)
    monkeypatch.setattr(Config, "GRAPHITI_SERVICE_URL", "http://127.0.0.1:8011")
    monkeypatch.setattr("app.api.graph.GraphBuilderService", DummyGraphBuilderService)

    client = create_app().test_client()
    response = client.get("/api/graph/data/graph-001")

    assert response.status_code == 200
    assert response.get_json() == {
        "success": True,
        "data": {
            "graph_id": "graph-001",
            "nodes": [{"uuid": "node-001", "name": "Alice", "labels": ["Entity", "Person"]}],
            "edges": [],
            "node_count": 1,
            "edge_count": 0,
        },
    }


def test_delete_graph_route_uses_graph_builder_in_graphiti_mode(monkeypatch):
    DummyGraphBuilderService.deleted_graph_ids = []
    monkeypatch.setattr(Config, "GRAPH_BACKEND", "graphiti")
    monkeypatch.setattr(Config, "ZEP_API_KEY", None)
    monkeypatch.setattr(Config, "GRAPHITI_SERVICE_URL", "http://127.0.0.1:8011")
    monkeypatch.setattr("app.api.graph.GraphBuilderService", DummyGraphBuilderService)

    client = create_app().test_client()
    response = client.delete("/api/graph/delete/graph-001")

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert DummyGraphBuilderService.deleted_graph_ids == ["graph-001"]
