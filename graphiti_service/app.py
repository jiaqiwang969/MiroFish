"""
Flask entrypoint for the Graphiti sidecar service.
"""

from __future__ import annotations

import logging

from flask import Flask, jsonify, request

from config import Config
from service import GraphitiMemoryService


logger = logging.getLogger(__name__)


def create_app(service=None, config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    graph_service = service or GraphitiMemoryService(config_class)

    if getattr(config_class, "GRAPHITI_PREWARM", False):
        warmup = getattr(graph_service, "warmup", None)
        if callable(warmup):
            try:
                warmup()
            except Exception:
                logger.exception("Graphiti sidecar warmup failed")

    @app.get("/health")
    def health():
        return jsonify({"success": True, "data": {"status": "ok"}})

    @app.post("/graphs")
    def create_graph():
        payload = request.get_json() or {}
        result = graph_service.create_graph(
            name=payload.get("name", "MiroFish Graph"),
            description=payload.get("description", "MiroFish Social Simulation Graph"),
        )
        return jsonify({"success": True, "data": result})

    @app.post("/graphs/<graph_id>/ontology")
    def set_ontology(graph_id: str):
        payload = request.get_json() or {}
        graph_service.set_ontology(graph_id, payload.get("ontology") or {})
        return jsonify({"success": True, "data": {"graph_id": graph_id}})

    @app.post("/graphs/<graph_id>/episodes")
    def add_episodes(graph_id: str):
        payload = request.get_json() or {}
        episode_ids = graph_service.add_episodes(graph_id, payload.get("episodes") or [])
        return jsonify({"success": True, "data": {"episode_ids": episode_ids}})

    @app.get("/graphs/<graph_id>")
    def get_graph(graph_id: str):
        result = graph_service.get_graph_summary(graph_id)
        return jsonify({"success": True, "data": result})

    @app.get("/graphs/<graph_id>/nodes")
    def list_nodes(graph_id: str):
        return jsonify({"success": True, "data": {"nodes": graph_service.list_nodes(graph_id)}})

    @app.get("/graphs/<graph_id>/edges")
    def list_edges(graph_id: str):
        return jsonify({"success": True, "data": {"edges": graph_service.list_edges(graph_id)}})

    @app.delete("/graphs/<graph_id>")
    def delete_graph(graph_id: str):
        graph_service.delete_graph(graph_id)
        return jsonify({"success": True, "data": {"graph_id": graph_id}})

    @app.errorhandler(Exception)
    def handle_error(error: Exception):
        return jsonify({"success": False, "error": str(error)}), 500

    return app


def main():
    errors = Config.validate()
    if errors:
        print("配置错误:")
        for err in errors:
            print(f"  - {err}")
        raise SystemExit(1)

    app = create_app()
    app.run(host=Config.GRAPHITI_HOST, port=Config.GRAPHITI_PORT, debug=False, threaded=True)


if __name__ == "__main__":
    main()
