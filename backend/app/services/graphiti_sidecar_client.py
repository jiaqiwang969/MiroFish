"""
Graphiti sidecar HTTP client
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, Optional, Tuple
from urllib import error, parse, request

from ..config import Config


Transport = Callable[[str, str, Optional[Dict[str, Any]], float], Tuple[int, Any]]


class GraphitiSidecarError(RuntimeError):
    """Raised when the Graphiti sidecar returns an error."""


class GraphitiSidecarClient:
    """Thin HTTP client for the local Graphiti sidecar service."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        transport: Optional[Transport] = None,
        timeout: Optional[float] = None,
    ):
        self.base_url = (base_url or Config.GRAPHITI_SERVICE_URL or "").rstrip("/")
        if not self.base_url:
            raise ValueError("GRAPHITI_SERVICE_URL 未配置")

        self.transport = transport or self._default_transport
        self.timeout = timeout if timeout is not None else Config.GRAPHITI_REQUEST_TIMEOUT_SECONDS

    def create_graph(self, name: str, description: str) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/graphs",
            {
                "name": name,
                "description": description,
            },
        )

    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/graphs/{parse.quote(graph_id, safe='')}/ontology",
            {"ontology": ontology},
        )

    def add_episodes(self, graph_id: str, episodes: list[dict[str, Any]]) -> list[str]:
        response = self._request(
            "POST",
            f"/graphs/{parse.quote(graph_id, safe='')}/episodes",
            {"episodes": episodes},
        )
        return list(response.get("episode_ids", []))

    def get_nodes(self, graph_id: str) -> list[dict[str, Any]]:
        response = self._request(
            "GET",
            f"/graphs/{parse.quote(graph_id, safe='')}/nodes",
        )
        return list(response.get("nodes", []))

    def get_edges(self, graph_id: str) -> list[dict[str, Any]]:
        response = self._request(
            "GET",
            f"/graphs/{parse.quote(graph_id, safe='')}/edges",
        )
        return list(response.get("edges", []))

    def get_graph(self, graph_id: str) -> Dict[str, Any]:
        return self._request(
            "GET",
            f"/graphs/{parse.quote(graph_id, safe='')}",
        )

    def delete_graph(self, graph_id: str) -> Dict[str, Any]:
        return self._request(
            "DELETE",
            f"/graphs/{parse.quote(graph_id, safe='')}",
        )

    def _request(
        self,
        method: str,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        status_code, response = self.transport(
            method,
            f"{self.base_url}{path}",
            payload,
            self.timeout,
        )

        response = self._unwrap_response(response)

        if status_code >= 400:
            message = "Graphiti sidecar 请求失败"
            if isinstance(response, dict):
                message = response.get("error") or response.get("message") or message
            raise GraphitiSidecarError(message)

        if not isinstance(response, dict):
            raise GraphitiSidecarError("Graphiti sidecar 返回了无效响应")

        return response

    @staticmethod
    def _unwrap_response(response: Any) -> Any:
        if isinstance(response, dict) and "data" in response:
            if response.get("success", True):
                return response["data"]

            message = response.get("error") or response.get("message") or "Graphiti sidecar 请求失败"
            raise GraphitiSidecarError(message)

        return response

    @staticmethod
    def _default_transport(
        method: str,
        url: str,
        payload: Optional[Dict[str, Any]],
        timeout: float,
    ) -> Tuple[int, Any]:
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = request.Request(url, data=body, headers=headers, method=method)

        try:
            with request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                data = json.loads(raw.decode("utf-8")) if raw else {}
                return resp.status, data
        except error.HTTPError as exc:
            raw = exc.read()
            try:
                data = json.loads(raw.decode("utf-8")) if raw else {}
            except json.JSONDecodeError:
                data = {"error": raw.decode("utf-8") if raw else str(exc)}
            return exc.code, data
