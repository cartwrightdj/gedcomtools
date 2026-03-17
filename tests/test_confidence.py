"""
Tests for gedcomtools.gedcomx.conclusion.ConfidenceLevel.from_json
"""
import pytest
from gedcomtools.gedcomx.conclusion import ConfidenceLevel


def _value(cl):
    """ConfidenceLevel.from_json returns a ConfidenceLevel instance; .value holds the canonical URI."""
    return getattr(cl, "value", cl)


class TestConfidenceLevelFromJson:
    def test_short_name_high(self):
        cl = ConfidenceLevel.from_json("High", None)
        assert _value(cl) == ConfidenceLevel.High

    def test_short_name_medium(self):
        cl = ConfidenceLevel.from_json("Medium", None)
        assert _value(cl) == ConfidenceLevel.Medium

    def test_short_name_low(self):
        cl = ConfidenceLevel.from_json("Low", None)
        assert _value(cl) == ConfidenceLevel.Low

    def test_case_insensitive_lower(self):
        assert _value(ConfidenceLevel.from_json("high", None)) == ConfidenceLevel.High

    def test_case_insensitive_upper(self):
        assert _value(ConfidenceLevel.from_json("HIGH", None)) == ConfidenceLevel.High

    def test_case_insensitive_medium(self):
        assert _value(ConfidenceLevel.from_json("MEDIUM", None)) == ConfidenceLevel.Medium

    def test_full_uri_high(self):
        cl = ConfidenceLevel.from_json("http://gedcomx.org/High", None)
        assert _value(cl) == ConfidenceLevel.High

    def test_full_uri_medium(self):
        cl = ConfidenceLevel.from_json("http://gedcomx.org/Medium", None)
        assert _value(cl) == ConfidenceLevel.Medium

    def test_full_uri_low(self):
        cl = ConfidenceLevel.from_json("http://gedcomx.org/Low", None)
        assert _value(cl) == ConfidenceLevel.Low

    def test_dict_confidence_key(self):
        cl = ConfidenceLevel.from_json({"confidence": "High"}, None)
        assert _value(cl) == ConfidenceLevel.High

    def test_dict_type_key(self):
        cl = ConfidenceLevel.from_json({"type": "Medium"}, None)
        assert _value(cl) == ConfidenceLevel.Medium

    def test_dict_value_key(self):
        cl = ConfidenceLevel.from_json({"value": "Low"}, None)
        assert _value(cl) == ConfidenceLevel.Low

    def test_dict_level_key(self):
        cl = ConfidenceLevel.from_json({"level": "High"}, None)
        assert _value(cl) == ConfidenceLevel.High

    def test_dict_uri_key(self):
        cl = ConfidenceLevel.from_json({"uri": "http://gedcomx.org/Medium"}, None)
        assert _value(cl) == ConfidenceLevel.Medium

    def test_none_returns_none(self):
        cl = ConfidenceLevel.from_json(None, None)
        assert cl is None

    def test_existing_instance_passthrough(self):
        # from_json on a ConfidenceLevel instance returns it unchanged
        original = ConfidenceLevel.from_json("High", None)
        result = ConfidenceLevel.from_json(original, None)
        assert _value(result) == ConfidenceLevel.High

    def test_unknown_string_raises(self):
        with pytest.raises(ValueError):
            ConfidenceLevel.from_json("bogus", None)

    def test_description_high(self):
        cl = ConfidenceLevel.from_json("High", None)
        assert "high" in cl.description.lower()

    def test_description_medium(self):
        cl = ConfidenceLevel.from_json("Medium", None)
        assert "medium" in cl.description.lower()

    def test_description_low(self):
        cl = ConfidenceLevel.from_json("Low", None)
        assert "low" in cl.description.lower()
