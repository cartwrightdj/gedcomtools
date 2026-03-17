"""
Tests for gedcomtools.gedcomx.textvalue.TextValue
"""
import pytest
from gedcomtools.gedcomx.textvalue import TextValue


class TestTextValueConstruction:
    def test_basic(self):
        tv = TextValue(value="Hello")
        assert tv.value == "Hello"
        assert tv.lang is None

    def test_with_lang(self):
        tv = TextValue(value="Hello", lang="en")
        assert tv.lang == "en"

    def test_no_args(self):
        tv = TextValue()
        assert tv.value is None
        assert tv.lang is None

    def test_lang_stored_as_given(self):
        tv = TextValue(value="Bonjour", lang="FR")
        assert tv.lang == "FR"

    def test_lang_stored_as_given_mixed_case(self):
        tv = TextValue(value="text", lang="En-US")
        assert tv.lang == "En-US"


class TestTextValueEquality:
    def test_equal_same_value_no_lang(self):
        assert TextValue(value="Hello") == TextValue(value="Hello")

    def test_equal_same_value_same_lang(self):
        assert TextValue(value="Hello", lang="en") == TextValue(value="Hello", lang="en")

    def test_equal_lang_case_insensitive(self):
        assert TextValue(value="Hello", lang="EN") == TextValue(value="Hello", lang="en")

    def test_not_equal_different_value(self):
        assert TextValue(value="Hello") != TextValue(value="World")

    def test_not_equal_different_lang(self):
        assert TextValue(value="Hello", lang="en") != TextValue(value="Hello", lang="fr")

    def test_not_equal_to_string(self):
        assert TextValue(value="Hello") != "Hello"


class TestTextValueKey:
    def test_key_is_tuple(self):
        tv = TextValue(value="Hello", lang="en")
        k = tv._key()
        assert isinstance(k, tuple)

    def test_key_lang_normalized(self):
        tv1 = TextValue(value="Hello", lang="EN")
        tv2 = TextValue(value="Hello", lang="en")
        assert tv1._key() == tv2._key()

    def test_key_none_lang(self):
        tv = TextValue(value="Hello")
        k = tv._key()
        assert k is not None


class TestTextValueMutability:
    def test_append_to_value(self):
        tv = TextValue(value="Hello")
        tv._append_to_value("World")
        assert tv.value == "Hello World"

    def test_append_to_none_value(self):
        tv = TextValue()
        tv._append_to_value("text")
        assert "text" in (tv.value or "")


class TestTextValueInstances:
    def test_instances_independent(self):
        """Regression: mutable defaults must not be shared across instances."""
        tv1 = TextValue(value="A")
        tv2 = TextValue(value="B")
        tv1._append_to_value("!")
        assert tv2.value == "B"
