from app.config import Config
from app.services.graph_backend import GraphBackendEdge, GraphBackendNode
from app.services.zep_entity_reader import ZepEntityReader


class RecordingGraphBackend:
    def list_nodes(self, graph_id):
        assert graph_id == "graph-001"
        return [
            GraphBackendNode(
                uuid="node-001",
                name="Alice",
                labels=["Entity", "Person"],
                summary="Student leader",
                attributes={"role": "student"},
            ),
            GraphBackendNode(
                uuid="node-002",
                name="Campus Forum",
                labels=["Entity", "Community"],
                summary="Online community",
                attributes={},
            ),
            GraphBackendNode(
                uuid="node-003",
                name="Ignored",
                labels=["Entity"],
                summary="Should be filtered out",
                attributes={},
            ),
        ]

    def list_edges(self, graph_id):
        assert graph_id == "graph-001"
        return [
            GraphBackendEdge(
                uuid="edge-001",
                name="participates_in",
                fact="Alice participates in Campus Forum",
                source_node_uuid="node-001",
                target_node_uuid="node-002",
                attributes={},
            )
        ]


def test_entity_reader_filters_and_enriches_entities_in_graphiti_mode(monkeypatch):
    monkeypatch.setattr(Config, "GRAPH_BACKEND", "graphiti")

    reader = ZepEntityReader(graph_backend=RecordingGraphBackend())
    result = reader.filter_defined_entities("graph-001", enrich_with_edges=True)

    assert result.total_count == 3
    assert result.filtered_count == 2
    assert result.entity_types == {"Person", "Community"}
    assert result.entities[0].related_edges == [
        {
            "direction": "outgoing",
            "edge_name": "participates_in",
            "fact": "Alice participates in Campus Forum",
            "target_node_uuid": "node-002",
        }
    ]
    assert result.entities[0].related_nodes == [
        {
            "uuid": "node-002",
            "name": "Campus Forum",
            "labels": ["Entity", "Community"],
            "summary": "Online community",
        }
    ]


def test_entity_reader_gets_entity_context_from_graph_backend(monkeypatch):
    monkeypatch.setattr(Config, "GRAPH_BACKEND", "graphiti")

    reader = ZepEntityReader(graph_backend=RecordingGraphBackend())
    entity = reader.get_entity_with_context("graph-001", "node-001")

    assert entity is not None
    assert entity.uuid == "node-001"
    assert entity.name == "Alice"
    assert entity.related_edges == [
        {
            "direction": "outgoing",
            "edge_name": "participates_in",
            "fact": "Alice participates in Campus Forum",
            "target_node_uuid": "node-002",
        }
    ]
