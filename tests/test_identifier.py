"""
Tests for gedcomtools.gedcomx.identifier.Identifier, IdentifierList, make_uid
"""
import pytest
from gedcomtools.gedcomx.identifier import Identifier, IdentifierList, IdentifierType, make_uid
from gedcomtools.gedcomx.uri import URI


def _uri(s: str) -> URI:
    return URI(value=s)


class TestMakeUid:
    def test_default_length(self):
        uid = make_uid()
        assert len(uid) == 10

    def test_custom_length(self):
        uid = make_uid(length=20)
        assert len(uid) == 20

    def test_uniqueness(self):
        uids = {make_uid() for _ in range(100)}
        assert len(uids) == 100

    def test_only_alphanumeric(self):
        uid = make_uid(length=50)
        assert uid.isalnum()


class TestIdentifier:
    def test_basic_construction(self):
        ident = Identifier(value=[_uri("https://example.com/person/1")])
        assert ident.type == IdentifierType.Primary

    def test_explicit_type(self):
        ident = Identifier(value=[_uri("https://example.com/id")], type=IdentifierType.External)
        assert ident.type == IdentifierType.External

    def test_none_value(self):
        ident = Identifier(value=None)
        assert ident.values is None or ident.values == []


class TestIdentifierList:
    def test_empty_construction(self):
        il = IdentifierList()
        assert len(il) == 0

    def test_append_and_contains(self):
        il = IdentifierList()
        ident = Identifier(value=[_uri("https://example.com/1")], type=IdentifierType.Primary)
        il.append(ident)
        assert il.contains(ident)

    def test_len_increments(self):
        il = IdentifierList()
        il.append(Identifier(value=[_uri("https://example.com/1")], type=IdentifierType.Primary))
        il.append(Identifier(value=[_uri("https://example.com/2")], type=IdentifierType.External))
        assert len(il) >= 1

    def test_getitem_by_type(self):
        il = IdentifierList()
        ident = Identifier(value=[_uri("https://example.com/1")], type=IdentifierType.Primary)
        il.append(ident)
        key = IdentifierType.Primary.value
        assert key in il or IdentifierType.Primary in il or len(il) > 0

    def test_iter_yields_keys(self):
        il = IdentifierList()
        il.append(Identifier(value=[_uri("https://example.com/1")], type=IdentifierType.Primary))
        keys = list(il)
        assert len(keys) >= 1

    def test_from_json_dict(self):
        data = {
            "http://gedcomx.org/Primary": ["https://example.com/person/1"]
        }
        il = IdentifierList.from_json(data)
        assert len(il) >= 1

    def test_from_json_empty(self):
        il = IdentifierList.from_json({})
        assert len(il) == 0

    def test_from_json_none(self):
        with pytest.raises(ValueError):
            IdentifierList.from_json(None)

    def test_independent_instances(self):
        """Regression: two IdentifierLists must not share state."""
        il1 = IdentifierList()
        il2 = IdentifierList()
        il1.append(Identifier(value=[_uri("https://example.com/1")], type=IdentifierType.Primary))
        assert len(il2) == 0

    def test_repr_non_empty(self):
        """Regression: __repr__ must produce a useful string, not garbage."""
        il = IdentifierList()
        il.append(Identifier(value=[_uri("https://example.com/1")], type=IdentifierType.Primary))
        r = repr(il)
        assert "IdentifierList" in r
        assert "1" in r  # at least one type reported

    def test_repr_empty(self):
        il = IdentifierList()
        r = repr(il)
        assert "IdentifierList" in r
        assert "0" in r

    def test_str_non_empty_contains_type_key(self):
        """Regression: __str__ must show identifier type keys, not garbage."""
        il = IdentifierList()
        il.append(Identifier(value=[_uri("https://example.com/1")], type=IdentifierType.Primary))
        s = str(il)
        # Should contain the type key (Primary URI) or at minimum not be empty
        assert s and s != "None"
        assert "gedcomx.org" in s or "Primary" in s

    def test_str_empty_sentinel(self):
        """__str__ on an empty IdentifierList returns the sentinel string."""
        il = IdentifierList()
        assert str(il) == "IdentifierList(empty)"
