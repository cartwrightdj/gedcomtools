import json
from pathlib import Path

import pytest

pytest.importorskip("mcp")

from gedcomtools.mcp import server


SAMPLE = Path(__file__).parent.parent / ".sample_data" / "gedcom5" / "gedcom5_sample.ged"


def test_export_graph_jsonl_uses_generic_node_edge_names(tmp_path):
    result = server.export_arango_graph(str(SAMPLE), str(tmp_path), strict=False)

    assert set(result["written"]) == {"nodes", "edges"}
    nodes_path = tmp_path / "nodes.jsonl"
    edges_path = tmp_path / "edges.jsonl"
    assert result["written"]["nodes"]["path"] == str(nodes_path)
    assert result["written"]["edges"]["path"] == str(edges_path)
    assert nodes_path.exists()
    assert edges_path.exists()

    node_types = {
        json.loads(line)["node_type"]
        for line in nodes_path.read_text(encoding="utf-8").splitlines()
    }
    assert "person" in node_types
    assert node_types - {"person"}
