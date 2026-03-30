import importlib
import sys
from pathlib import Path


def load_config(monkeypatch, **env):
    managed_keys = {
        "LLM_API_KEY",
        "LLM_BASE_URL",
        "LLM_MODEL_NAME",
        "ZEP_API_KEY",
        "GRAPH_BACKEND",
        "GRAPHITI_SERVICE_URL",
        "GRAPHITI_DB_PATH",
        "GRAPHITI_EMBEDDING_MODEL",
    }

    for key in managed_keys:
        monkeypatch.delenv(key, raising=False)

    for key, value in env.items():
        monkeypatch.setenv(key, value)

    project_env = Path(__file__).resolve().parents[2] / ".env"
    backup_env = project_env.with_suffix(".env.test-backup")

    if project_env.exists():
        project_env.replace(backup_env)

    try:
        sys.modules.pop("app.config", None)
        module = importlib.import_module("app.config")
        return module.Config
    finally:
        if backup_env.exists():
            backup_env.replace(project_env)


def test_validate_accepts_graphiti_mode_without_zep_api_key(monkeypatch):
    config = load_config(
        monkeypatch,
        GRAPH_BACKEND="graphiti",
        GRAPHITI_SERVICE_URL="http://127.0.0.1:8011",
        LLM_API_KEY="test-key",
        LLM_BASE_URL="https://example.invalid/v1",
        LLM_MODEL_NAME="gpt-5.4",
    )

    assert config.validate() == []


def test_validate_requires_graphiti_service_url(monkeypatch):
    config = load_config(
        monkeypatch,
        GRAPH_BACKEND="graphiti",
        LLM_API_KEY="test-key",
        LLM_BASE_URL="https://example.invalid/v1",
        LLM_MODEL_NAME="gpt-5.4",
    )

    errors = config.validate()

    assert errors == ["GRAPHITI_SERVICE_URL 未配置"]


def test_validate_still_requires_llm_api_key_in_graphiti_mode(monkeypatch):
    config = load_config(
        monkeypatch,
        GRAPH_BACKEND="graphiti",
        GRAPHITI_SERVICE_URL="http://127.0.0.1:8011",
        LLM_BASE_URL="https://example.invalid/v1",
        LLM_MODEL_NAME="gpt-5.4",
    )

    errors = config.validate()

    assert errors == ["LLM_API_KEY 未配置"]


def test_chunk_defaults_are_tuned_for_graphiti_build_speed(monkeypatch):
    config = load_config(
        monkeypatch,
        GRAPH_BACKEND="graphiti",
        GRAPHITI_SERVICE_URL="http://127.0.0.1:8011",
        LLM_API_KEY="test-key",
        LLM_BASE_URL="https://example.invalid/v1",
        LLM_MODEL_NAME="gpt-5.4-mini",
    )

    assert config.DEFAULT_CHUNK_SIZE == 6500
    assert config.DEFAULT_CHUNK_OVERLAP == 650
