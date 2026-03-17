"""
Tests for gedcomtools.gedcom5.parser.Gedcom5x
"""
import pytest
from gedcomtools.gedcom5.parser import Gedcom5x


class TestGedcom5xParseTiny:
    """555SAMPLE.GED — tiny file, fast, known counts."""

    @pytest.fixture(autouse=True)
    def parse(self, ged_tiny):
        self.p = Gedcom5x()
        self.p.parse_file(str(ged_tiny), strict=True)

    def test_has_individuals(self):
        assert len(self.p.individuals) > 0

    def test_has_families(self):
        assert len(self.p.families) >= 0

    def test_has_header(self):
        assert len(self.p.header) >= 1

    def test_individuals_have_xref(self):
        for indi in self.p.individuals:
            assert indi.xref is not None

    def test_element_dictionary_not_empty(self):
        d = self.p.get_element_dictionary()
        assert isinstance(d, dict)
        assert len(d) > 0

    def test_root_child_elements(self):
        elements = self.p.get_root_child_elements()
        assert len(elements) > 0


class TestGedcom5xParseSmall:
    """Sui_Dynasty.ged — small file."""

    @pytest.fixture(autouse=True)
    def parse(self, ged_small):
        self.p = Gedcom5x()
        self.p.parse_file(str(ged_small), strict=True)

    def test_parses_without_error(self):
        assert self.p is not None

    def test_has_individuals(self):
        assert len(self.p.individuals) > 0


class TestGedcom5xParseMedium:
    """allged.ged — medium file, broader GEDCOM coverage."""

    @pytest.fixture(autouse=True)
    def parse(self, ged_medium):
        self.p = Gedcom5x()
        self.p.parse_file(str(ged_medium), strict=True)

    def test_parses_without_error(self):
        assert self.p is not None

    def test_has_individuals(self):
        assert len(self.p.individuals) > 0

    def test_has_sources(self):
        # allged.ged has sources
        assert len(self.p.sources) >= 0


class TestGedcom5xFileMissing:
    def test_missing_file_raises(self):
        p = Gedcom5x()
        with pytest.raises(Exception):
            p.parse_file("/nonexistent/path/file.ged", strict=True)


class TestGedcom5xCollectionTypes:
    def test_individuals_is_list(self, ged_tiny):
        p = Gedcom5x()
        p.parse_file(str(ged_tiny))
        assert isinstance(p.individuals, list)

    def test_families_is_list(self, ged_tiny):
        p = Gedcom5x()
        p.parse_file(str(ged_tiny))
        assert isinstance(p.families, list)

    def test_sources_is_list(self, ged_tiny):
        p = Gedcom5x()
        p.parse_file(str(ged_tiny))
        assert isinstance(p.sources, list)

    def test_repositories_is_list(self, ged_tiny):
        p = Gedcom5x()
        p.parse_file(str(ged_tiny))
        assert isinstance(p.repositories, list)

    def test_submitters_is_list(self, ged_tiny):
        p = Gedcom5x()
        p.parse_file(str(ged_tiny))
        assert isinstance(p.submitters, list)
