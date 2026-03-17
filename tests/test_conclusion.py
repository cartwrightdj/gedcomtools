"""
Tests for gedcomtools.gedcomx.conclusion.Conclusion
Covers: add_source_reference() ValueError, add_note(), equality.
"""
import pytest
from gedcomtools.gedcomx.conclusion import Conclusion
from gedcomtools.gedcomx.source_reference import SourceReference
from gedcomtools.gedcomx.source_description import SourceDescription
from gedcomtools.gedcomx.note import Note
from gedcomtools.gedcomx.uri import URI


class TestConclusionAddSourceReference:
    def test_add_source_reference_ok(self):
        c = Conclusion()
        sr = SourceReference(description=SourceDescription(id="SD1"))
        c.add_source_reference(sr)
        assert sr in c.sources

    def test_add_source_reference_duplicate_is_skipped(self):
        c = Conclusion()
        sr = SourceReference(description=SourceDescription(id="SD1"))
        c.add_source_reference(sr)
        c.add_source_reference(sr)
        assert c.sources.count(sr) == 1

    def test_add_source_reference_raises_for_wrong_type(self):
        """Regression: add_source_reference() must raise ValueError with a message for non-SourceReference."""
        c = Conclusion()
        with pytest.raises(ValueError) as exc_info:
            c.add_source_reference("not a source reference")
        assert "SourceReference" in str(exc_info.value)

    def test_add_source_reference_raises_for_none(self):
        """add_source_reference(None) must raise ValueError."""
        c = Conclusion()
        with pytest.raises(ValueError):
            c.add_source_reference(None)

    def test_add_source_reference_raises_for_dict(self):
        c = Conclusion()
        with pytest.raises(ValueError):
            c.add_source_reference({"description": "https://example.com"})

    def test_add_multiple_source_references(self):
        """Use SourceDescription as description (has _uri) to ensure distinct equality."""
        c = Conclusion()
        sd1 = SourceDescription(id="S1")
        sd2 = SourceDescription(id="S2")
        sr1 = SourceReference(description=sd1)
        sr2 = SourceReference(description=sd2)
        c.add_source_reference(sr1)
        c.add_source_reference(sr2)
        assert len(c.sources) == 2


class TestConclusionAddNote:
    def test_add_note_ok(self):
        c = Conclusion()
        n = Note(text="A genealogical note.")
        c.add_note(n)
        assert n in c.notes

    def test_add_note_duplicate_returns_false(self):
        c = Conclusion()
        n = Note(text="A note.")
        c.add_note(n)
        result = c.add_note(n)
        assert result is False

    def test_add_note_raises_for_non_note(self):
        c = Conclusion()
        with pytest.raises(ValueError):
            c.add_note("not a note")

    def test_add_note_raises_for_none(self):
        c = Conclusion()
        with pytest.raises(ValueError):
            c.add_note(None)


class TestConclusionEquality:
    def test_equal_conclusions_same_id(self):
        c1 = Conclusion(id="C1")
        c2 = Conclusion(id="C1")
        assert c1 == c2

    def test_not_equal_different_id(self):
        c1 = Conclusion(id="C1")
        c2 = Conclusion(id="C2")
        assert c1 != c2

    def test_not_equal_different_class(self):
        c = Conclusion(id="C1")
        assert c != "not a conclusion"
