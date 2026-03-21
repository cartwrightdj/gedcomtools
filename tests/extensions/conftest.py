"""
Shared fixtures for the GedcomX extension test suite.
"""
import pytest


@pytest.fixture(scope="session", autouse=True)
def load_all_plugins():
    """Load all GedcomX extensions once for the entire extensions test session."""
    from gedcomtools.gedcomx.extensible import plugin_registry, TrustLevel

    plugin_registry.set_trust_level(TrustLevel.BUILTIN)
    plugin_registry.allow("gedcomtools.gedcomx.extensions.fs")
    plugin_registry.allow("gedcomtools.gedcomx.extensions.rs10")
    plugin_registry.allow("gedcomtools.gedcomx.extensions.test")
    result = plugin_registry.load()
    assert result["errors"] == {}, f"Plugin load errors: {result['errors']}"
    return result
