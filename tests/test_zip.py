"""
Tests for GedcomZip packaging.

Verifies that a GedcomX object converted from GEDCOM 5 can be
packaged into a zip archive and that the archive is readable and
contains the expected GedcomX JSON resource.
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

    def test_multiple_resources(self, gx, tmp_path):
        """Adding the same GedcomX object twice should produce two entries."""
        path = tmp_path / "multi.zip"
        with GedcomZip(str(path)) as gz:
            gz.add_object_as_resource(gx)
            gz.add_object_as_resource(gx)
        with zipfile.ZipFile(path) as zf:
            json_files = [n for n in zf.namelist() if n.endswith(".json")]
            assert len(json_files) >= 2
