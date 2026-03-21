"""
Shared fixtures for the GedcomX extension test suite.
"""
import pytest


@pytest.fixture(scope="session", autouse=True)
def load_all_plugins():
    """Load all GedcomX extensions once for the entire extensions test session."""
    from gedcomtools.gedcomx.extensible import import_plugins
    result = import_plugins("gedcomx")
    assert result["errors"] == {}, f"Plugin load errors: {result['errors']}"
    return result
