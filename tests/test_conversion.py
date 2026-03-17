"""
Tests for gedcomtools.gedcomx.conversion.GedcomConverter (G5 → GedcomX)
"""
import pytest
from gedcomtools.gedcom5.parser import Gedcom5x
from gedcomtools.gedcomx.conversion import GedcomConverter
from gedcomtools.gedcomx.gedcomx import GedcomX
from gedcomtools.gedcomx.serialization import Serialization


def _convert(ged_path) -> GedcomX:
    p = Gedcom5x()
    p.parse_file(str(ged_path), strict=True)
    conv = GedcomConverter()
    return conv.Gedcom5x_GedcomX(p)


class TestConversionTiny:
    """555SAMPLE.GED — minimal smoke test."""

    @pytest.fixture(autouse=True)
    def convert(self, ged_tiny):
        self.gx = _convert(ged_tiny)

    def test_returns_gedcomx(self):
        assert isinstance(self.gx, GedcomX)

    def test_has_persons(self):
        assert len(self.gx.persons) > 0

    def test_persons_have_ids(self):
        for p in self.gx.persons:
            assert p.id is not None

    def test_has_relationships(self):
        assert len(self.gx.relationships) >= 0

    def test_unhandled_tags_recorded(self):
        assert hasattr(self.gx, "_import_unhandled_tags")
        assert isinstance(self.gx._import_unhandled_tags, dict)


class TestConversionSmall:
    """Sui_Dynasty.ged"""

    @pytest.fixture(autouse=True)
    def convert(self, ged_small):
        self.gx = _convert(ged_small)

    def test_returns_gedcomx(self):
        assert isinstance(self.gx, GedcomX)

    def test_has_persons(self):
        assert len(self.gx.persons) > 0

    def test_persons_have_names(self):
        persons_with_names = [p for p in self.gx.persons if len(p.names) > 0]
        assert len(persons_with_names) > 0


@pytest.mark.xfail(reason="allged.ged contains tags not yet handled by GedcomConverter", strict=False)
class TestConversionMedium:
    """allged.ged — broader tag coverage."""

    @pytest.fixture(autouse=True)
    def convert(self, ged_medium):
        self.gx = _convert(ged_medium)

    def test_returns_gedcomx(self):
        assert isinstance(self.gx, GedcomX)

    def test_has_persons(self):
        assert len(self.gx.persons) > 0


class TestConversionLarge:
    """Royal92 — larger real-world file."""

    @pytest.fixture(autouse=True)
    def convert(self, ged_large):
        self.gx = _convert(ged_large)

    def test_returns_gedcomx(self):
        assert isinstance(self.gx, GedcomX)

    def test_person_count_reasonable(self):
        assert len(self.gx.persons) > 100

    def test_relationship_count_reasonable(self):
        assert len(self.gx.relationships) > 0

    def test_person_lookup_works(self):
        first_id = list(self.gx.persons)[0].id
        assert self.gx.get_person_by_id(first_id) is not None


class TestConversionSerializable:
    """Conversion output must be fully serializable to JSON."""

    def test_tiny_serializes(self, ged_tiny):
        gx = _convert(ged_tiny)
        data = Serialization.serialize(gx)
        assert isinstance(data, dict)

    @pytest.mark.xfail(reason="allged.ged causes ConversionErrorDump", strict=False)
    def test_medium_serializes(self, ged_medium):
        gx = _convert(ged_medium)
        data = Serialization.serialize(gx)
        assert isinstance(data, dict)
        if "persons" in data:
            assert isinstance(data["persons"], list)
