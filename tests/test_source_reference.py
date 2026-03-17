"""
Tests for gedcomtools.gedcomx.source_reference.SourceReference
Covers: append(), add_qualifier(), __eq__, construction.
"""
import pytest
from gedcomtools.gedcomx.source_reference import SourceReference, KnownSourceReference
from gedcomtools.gedcomx.qualifier import Qualifier
from gedcomtools.gedcomx.source_description import SourceDescription
from gedcomtools.gedcomx.uri import URI


class TestSourceReferenceConstruction:
    def test_default_construction(self):
        sr = SourceReference()
        assert sr.description is None
        assert sr.descriptionId is None
        assert sr.qualifiers == []

    def test_with_description_id(self):
        sr = SourceReference(descriptionId="S1")
        assert sr.descriptionId == "S1"

    def test_with_uri_description(self):
        uri = URI(value="https://example.com/src/1")
        sr = SourceReference(description=uri)
        assert sr.description is uri


class TestSourceReferenceAppend:
    def test_append_sets_description_id_when_none(self):
        """Regression: append() must set descriptionId when it was None (dead code fixed)."""
        sr = SourceReference()
        sr.append("S1")
        assert sr.descriptionId == "S1"

    def test_append_concatenates_when_existing(self):
        sr = SourceReference(descriptionId="S1")
        sr.append("-extra")
        assert sr.descriptionId == "S1-extra"

    def test_append_multiple_times(self):
        sr = SourceReference()
        sr.append("part1")
        sr.append("part2")
        assert sr.descriptionId == "part1part2"

    def test_append_none_raises_value_error(self):
        """append(None) must raise ValueError."""
        sr = SourceReference()
        with pytest.raises(ValueError):
            sr.append(None)

    def test_append_empty_string_raises_value_error(self):
        """append('') must raise ValueError."""
        sr = SourceReference()
        with pytest.raises(ValueError):
            sr.append("")

    def test_append_non_string_raises_value_error(self):
        sr = SourceReference()
        with pytest.raises(ValueError):
            sr.append(42)


class TestSourceReferenceEq:
    def test_equal_same_source_description(self):
        """Two SourceReferences pointing to the same SourceDescription are equal."""
        sd = SourceDescription(id="SD1")
        sr1 = SourceReference(description=sd)
        sr2 = SourceReference(description=sd)
        assert sr1 == sr2

    def test_not_equal_different_source_descriptions(self):
        """Two SourceReferences pointing to different SourceDescriptions are not equal."""
        sr1 = SourceReference(description=SourceDescription(id="SD1"))
        sr2 = SourceReference(description=SourceDescription(id="SD2"))
        assert sr1 != sr2

    def test_not_equal_different_class(self):
        sr = SourceReference(descriptionId="S1")
        assert sr != "not a source reference"

    def test_equal_both_no_description(self):
        """Two SourceReferences with no description both have _uri=None and compare equal."""
        sr1 = SourceReference()
        sr2 = SourceReference()
        assert sr1 == sr2
