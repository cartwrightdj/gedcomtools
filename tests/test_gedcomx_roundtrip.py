"""
Tests for GedcomX serialization round-trip.

Converts GEDCOM 5 → GedcomX → JSON → GedcomX and verifies
record counts are preserved and the result is fully JSON-serialisable.
"""
from __future__ import annotations

import json
import pytest
from pathlib import Path

from gedcomtools.gedcom5.parser import Gedcom5x
from gedcomtools.gedcomx.conversion import GedcomConverter
from gedcomtools.gedcomx.gedcomx import GedcomX
from gedcomtools.gedcomx.serialization import Serialization, ResolveStats

SAMPLE_DIR = Path(__file__).parent.parent / ".sample_data"


@pytest.fixture(scope="module")
def tiny_gx():
    p = Gedcom5x()
    p.parse_file(str(SAMPLE_DIR / "555SAMPLE.GED"))
    return GedcomConverter().Gedcom5x_GedcomX(p)


@pytest.fixture(scope="module")
def small_gx():
    p = Gedcom5x()
    p.parse_file(str(SAMPLE_DIR / "Sui_Dynasty.ged"))
    return GedcomConverter().Gedcom5x_GedcomX(p)


@pytest.fixture(scope="module")
def tiny_roundtrip(tiny_gx):
    raw = json.loads(tiny_gx.json)
    gx2 = Serialization.deserialize(raw, GedcomX)
    return tiny_gx, gx2


# ---------------------------------------------------------------------------
# Serialization produces valid output
# ---------------------------------------------------------------------------

class TestSerialization:
    def test_json_is_bytes(self, tiny_gx):
        assert isinstance(tiny_gx.json, bytes)

    def test_json_is_valid(self, tiny_gx):
        data = json.loads(tiny_gx.json)
        assert isinstance(data, dict)

    def test_json_has_persons(self, tiny_gx):
        data = json.loads(tiny_gx.json)
        assert "persons" in data
        assert len(data["persons"]) > 0

    def test_serialized_persons_have_ids(self, tiny_gx):
        data = json.loads(tiny_gx.json)
        for p in data["persons"]:
            assert p.get("id"), f"Person missing id: {p}"

    def test_serialized_persons_have_names(self, tiny_gx):
        data = json.loads(tiny_gx.json)
        for p in data["persons"]:
            assert p.get("names"), f"Person {p.get('id')} has no names"

    def test_serialized_relationships_have_person1(self, tiny_gx):
        data = json.loads(tiny_gx.json)
        for r in data.get("relationships", []):
            assert r.get("person1"), f"Relationship missing person1: {r}"

    def test_all_values_json_serialisable(self, tiny_gx):
        """orjson produced the bytes — verify std json can also parse them."""
        raw = tiny_gx.json.decode("utf-8")
        parsed = json.loads(raw)
        json.dumps(parsed)  # must not raise


# ---------------------------------------------------------------------------
# Round-trip: JSON → GedcomX preserves record counts
# ---------------------------------------------------------------------------

class TestRoundTrip:
    def test_persons_count_preserved(self, tiny_roundtrip):
        gx1, gx2 = tiny_roundtrip
        assert len(gx2.persons) == len(gx1.persons)

    def test_relationships_count_preserved(self, tiny_roundtrip):
        gx1, gx2 = tiny_roundtrip
        assert len(gx2.relationships) == len(gx1.relationships)

    def test_sources_count_preserved(self, tiny_roundtrip):
        gx1, gx2 = tiny_roundtrip
        assert len(gx2.sourceDescriptions) == len(gx1.sourceDescriptions)

    def test_agents_count_preserved(self, tiny_roundtrip):
        gx1, gx2 = tiny_roundtrip
        assert len(gx2.agents) == len(gx1.agents)

    def test_double_roundtrip_stable(self, tiny_roundtrip):
        """Serialise the round-tripped result again — counts must still match."""
        gx1, gx2 = tiny_roundtrip
        raw2 = json.loads(gx2.json)
        gx3 = Serialization.deserialize(raw2, GedcomX)
        assert len(gx3.persons) == len(gx1.persons)
        assert len(gx3.relationships) == len(gx1.relationships)


# ---------------------------------------------------------------------------
# Reference resolution
# ---------------------------------------------------------------------------

class TestReferenceResolution:
    def test_resolve_runs_without_error(self, tiny_roundtrip):
        _, gx2 = tiny_roundtrip
        stats = ResolveStats()
        Serialization._resolve_structure(gx2, gx2._resolve, stats=stats)

    def test_no_resolution_failures(self, tiny_roundtrip):
        _, gx2 = tiny_roundtrip
        stats = ResolveStats()
        Serialization._resolve_structure(gx2, gx2._resolve, stats=stats)
        assert stats.resolved_fail == 0, (
            f"{stats.resolved_fail} reference(s) failed to resolve"
        )


# ---------------------------------------------------------------------------
# Larger file: Sui Dynasty
# ---------------------------------------------------------------------------

class TestSmallFile:
    def test_sui_dynasty_converts(self, small_gx):
        assert len(small_gx.persons) > 0

    def test_sui_dynasty_json_valid(self, small_gx):
        data = json.loads(small_gx.json)
        assert isinstance(data, dict)
        assert "persons" in data

    def test_sui_dynasty_roundtrip_persons(self, small_gx):
        raw = json.loads(small_gx.json)
        gx2 = Serialization.deserialize(raw, GedcomX)
        assert len(gx2.persons) == len(small_gx.persons)
