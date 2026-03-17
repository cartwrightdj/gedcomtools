"""
Tests for gedcomtools.gedcomx.note.Note
Covers: construction, append(), equality, ValueError on invalid input.
"""
import pytest
from gedcomtools.gedcomx.note import Note


class TestNoteConstruction:
    def test_default_lang(self):
        n = Note()
        assert n.lang == "en"

    def test_with_text(self):
        n = Note(text="Some genealogical note.")
        assert n.text == "Some genealogical note."

    def test_with_subject(self):
        n = Note(subject="Birth record")
        assert n.subject == "Birth record"

    def test_no_text_is_none(self):
        n = Note()
        assert n.text is None


class TestNoteAppend:
    def test_append_to_empty_note(self):
        n = Note()
        n.append("Hello")
        assert n.text == "Hello"

    def test_append_to_existing_text(self):
        n = Note(text="Hello")
        n.append(" world")
        assert n.text == "Hello world"

    def test_append_multiple(self):
        n = Note()
        n.append("Line 1")
        n.append(" Line 2")
        assert n.text == "Line 1 Line 2"

    def test_append_none_raises_value_error(self):
        """Regression: append(None) must raise ValueError (was unreachable before the fix)."""
        n = Note()
        with pytest.raises(ValueError):
            n.append(None)

    def test_append_empty_string_raises_value_error(self):
        """Regression: append('') must raise ValueError."""
        n = Note()
        with pytest.raises(ValueError):
            n.append("")

    def test_append_integer_raises_value_error(self):
        """Regression: append(42) must raise ValueError."""
        n = Note()
        with pytest.raises(ValueError):
            n.append(42)


class TestNoteEquality:
    def test_equal_notes(self):
        n1 = Note(lang="en", subject="Birth", text="Note text")
        n2 = Note(lang="en", subject="Birth", text="Note text")
        assert n1 == n2

    def test_different_text_not_equal(self):
        n1 = Note(text="A")
        n2 = Note(text="B")
        assert n1 != n2

    def test_different_subject_not_equal(self):
        n1 = Note(subject="Birth", text="text")
        n2 = Note(subject="Death", text="text")
        assert n1 != n2

    def test_lang_case_insensitive(self):
        n1 = Note(lang="EN", text="text")
        n2 = Note(lang="en", text="text")
        assert n1 == n2

    def test_not_equal_to_non_note(self):
        n = Note(text="text")
        result = n.__eq__("not a note")
        assert result is NotImplemented
