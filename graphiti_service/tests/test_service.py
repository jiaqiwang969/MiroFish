import asyncio
from pathlib import Path

from pydantic import BaseModel

from graphiti_core.embedder.client import EmbedderClient
from graphiti_core.driver.driver import GraphProvider
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.prompts.models import Message
from service import GraphitiMemoryService
from service import OpenAICompatibleGraphitiClient


class DummyConfig:
    LLM_API_KEY = "test-key"
    LLM_BASE_URL = "https://example.invalid/v1"
    LLM_MODEL_NAME = "gpt-5.4"
    GRAPHITI_DB_PATH = ""
    GRAPHITI_METADATA_PATH = ""
    GRAPHITI_EMBEDDING_MODEL = "BAAI/bge-m3"


def test_graphiti_service_builds_reranker_with_llm_config(tmp_path, monkeypatch):
    DummyConfig.GRAPHITI_DB_PATH = str(tmp_path / "data" / "graphiti.kuzu")
    DummyConfig.GRAPHITI_METADATA_PATH = str(tmp_path / "data" / "graphs.json")

    captured = {}

    class FakeLLMConfig:
        def __init__(self, api_key=None, base_url=None, model=None):
            self.api_key = api_key
            self.base_url = base_url
            self.model = model

    class FakeKuzuDriver:
        def __init__(self, db):
            self.db = db

    class FakeOpenAIGenericClient:
        def __init__(self, config):
            self.config = config

    class FakeOpenAIRerankerClient:
        def __init__(self, config):
            self.config = config

    class FakeGraphiti:
        def __init__(self, graph_driver, llm_client, embedder, cross_encoder):
            captured["graph_driver"] = graph_driver
            captured["llm_client"] = llm_client
            captured["embedder"] = embedder
            captured["cross_encoder"] = cross_encoder

        async def build_indices_and_constraints(self):
            return None

    service = GraphitiMemoryService(DummyConfig)
    monkeypatch.setattr(
        service,
        "_graphiti_imports",
        lambda: {
            "Graphiti": FakeGraphiti,
            "KuzuDriver": FakeKuzuDriver,
            "LLMConfig": FakeLLMConfig,
            "OpenAIGenericClient": FakeOpenAIGenericClient,
            "OpenAIRerankerClient": FakeOpenAIRerankerClient,
        },
    )
    monkeypatch.setattr(service, "_build_embedder", lambda: "embedder")
    monkeypatch.setattr(service, "_run_async", lambda coro: coro.close())

    service._get_graphiti()

    assert captured["llm_client"].config.api_key == "test-key"
    assert captured["llm_client"].config.base_url == "https://example.invalid/v1"
    assert captured["llm_client"].config.model == "gpt-5.4"
    assert captured["cross_encoder"].config.api_key == "test-key"
    assert captured["cross_encoder"].config.base_url == "https://example.invalid/v1"
    assert captured["cross_encoder"].config.model == "gpt-5.4"


def test_add_episodes_aligns_driver_database_with_graph_id(tmp_path, monkeypatch):
    DummyConfig.GRAPHITI_DB_PATH = str(tmp_path / "data" / "graphiti.kuzu")
    DummyConfig.GRAPHITI_METADATA_PATH = str(tmp_path / "data" / "graphs.json")

    class FakeEpisode:
        uuid = "episode-001"

    class FakeResult:
        episode = FakeEpisode()

    class FakeDriver:
        pass

    class FakeClients:
        def __init__(self, driver):
            self.driver = driver

    class FakeGraphiti:
        def __init__(self):
            self.driver = FakeDriver()
            self.clients = FakeClients(self.driver)
            self.calls = []

        async def add_episode(self, **kwargs):
            self.calls.append(
                {
                    "database": getattr(self.driver, "_database", None),
                    "group_id": kwargs["group_id"],
                }
            )
            return FakeResult()

    service = GraphitiMemoryService(DummyConfig)
    fake_graphiti = FakeGraphiti()
    monkeypatch.setattr(service, "_get_graphiti", lambda: fake_graphiti)
    monkeypatch.setattr(service, "_run_async", lambda coro: __import__("asyncio").run(coro))

    graph = service.create_graph("Campus Graph", "Local Graphiti smoke")
    service.add_episodes(
        graph["graph_id"],
        [
            {
                "content": "Alice organizes the campus meetup through Campus Forum.",
                "source": "text",
            }
        ],
    )

    assert fake_graphiti.calls == [
        {
            "database": graph["graph_id"],
            "group_id": graph["graph_id"],
        }
    ]


