"""
Configuration for the local Graphiti sidecar service.
"""

from __future__ import annotations

import os
from dotenv import load_dotenv


service_root = os.path.dirname(os.path.abspath(__file__))
service_env = os.path.join(service_root, ".env")
project_env = os.path.join(os.path.dirname(service_root), ".env")

if os.path.exists(service_env):
    load_dotenv(service_env, override=True)
elif os.path.exists(project_env):
    load_dotenv(project_env, override=True)
else:
    load_dotenv(override=True)


class Config:
    LLM_API_KEY = os.environ.get("LLM_API_KEY")
    LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL_NAME = os.environ.get("LLM_MODEL_NAME", "gpt-5.4-mini")

    GRAPHITI_DB_PATH = os.environ.get(
        "GRAPHITI_DB_PATH",
        os.path.join(service_root, "data", "graphiti.kuzu"),
    )
    GRAPHITI_EMBEDDING_MODEL = os.environ.get("GRAPHITI_EMBEDDING_MODEL", "BAAI/bge-m3")
    GRAPHITI_HOST = os.environ.get("GRAPHITI_HOST", "127.0.0.1")
    GRAPHITI_PORT = int(os.environ.get("GRAPHITI_PORT", "8011"))
    GRAPHITI_METADATA_PATH = os.environ.get(
        "GRAPHITI_METADATA_PATH",
        os.path.join(os.path.dirname(GRAPHITI_DB_PATH), "graphs.json"),
    )
    GRAPHITI_PREWARM = os.environ.get("GRAPHITI_PREWARM", "true").lower() == "true"
    GRAPHITI_CHECKPOINT_AFTER_WRITE = (
        os.environ.get("GRAPHITI_CHECKPOINT_AFTER_WRITE", "true").lower() == "true"
    )
    GRAPHITI_RECOVER_STALE_WAL = (
        os.environ.get("GRAPHITI_RECOVER_STALE_WAL", "true").lower() == "true"
    )

    @classmethod
    def validate(cls) -> list[str]:
        errors = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY 未配置")
        if not cls.GRAPHITI_DB_PATH:
            errors.append("GRAPHITI_DB_PATH 未配置")
        if not cls.GRAPHITI_EMBEDDING_MODEL:
            errors.append("GRAPHITI_EMBEDDING_MODEL 未配置")
        return errors
