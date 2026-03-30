from app.config import Config
from app.services.zep_graph_memory_updater import AgentActivity, ZepGraphMemoryUpdater


class RecordingGraphBackend:
    def __init__(self):
        self.calls = []

    def append_episode(self, graph_id, content, source="text", metadata=None):
        self.calls.append(
            {
                "graph_id": graph_id,
                "content": content,
                "source": source,
                "metadata": metadata or {},
            }
        )
        return "episode-001"


def test_graph_memory_updater_flushes_runtime_batch_through_graph_backend(monkeypatch):
    monkeypatch.setattr(Config, "GRAPH_BACKEND", "graphiti")
    monkeypatch.setattr(Config, "ZEP_API_KEY", None)
    monkeypatch.setattr(Config, "GRAPHITI_SERVICE_URL", "http://127.0.0.1:8011")

    backend = RecordingGraphBackend()
    updater = ZepGraphMemoryUpdater("graph-001", graph_backend=backend)

    updater.add_activity(
        AgentActivity(
            platform="twitter",
            agent_id=1,
            agent_name="Alice",
            action_type="CREATE_POST",
            action_args={"content": "校园见面会开始了"},
            round_num=1,
            timestamp="2026-03-29T10:00:00",
        )
    )
    updater.add_activity(
        AgentActivity(
            platform="twitter",
            agent_id=2,
            agent_name="Bob",
            action_type="FOLLOW",
            action_args={"target_user_name": "Alice"},
            round_num=1,
            timestamp="2026-03-29T10:01:00",
        )
    )

    updater._flush_remaining()

    assert backend.calls == [
        {
            "graph_id": "graph-001",
            "content": (
                "Alice: 发布了一条帖子：「校园见面会开始了」\n"
                "Bob: 关注了用户「Alice」"
            ),
            "source": "simulation_runtime",
            "metadata": {
                "platform": "twitter",
                "batch_size": 2,
            },
        }
    ]

    assert updater.get_stats()["items_sent"] == 2
    assert updater.get_stats()["batches_sent"] == 1
