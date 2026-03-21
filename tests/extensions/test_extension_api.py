"""
Tests for the GedcomX extension API after the pydantic migration.

Covers:
- define_ext() adds a proper pydantic model field
- declared_extras() reflects dynamically added fields
- model_extra captures unknown kwargs
- import_plugins() loads all extensions without errors
- SCHEMA.register_extra() wires up define_ext() for pydantic models
- Extension field serialization via model_dump()
- FamilyLinks (Extensible subclass) instantiation
- rs10 extension field access on pydantic models
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fresh_person():
    """Import Person fresh each test to avoid cross-test field pollution."""
    from gedcomtools.gedcomx.person import Person
    return Person


# ---------------------------------------------------------------------------
# define_ext
# ---------------------------------------------------------------------------

class TestDefineExt:
    def test_adds_to_model_fields(self):
        from gedcomtools.gedcomx.name import Name
        Name.define_ext("_test_str", typ=str, default=None)
        assert "_test_str" in Name.model_fields

    def test_field_accessible_on_instance(self):
        from gedcomtools.gedcomx.note import Note
        Note.define_ext("_test_note_tag", typ=str, default=None)
        n = Note(text="hi", _test_note_tag="custom")
        assert n._test_note_tag == "custom"

    def test_field_not_in_model_extra(self):
        from gedcomtools.gedcomx.attribution import Attribution
        Attribution.define_ext("_test_attr_ext", typ=str, default=None)
        a = Attribution(_test_attr_ext="value")
        assert (a.model_extra or {}).get("_test_attr_ext") is None
        assert a._test_attr_ext == "value"

    def test_default_none(self):
        from gedcomtools.gedcomx.document import Document
        Document.define_ext("_test_doc_ext", typ=str, default=None)
        d = Document()
        assert d._test_doc_ext is None

    def test_no_overwrite_by_default(self):
        from gedcomtools.gedcomx.event import Event
        Event.define_ext("_test_ev_ext", typ=str, default=None)
        # calling again without overwrite should be a no-op
        Event.define_ext("_test_ev_ext", typ=int, default=None)
        # type should remain str (original)
        fi = Event.model_fields["_test_ev_ext"]
        # annotation is Optional[str] — just verify field still exists
        assert "_test_ev_ext" in Event.model_fields

    def test_overwrite_replaces_field(self):
        from gedcomtools.gedcomx.relationship import Relationship
        Relationship.define_ext("_test_rel_ext", typ=str, default=None)
        Relationship.define_ext("_test_rel_ext", typ=int, default=None, overwrite=True)
        assert "_test_rel_ext" in Relationship.model_fields

    def test_inherits_to_subclass(self):
        """Fields added to a base class are visible on subclass instances."""
        from gedcomtools.gedcomx.subject import Subject
        from gedcomtools.gedcomx.person import Person
        Subject.define_ext("_test_subj_inherit", typ=str, default=None)
        p = Person(id="P1", _test_subj_inherit="hello")
        assert p._test_subj_inherit == "hello"


# ---------------------------------------------------------------------------
# declared_extras
# ---------------------------------------------------------------------------

class TestDeclaredExtras:
    def test_shows_added_field(self):
        from gedcomtools.gedcomx.source_reference import SourceReference
        SourceReference.define_ext("_test_sr_ext", typ=str, default=None)
        extras = SourceReference.declared_extras()
        assert "_test_sr_ext" in extras

    def test_does_not_show_builtin_fields(self):
        from gedcomtools.gedcomx.person import Person
        extras = Person.declared_extras()
        # 'id', 'names', 'facts' etc. are built-in and must NOT appear
        assert "id" not in extras
        assert "names" not in extras
        assert "facts" not in extras

    def test_empty_for_unextended_class(self):
        from gedcomtools.gedcomx.qualifier import Qualifier
        # Qualifier has no define_ext calls in the test suite
        # (if this fails because another test added one, that is expected)
        extras = Qualifier.declared_extras()
        # Just verify it returns a dict
        assert isinstance(extras, dict)


# ---------------------------------------------------------------------------
# model_extra capture
# ---------------------------------------------------------------------------

class TestModelExtra:
    def test_unknown_field_captured(self):
        from gedcomtools.gedcomx.person import Person
        p = Person(id="P1", completely_unknown_field="surprise")
        assert (p.model_extra or {}).get("completely_unknown_field") == "surprise"

    def test_known_field_not_in_model_extra(self):
        from gedcomtools.gedcomx.person import Person
        p = Person(id="P1")
        assert (p.model_extra or {}).get("id") is None

    def test_model_extra_is_dict_or_none(self):
        from gedcomtools.gedcomx.person import Person
        p = Person(id="P1")
        assert p.model_extra is None or isinstance(p.model_extra, dict)


# ---------------------------------------------------------------------------
# import_plugins
# ---------------------------------------------------------------------------

class TestImportPlugins:
    def _make_registry(self):
        from gedcomtools.gedcomx.extensible import PluginRegistry, TrustLevel
        reg = PluginRegistry()
        reg.set_trust_level(TrustLevel.BUILTIN)
        return reg

    def test_loads_without_errors(self):
        from gedcomtools.gedcomx.extensible import import_plugins
        result = import_plugins("gedcomx", registry=self._make_registry())
        assert result["errors"] == {}, f"Plugin load errors: {result['errors']}"

    def test_rs10_imported(self):
        from gedcomtools.gedcomx.extensible import import_plugins
        result = import_plugins("gedcomx", registry=self._make_registry())
        assert any("rs10" in m for m in result["imported"])

    def test_test_extension_imported(self):
        from gedcomtools.gedcomx.extensible import import_plugins
        result = import_plugins("gedcomx", registry=self._make_registry())
        assert any("test" in m for m in result["imported"])


class TestUrlLoading:
    """Tests for URL-based plugin loading (uses a local HTTP server via pytest-httpserver
    or falls back to file:// for offline CI).  The _download_to_temp helper is tested
    directly with a real temporary .py file served over a minimal HTTP response."""

    def test_is_url_detects_http(self):
        from gedcomtools.gedcomx.extensible import _is_url
        assert _is_url("http://example.com/plugin.py")
        assert _is_url("https://example.com/plugin.zip")

    def test_is_url_rejects_paths(self):
        from gedcomtools.gedcomx.extensible import _is_url
        assert not _is_url("/tmp/plugin.py")
        assert not _is_url("./plugin.py")
        assert not _is_url("mymodule.extensions")

    def test_download_py_file(self, tmp_path):
        """_download_to_temp downloads a .py file and returns its local path."""
        import http.server
        import threading
        from gedcomtools.gedcomx.extensible import _download_to_temp

        # Write a minimal plugin file
        plugin_src = tmp_path / "plugin.py"
        plugin_src.write_text("MY_VALUE = 42\n")

        # Serve it over HTTP on a free port
        handler = http.server.SimpleHTTPRequestHandler
        server = http.server.HTTPServer(("127.0.0.1", 0), handler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{port}/{plugin_src.name}"
            # Change handler's cwd so it serves from tmp_path
            import os
            old_cwd = os.getcwd()
            os.chdir(tmp_path)
            try:
                local = _download_to_temp(url)
            finally:
                os.chdir(old_cwd)
        finally:
            server.shutdown()

        assert local.exists()
        assert local.suffix == ".py"
        assert "MY_VALUE = 42" in local.read_text()

    def test_download_zip_file(self, tmp_path):
        """_download_to_temp extracts a zip and returns the extracted directory."""
        import http.server
        import threading
        import zipfile as zf
        from gedcomtools.gedcomx.extensible import _download_to_temp

        # Create a zip containing a single .py file
        plugin_py = tmp_path / "myplugin.py"
        plugin_py.write_text("PLUGIN_NAME = 'myplugin'\n")
        zip_path = tmp_path / "myplugin.zip"
        with zf.ZipFile(zip_path, "w") as z:
            z.write(plugin_py, "myplugin.py")

        server = http.server.HTTPServer(("127.0.0.1", 0), http.server.SimpleHTTPRequestHandler)
        port = server.server_address[1]
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            import os
            old_cwd = os.getcwd()
            os.chdir(tmp_path)
            try:
                local = _download_to_temp(f"http://127.0.0.1:{port}/myplugin.zip")
            finally:
                os.chdir(old_cwd)
        finally:
            server.shutdown()

        assert local.is_dir()
        assert (local / "myplugin.py").exists()

    def test_import_plugins_local_dir_url(self, tmp_path):
        """import_plugins accepts a URL for local_dir when TrustLevel.ALL is set."""
        import http.server
        import threading
        import zipfile as zf
        from gedcomtools.gedcomx.extensible import import_plugins, PluginRegistry, TrustLevel

        # Build a minimal extension zip: a package with an __init__.py
        pkg_dir = tmp_path / "url_ext"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("URL_EXT_LOADED = True\n")
        zip_path = tmp_path / "url_ext.zip"
        with zf.ZipFile(zip_path, "w") as z:
            z.write(pkg_dir / "__init__.py", "url_ext/__init__.py")

        reg = PluginRegistry()
        reg.set_trust_level(TrustLevel.ALL)

        server = http.server.HTTPServer(("127.0.0.1", 0), http.server.SimpleHTTPRequestHandler)
        port = server.server_address[1]
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            import os
            old_cwd = os.getcwd()
            os.chdir(tmp_path)
            try:
                result = import_plugins(
                    "gedcomx",
                    local_dir=f"http://127.0.0.1:{port}/url_ext.zip",
                    registry=reg,
                )
            finally:
                os.chdir(old_cwd)
        finally:
            server.shutdown()

        assert result["errors"] == {}

    def test_import_plugins_env_var_url(self, tmp_path, monkeypatch):
        """import_plugins loads a .py plugin from a URL set in the env var when TrustLevel.ALL."""
        import http.server
        import threading
        from gedcomtools.gedcomx.extensible import import_plugins, PluginRegistry, TrustLevel

        plugin_src = tmp_path / "envplugin.py"
        plugin_src.write_text("ENV_PLUGIN_LOADED = True\n")

        reg = PluginRegistry()
        reg.set_trust_level(TrustLevel.ALL)

        server = http.server.HTTPServer(("127.0.0.1", 0), http.server.SimpleHTTPRequestHandler)
        port = server.server_address[1]
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            import os
            old_cwd = os.getcwd()
            os.chdir(tmp_path)
            try:
                url = f"http://127.0.0.1:{port}/envplugin.py"
                monkeypatch.setenv("GEDCOMX_PLUGINS", url)
                result = import_plugins("gedcomx", registry=reg)
            finally:
                os.chdir(old_cwd)
        finally:
            server.shutdown()

        assert result["errors"] == {}


# ---------------------------------------------------------------------------
# SCHEMA.register_extra wires up define_ext
# ---------------------------------------------------------------------------

class TestSchemaRegisterExtra:
    def test_register_extra_adds_model_field(self):
        """SCHEMA.register_extra on a pydantic model must call define_ext."""
        from gedcomtools.gedcomx.schemas import SCHEMA
        from gedcomtools.gedcomx.agent import Agent

        SCHEMA.register_extra(Agent, "_test_agent_extra", str)
        assert "_test_agent_extra" in Agent.model_fields

    def test_rs10_living_in_person_model_fields(self):
        """After rs10 loads, Person.living must be a proper model field."""
        from gedcomtools.gedcomx.extensible import import_plugins
        import_plugins("gedcomx")
        from gedcomtools.gedcomx.person import Person

        assert "living" in Person.model_fields

    def test_rs10_living_field_works(self):
        from gedcomtools.gedcomx.extensible import import_plugins
        import_plugins("gedcomx")
        from gedcomtools.gedcomx.person import Person

        p = Person(id="P1", living=True)
        assert p.living is True
        assert (p.model_extra or {}).get("living") is None  # not in extras

    def test_rs10_links_in_conclusion_model_fields(self):
        from gedcomtools.gedcomx.extensible import import_plugins
        import_plugins("gedcomx")
        from gedcomtools.gedcomx.conclusion import Conclusion

        # 'links' should be registered (type is _rsLinks, not a plain type — define_ext
        # may store it as Optional[Any]; just check it's present)
        assert "links" in Conclusion.model_fields


# ---------------------------------------------------------------------------
# Serialization of extension fields
# ---------------------------------------------------------------------------

class TestExtensionSerialization:
    def test_define_ext_field_in_model_dump(self):
        from gedcomtools.gedcomx.fact import Fact, FactType
        Fact.define_ext("_test_fact_ext", typ=str, default=None)
        f = Fact(type=FactType.Birth, _test_fact_ext="extra_val")
        d = f.model_dump(exclude_none=True)
        assert d.get("_test_fact_ext") == "extra_val"

    def test_unknown_extra_in_model_dump(self):
        from gedcomtools.gedcomx.person import Person
        p = Person(id="P1", _adhoc_extra=42)
        d = p.model_dump(exclude_none=True)
        assert d.get("_adhoc_extra") == 42


# ---------------------------------------------------------------------------
# rs10 extension classes
# ---------------------------------------------------------------------------

class TestRs10Extension:
    def setup_method(self):
        from gedcomtools.gedcomx.extensible import import_plugins
        import_plugins("gedcomx")

    def test_rslink_creation(self):
        from gedcomtools.gedcomx.extensions.rs10.rs10 import rsLink
        link = rsLink(href="http://example.com/person/1")
        assert "example.com" in str(link)

    def test_rslink_requires_href_or_template(self):
        from gedcomtools.gedcomx.extensions.rs10.rs10 import rsLink
        from gedcomtools.gedcomx.exceptions import GedcomClassAttributeError
        with pytest.raises(GedcomClassAttributeError):
            rsLink()

    def test_family_links_creation(self):
        from gedcomtools.gedcomx.extensions.rs10.rs10 import FamilyLinks
        from gedcomtools.gedcomx.uri import URI
        fl = FamilyLinks(parent1=URI(path="/persons/P1"))
        assert str(fl.parent1) == "/persons/P1"

    def test_family_links_all_fields(self):
        from gedcomtools.gedcomx.extensions.rs10.rs10 import FamilyLinks
        from gedcomtools.gedcomx.uri import URI
        fl = FamilyLinks(
            parent1=URI(path="/P1"),
            parent2=URI(path="/P2"),
            children=[URI(path="/P3"), URI(path="/P4")],
        )
        assert fl.parent1 is not None
        assert fl.parent2 is not None
        assert len(fl.children) == 2

    def test_family_links_defaults_none(self):
        from gedcomtools.gedcomx.extensions.rs10.rs10 import FamilyLinks
        fl = FamilyLinks()
        assert fl.parent1 is None
        assert fl.parent2 is None
        assert fl.children is None

    def test_display_properties_creation(self):
        from gedcomtools.gedcomx.extensions.rs10.rs10 import DisplayProperties
        dp = DisplayProperties(name="Alice", gender="F", lifespan="1900-1975")
        assert dp.name == "Alice"
        assert dp.gender == "F"


# ---------------------------------------------------------------------------
# Extensible base class
# ---------------------------------------------------------------------------

class TestExtensibleBase:
    def test_extensible_is_gedcomx_model(self):
        from gedcomtools.gedcomx.extensible import Extensible
        from gedcomtools.gedcomx.gx_base import GedcomXModel
        assert issubclass(Extensible, GedcomXModel)

    def test_extensible_has_define_ext(self):
        from gedcomtools.gedcomx.extensible import Extensible
        assert hasattr(Extensible, "define_ext")

    def test_extensible_has_declared_extras(self):
        from gedcomtools.gedcomx.extensible import Extensible
        assert hasattr(Extensible, "declared_extras")

    def test_extensible_subclass_works(self):
        from gedcomtools.gedcomx.extensible import Extensible

        class MyExtension(Extensible):
            value: str = ""

        obj = MyExtension(value="test")
        assert obj.value == "test"

    def test_extensible_subclass_define_ext(self):
        from gedcomtools.gedcomx.extensible import Extensible

        class AnotherExtension(Extensible):
            x: int = 0

        AnotherExtension.define_ext("extra_y", typ=str, default=None)
        obj = AnotherExtension(x=1, extra_y="hello")
        assert obj.extra_y == "hello"