def test_warmup_initializes_graphiti_and_embedding(tmp_path, monkeypatch):
    DummyConfig.GRAPHITI_DB_PATH = str(tmp_path / "data" / "graphiti.kuzu")
    DummyConfig.GRAPHITI_METADATA_PATH = str(tmp_path / "data" / "graphs.json")

    calls = []

    class FakeEmbedder:
        async def create(self, input_data):
            calls.append(("embed", input_data))
            return [0.1, 0.2, 0.3]

    service = GraphitiMemoryService(DummyConfig)
    service._embedder = FakeEmbedder()
    monkeypatch.setattr(
        service,
        "_get_graphiti",
        lambda: calls.append(("graphiti", "init")) or object(),
    )
    monkeypatch.setattr(service, "_run_async", lambda coro: asyncio.run(coro))

    result = service.warmup()

    assert calls == [
        ("graphiti", "init"),
        ("embed", "graphiti warmup"),
    ]
    assert result["embedder_warmed"] is True


def test_run_async_reuses_single_background_event_loop(tmp_path):
    DummyConfig.GRAPHITI_DB_PATH = str(tmp_path / "data" / "graphiti.kuzu")
    DummyConfig.GRAPHITI_METADATA_PATH = str(tmp_path / "data" / "graphs.json")

    service = GraphitiMemoryService(DummyConfig)

    async def current_loop():
        return asyncio.get_running_loop()

    loop_1 = service._run_async(current_loop())
    loop_2 = service._run_async(current_loop())

    assert loop_1 is loop_2
    assert loop_1.is_running() is True

    service.close()

    assert loop_1.is_closed() is True


def test_openai_compatible_client_closes_json_schema_objects():
    captured = {}

    class Child(BaseModel):
        name: str

    class Payload(BaseModel):
        child: Child

    class FakeResponse:
        class Choice:
            class MessageObj:
                content = '{"child":{"name":"Alice"}}'

            message = MessageObj()

        choices = [Choice()]

    class FakeCompletions:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return FakeResponse()

    class FakeChat:
        def __init__(self):
            self.completions = FakeCompletions()

    class FakeClient:
        def __init__(self):
            self.chat = FakeChat()

    client = OpenAICompatibleGraphitiClient(
        config=LLMConfig(
            api_key="test-key",
            base_url="https://example.invalid/v1",
            model="gpt-5.4",
            temperature=0,
        ),
        client=FakeClient(),
    )

    result = asyncio.run(
        client._generate_response(
            messages=[Message(role="system", content="Return JSON")],
            response_model=Payload,
        )
    )

    schema = captured["response_format"]["json_schema"]["schema"]
    child_schema = schema["$defs"]["Child"]

    assert result == {"child": {"name": "Alice"}}
    assert schema["additionalProperties"] is False
    assert child_schema["additionalProperties"] is False
    assert captured["response_format"]["json_schema"]["strict"] is True


def test_openai_compatible_client_marks_all_object_properties_required():
    captured = {}

    class Payload(BaseModel):
        name: str
        invalid_at: str | None = None

    class FakeResponse:
        class Choice:
            class MessageObj:
                content = '{"name":"Alice","invalid_at":null}'

            message = MessageObj()

        choices = [Choice()]

    class FakeCompletions:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return FakeResponse()

    class FakeChat:
        def __init__(self):
            self.completions = FakeCompletions()

    class FakeClient:
        def __init__(self):
            self.chat = FakeChat()

    client = OpenAICompatibleGraphitiClient(
        config=LLMConfig(
            api_key="test-key",
            base_url="https://example.invalid/v1",
            model="gpt-5.4",
            temperature=0,
        ),
        client=FakeClient(),
    )

    result = asyncio.run(
        client._generate_response(
            messages=[Message(role="system", content="Return JSON")],
            response_model=Payload,
        )
    )

    schema = captured["response_format"]["json_schema"]["schema"]

    assert result == {"name": "Alice", "invalid_at": None}
    assert schema["required"] == ["name", "invalid_at"]


