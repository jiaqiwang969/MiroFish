from app.config import Config
from app.models.project import Project, ProjectManager


def test_create_project_uses_config_chunk_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path / "projects"))

    project = ProjectManager.create_project(name="Chunk Defaults")

    assert project.chunk_size == Config.DEFAULT_CHUNK_SIZE
    assert project.chunk_overlap == Config.DEFAULT_CHUNK_OVERLAP


def test_project_from_dict_uses_config_chunk_defaults_when_missing():
    project = Project.from_dict(
        {
            "project_id": "proj_test",
            "name": "Chunk Defaults",
            "status": "created",
            "created_at": "2026-03-29T00:00:00",
            "updated_at": "2026-03-29T00:00:00",
        }
    )

    assert project.chunk_size == Config.DEFAULT_CHUNK_SIZE
    assert project.chunk_overlap == Config.DEFAULT_CHUNK_OVERLAP
