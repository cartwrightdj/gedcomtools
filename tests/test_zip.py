"""
Tests for GedcomZip packaging.

Verifies that a GedcomX object converted from GEDCOM 5 can be
packaged into a zip archive and that the archive is readable and
contains the expected GedcomX JSON resource.

Updates:
  2026-03-29 — added test_gedcomx_named_genealogy and updated
               test_multiple_resources to assert genealogy.json /
               genealogy2.json naming scheme (bug #5 fix)
             — added test_path_uri_builds_directory_structure: verifies
               that an object with an explicit path-based _uri is written
               under the correct directory in the zip archive
"""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest

from gedcomtools.gedcom5.parser import Gedcom5x
from gedcomtools.gedcomx.conversion import GedcomConverter
from gedcomtools.gedcomx.gedcomx import GedcomX
from gedcomtools.gedcomx.person import Person
from gedcomtools.gedcomx.name import QuickName
from gedcomtools.gedcomx.uri import URI
from gedcomtools.gedcomx.zip import GedcomZip

SAMPLE = Path(__file__).parent.parent / ".sample_data" / "gedcom5" / "gedcom5_sample.ged"


@pytest.fixture(scope="module")
def gx():
    p = Gedcom5x()
    p.parse_file(str(SAMPLE))
    gx = GedcomConverter().Gedcom5x_GedcomX(p)
    gx.id = "TEST_ZIP"
    return gx


@pytest.fixture(scope="module")
def zip_bytes(gx, tmp_path_factory):
    """Build a GedcomZip archive in a temp file and return its bytes."""
    path = tmp_path_factory.mktemp("zip") / "test.zip"
    gz = GedcomZip(str(path))
    gz.add_object_as_resource(gx)
    gz.close()
    return path.read_bytes()


# ---------------------------------------------------------------------------
# Archive structure
# ---------------------------------------------------------------------------

class TestZipStructure:
    def test_produces_valid_zip(self, zip_bytes):
        assert zipfile.is_zipfile(io.BytesIO(zip_bytes))

    def test_zip_is_non_empty(self, zip_bytes):
        assert len(zip_bytes) > 0

    def test_zip_contains_at_least_one_file(self, zip_bytes):
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            assert len(zf.namelist()) >= 1

    def test_zip_contains_json_resource(self, zip_bytes):
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            names = zf.namelist()
            json_files = [n for n in names if n.endswith(".json")]
            assert json_files, f"No .json file found in zip. Contents: {names}"


# ---------------------------------------------------------------------------
# Content validity
# ---------------------------------------------------------------------------

class TestZipContent:
    def test_json_resource_is_valid_json(self, zip_bytes):
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            json_files = [n for n in zf.namelist() if n.endswith(".json")]
            data = json.loads(zf.read(json_files[0]))
            assert isinstance(data, dict)

    def test_json_resource_has_persons(self, zip_bytes):
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            json_files = [n for n in zf.namelist() if n.endswith(".json")]
            data = json.loads(zf.read(json_files[0]))
            assert "persons" in data
            assert len(data["persons"]) > 0

    def test_json_resource_has_relationships(self, zip_bytes):
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            json_files = [n for n in zf.namelist() if n.endswith(".json")]
            data = json.loads(zf.read(json_files[0]))
            assert "relationships" in data


# ---------------------------------------------------------------------------
# Context manager usage
# ---------------------------------------------------------------------------

class TestContextManager:
    def test_context_manager_produces_valid_zip(self, gx, tmp_path):
        path = tmp_path / "ctx.zip"
        with GedcomZip(str(path)) as gz:
            gz.add_object_as_resource(gx)
        assert path.exists()
        assert zipfile.is_zipfile(path)

    def test_gedcomx_named_genealogy(self, gx, tmp_path):
        """First GedcomX object must be written as genealogy.json."""
        path = tmp_path / "name.zip"
        with GedcomZip(str(path)) as gz:
            arcname = gz.add_object_as_resource(gx)
        assert arcname == "genealogy.json"

    def test_multiple_resources(self, gx, tmp_path):
        """Adding GedcomX objects twice must produce genealogy.json and genealogy2.json."""
        path = tmp_path / "multi.zip"
        with GedcomZip(str(path)) as gz:
            first = gz.add_object_as_resource(gx)
            second = gz.add_object_as_resource(gx)
        assert first == "genealogy.json"
        assert second == "genealogy2.json"
        with zipfile.ZipFile(path) as zf:
            json_files = [n for n in zf.namelist() if n.endswith(".json")]
            assert "genealogy.json" in json_files
            assert "genealogy2.json" in json_files

    def test_path_uri_builds_directory_structure(self, tmp_path):
        """Object with a path-based _uri must be written under that directory in the zip."""
        from gedcomtools.gedcomx.schemas import SCHEMA
        SCHEMA.set_toplevel(Person)
        try:
            p = Person(id="P1", names=[QuickName("Alice Smith")])
            p._uri = URI(path="/persons/", fragment="P1")

            path = tmp_path / "dirs.zip"
            with GedcomZip(str(path)) as gz:
                arcname = gz.add_object_as_resource(p)

            assert arcname == "persons/P1.json"
            with zipfile.ZipFile(path) as zf:
                assert "persons/P1.json" in zf.namelist()
                data = json.loads(zf.read("persons/P1.json"))
                assert "persons" in data
        finally:
            SCHEMA._toplevel.pop("Person", None)

    def test_read_preserves_gedcomx_root_metadata(self, tmp_path):
        """Reading a genealogy zip should preserve id, description, attribution, and groups."""
        from gedcomtools.gedcomx.attribution import Attribution
        from gedcomtools.gedcomx.group import Group
        from gedcomtools.gedcomx.textvalue import TextValue

        gx = GedcomX(id="G1", description="desc")
        gx.attribution = Attribution(changeMessage="hello")
        gx.groups.append(Group(id="GR1", names=[TextValue(value="Group One")]))

        path = tmp_path / "meta.zip"
        with GedcomZip(str(path)) as gz:
            gz.add_object_as_resource(gx)

        restored = GedcomZip.read(path)
        assert restored.id == "G1"
        assert restored.description == "desc"
        assert restored.attribution is not None
        assert restored.attribution.changeMessage == "hello"
        assert restored.groups.by_id("GR1") is not None

    def test_read_single_top_level_person_resource(self, tmp_path):
        """Reading a zip with only a top-level Person resource should restore that person."""
        from gedcomtools.gedcomx.schemas import SCHEMA

        SCHEMA.set_toplevel(Person)
        try:
            p = Person(id="P1", names=[QuickName("Alice Smith")])
            p._uri = URI(path="/persons/", fragment="P1")

            path = tmp_path / "single-person.zip"
            with GedcomZip(str(path)) as gz:
                gz.add_object_as_resource(p)

            restored = GedcomZip.read(path)
            assert len(restored.persons) == 1
            assert restored.persons.by_id("P1") is not None
        finally:
            SCHEMA._toplevel.pop("Person", None)