def test_get_graphiti_creates_kuzu_fulltext_indexes(tmp_path, monkeypatch):
    DummyConfig.GRAPHITI_DB_PATH = str(tmp_path / "data" / "graphiti.kuzu")
    DummyConfig.GRAPHITI_METADATA_PATH = str(tmp_path / "data" / "graphs.json")

    class FakeEmbedder(EmbedderClient):
        async def create(self, input_data):
            return [0.1, 0.2, 0.3]

        async def create_batch(self, input_data_list):
            return [[0.1, 0.2, 0.3] for _ in input_data_list]

    service = GraphitiMemoryService(DummyConfig)
    monkeypatch.setattr(service, "_build_embedder", lambda: FakeEmbedder())

    graphiti = service._get_graphiti()

    result, _, _ = service._run_async(
        graphiti.driver.execute_query(
            "CALL QUERY_FTS_INDEX('Entity', 'node_name_and_summary', 'Alice', TOP := 5) RETURN *;"
        )
    )
    service.close()

    assert result == []


def test_ensure_kuzu_fulltext_indices_skips_existing_indexes(tmp_path):
    DummyConfig.GRAPHITI_DB_PATH = str(tmp_path / "data" / "graphiti.kuzu")
    DummyConfig.GRAPHITI_METADATA_PATH = str(tmp_path / "data" / "graphs.json")
    service = GraphitiMemoryService(DummyConfig)

    class FakeDriver:
        provider = GraphProvider.KUZU

        def __init__(self):
            self.queries = []

        async def execute_query(self, query):
            self.queries.append(query)
            if query.startswith("CALL QUERY_FTS_INDEX("):
                return [], None, None
            raise AssertionError("CREATE_FTS_INDEX should not run when index probe succeeds")

    class FakeGraphiti:
        def __init__(self):
            self.driver = FakeDriver()

    graphiti = FakeGraphiti()
    service._ensure_kuzu_fulltext_indices(graphiti)
    service.close()

    assert len(graphiti.driver.queries) == 4
    assert all(query.startswith("CALL QUERY_FTS_INDEX(") for query in graphiti.driver.queries)


def test_add_episodes_checkpoints_after_successful_batch(tmp_path, monkeypatch):
    DummyConfig.GRAPHITI_DB_PATH = str(tmp_path / "data" / "graphiti.kuzu")
    DummyConfig.GRAPHITI_METADATA_PATH = str(tmp_path / "data" / "graphs.json")

    class FakeEpisode:
        uuid = "episode-001"

    class FakeResult:
        episode = FakeEpisode()

    class FakeDriver:
        def __init__(self):
            self.queries = []

        async def execute_query(self, query):
            self.queries.append(query)
            return [], None, None

    class FakeClients:
        def __init__(self, driver):
            self.driver = driver

    class FakeGraphiti:
        def __init__(self):
            self.driver = FakeDriver()
            self.clients = FakeClients(self.driver)

        async def add_episode(self, **kwargs):
            return FakeResult()

    service = GraphitiMemoryService(DummyConfig)
    graphiti = FakeGraphiti()
    monkeypatch.setattr(service, "_get_graphiti", lambda: graphiti)

    graph = service.create_graph("Checkpoint Graph", "checkpoint")
    service.add_episodes(
        graph["graph_id"],
        [{"content": "Alice met Bob.", "source": "text"}],
    )

    assert graphiti.driver.queries == ["CHECKPOINT;"]


def test_service_backs_up_stale_wal_before_open(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    DummyConfig.GRAPHITI_DB_PATH = str(data_dir / "graphiti.kuzu")
    DummyConfig.GRAPHITI_METADATA_PATH = str(data_dir / "graphs.json")

    db_path = Path(DummyConfig.GRAPHITI_DB_PATH)
    wal_path = Path(f"{DummyConfig.GRAPHITI_DB_PATH}.wal")
    db_path.write_text("db", encoding="utf-8")
    wal_path.write_text("wal", encoding="utf-8")

    service = GraphitiMemoryService(DummyConfig)
    service.close()

    backups = sorted(data_dir.glob("graphiti.kuzu.wal.stale-*"))

    assert wal_path.exists() is False
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "wal"
