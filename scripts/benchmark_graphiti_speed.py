#!/usr/bin/env python3
"""
Quick local benchmark for Graphiti build latency bottlenecks.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from openai import OpenAI
from sentence_transformers import SentenceTransformer


def http_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    timeout: float = 600.0,
) -> dict[str, Any]:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            return json.loads(raw.decode("utf-8")) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed: {exc.code} {raw}") from exc


def benchmark_llm(base_url: str, api_key: str, model: str, text_sample: str) -> dict[str, Any]:
    client = OpenAI(base_url=base_url, api_key=api_key)
    started_at = time.perf_counter()
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "Return strict JSON with keys summary, actors, relations.",
            },
            {
                "role": "user",
                "content": (
                    "Analyze the following text and extract a brief summary, actors, and relations.\n\n"
                    f"{text_sample}"
                ),
            },
        ],
    )
    elapsed = time.perf_counter() - started_at
    content = response.choices[0].message.content or ""
    return {
        "model": model,
        "elapsed_seconds": round(elapsed, 3),
        "response_chars": len(content),
    }


def benchmark_embedding(model_name: str, text_sample: str) -> dict[str, Any]:
    load_started_at = time.perf_counter()
    model = SentenceTransformer(model_name)
    load_elapsed = time.perf_counter() - load_started_at

    encode_started_at = time.perf_counter()
    vectors = model.encode([text_sample], normalize_embeddings=True)
    encode_elapsed = time.perf_counter() - encode_started_at

    return {
        "model": model_name,
        "load_seconds": round(load_elapsed, 3),
        "encode_seconds": round(encode_elapsed, 3),
        "vector_dimensions": int(len(vectors[0])),
    }


def benchmark_sidecar(
    graphiti_url: str,
    ontology: dict[str, Any],
    text_sample: str,
    timeout: float,
) -> dict[str, Any]:
    graph_name = f"benchmark-{uuid.uuid4().hex[:8]}"
    graph_id = None

    try:
        create_started_at = time.perf_counter()
        create_response = http_json(
            "POST",
            f"{graphiti_url}/graphs",
            {"name": graph_name, "description": "Graphiti speed benchmark"},
            timeout=timeout,
        )
        create_elapsed = time.perf_counter() - create_started_at
        graph_id = create_response["data"]["graph_id"]

        ontology_started_at = time.perf_counter()
        http_json(
            "POST",
            f"{graphiti_url}/graphs/{graph_id}/ontology",
            {"ontology": ontology},
            timeout=timeout,
        )
        ontology_elapsed = time.perf_counter() - ontology_started_at

        ingest_started_at = time.perf_counter()
        ingest_response = http_json(
            "POST",
            f"{graphiti_url}/graphs/{graph_id}/episodes",
            {"episodes": [{"content": text_sample, "source": "text"}]},
            timeout=timeout,
        )
        ingest_elapsed = time.perf_counter() - ingest_started_at

        return {
            "graph_id": graph_id,
            "create_graph_seconds": round(create_elapsed, 3),
            "set_ontology_seconds": round(ontology_elapsed, 3),
            "add_episodes_seconds": round(ingest_elapsed, 3),
            "episode_count": len(ingest_response["data"].get("episode_ids", [])),
        }
    finally:
        if graph_id:
            try:
                http_json("DELETE", f"{graphiti_url}/graphs/{graph_id}", timeout=timeout)
            except Exception:
                pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark Graphiti speed bottlenecks.")
    parser.add_argument(
        "--models",
        nargs="+",
        default=["gpt-5.4", "gpt-5.4-mini"],
        help="Models to compare for direct chat-completion latency.",
    )
    parser.add_argument(
        "--project-file",
        required=True,
        help="Path to project.json containing ontology.",
    )
    parser.add_argument(
        "--text-file",
        required=True,
        help="Path to extracted_text.txt.",
    )
    parser.add_argument(
        "--sample-chars",
        type=int,
        default=1600,
        help="Number of characters to use from the extracted text sample.",
    )
    parser.add_argument(
        "--embedding-model",
        default=os.environ.get("GRAPHITI_EMBEDDING_MODEL", "BAAI/bge-m3"),
        help="Local embedding model name.",
    )
    parser.add_argument(
        "--llm-base-url",
        default=os.environ.get("LLM_BASE_URL"),
        help="OpenAI-compatible base URL.",
    )
    parser.add_argument(
        "--llm-api-key",
        default=os.environ.get("LLM_API_KEY"),
        help="OpenAI-compatible API key.",
    )
    parser.add_argument(
        "--graphiti-url",
        default=os.environ.get("GRAPHITI_SERVICE_URL", "http://127.0.0.1:8011"),
        help="Running Graphiti sidecar URL.",
    )
    parser.add_argument(
        "--sidecar-timeout",
        type=float,
        default=600.0,
        help="Timeout for sidecar HTTP requests in seconds.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.llm_base_url or not args.llm_api_key:
        raise SystemExit("LLM_BASE_URL and LLM_API_KEY are required.")

    project = json.loads(Path(args.project_file).read_text(encoding="utf-8"))
    text = Path(args.text_file).read_text(encoding="utf-8")
    text_sample = text[: args.sample_chars].strip()

    if not text_sample:
        raise SystemExit("Text sample is empty.")

    results = {
        "sample_chars": len(text_sample),
        "llm": [],
        "embedding": benchmark_embedding(args.embedding_model, text_sample),
        "sidecar": benchmark_sidecar(
            args.graphiti_url,
            project["ontology"],
            text_sample,
            args.sidecar_timeout,
        ),
    }

    for model in args.models:
        results["llm"].append(
            benchmark_llm(args.llm_base_url, args.llm_api_key, model, text_sample)
        )

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
