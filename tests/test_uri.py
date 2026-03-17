"""
Tests for gedcomtools.gedcomx.uri.URI
"""
import pytest
from gedcomtools.gedcomx.uri import URI


class TestURIConstruction:
    def test_from_value_string(self):
        u = URI(value="https://example.com/path?q=1#frag")
        assert u.scheme == "https"
        assert u.authority == "example.com"
        assert u.path == "/path"
        assert u.query == "q=1"
        assert u.fragment == "frag"

    def test_from_components(self):
        u = URI(scheme="http", authority="example.com", path="/foo")
        assert u.scheme == "http"
        assert u.authority == "example.com"
        assert u.path == "/foo"

    def test_fragment_only(self):
        u = URI(fragment="abc123")
        assert u.fragment == "abc123"

    def test_from_url_factory(self):
        u = URI.from_url("https://gedcomx.org/v1/Person")
        assert u.scheme == "https"
        assert u.authority == "gedcomx.org"
        assert u.path == "/v1/Person"

    def test_default_scheme_applied_on_value_without_scheme(self):
        u = URI(value="//example.com/path")
        # urlsplit returns empty scheme for //example.com/path
        assert u.scheme == "gedcomx"

    def test_no_args_raises(self):
        with pytest.raises(ValueError):
            URI()

    def test_str_round_trip(self):
        url = "https://example.com/path"
        u = URI(value=url)
        assert "example.com" in str(u)
        assert "/path" in str(u)

    def test_value_property_none_when_empty_after_target(self):
        # A URI with only a fragment should still have a value
        u = URI(fragment="someId")
        assert u.value is not None

    def test_target_with_id_attribute(self):
        class FakeObj:
            id = "person-1"
        u = URI(target=FakeObj())
        assert u.fragment == "person-1"

    def test_target_string(self):
        u = URI(target="https://example.com/resource")
        assert u.authority == "example.com"

    def test_from_url_matches_value_construction(self):
        url = "https://api.familysearch.org/platform/tree/persons/KPHP-4B4"
        u1 = URI.from_url(url)
        u2 = URI(value=url)
        assert str(u1) == str(u2)


class TestURIValue:
    def test_value_returns_string(self):
        u = URI(scheme="https", authority="example.com", path="/foo")
        assert isinstance(u.value, str)
        assert "example.com" in u.value

    def test_split_returns_split_result(self):
        from urllib.parse import SplitResult
        u = URI(value="https://example.com/path")
        assert isinstance(u.split(), SplitResult)

    def test_repr_contains_components(self):
        u = URI(scheme="https", authority="example.com", path="/foo")
        r = repr(u)
        assert "example.com" in r
        assert "/foo" in r
