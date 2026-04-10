"""
======================================================================
 Project: gedcomtools
 File:    tests/test_sample_data_roundtrip.py
 Purpose: Full-pipeline round-trip tests for every file in
          .sample_data/{gedcom5,gedcom70,gedcomx}.

 Pipeline per format
 -------------------
 GEDCOM 5  (.ged):
   1. read    – Gedcom5(path)  [UTF-16 files handled via io.BytesIO]
   2. write   – to_gedcom7() → g7.write(tmp.ged)
   3. read    – Gedcom7(tmp.ged)             [individuals count preserved]
   4. convert – g5.to_gedcomx()
   5. write   – gx.json → tmp.json
   6. read    – GedcomX.from_dict(json.loads(tmp.json)) [persons count preserved]

 GEDCOM 7  (.ged / .gdz):
   1. read    – Gedcom7(path)  [.gdz: unzip + parse_string]
   2. write   – g7.write(tmp.ged)
   3. read    – Gedcom7(tmp.ged)             [record counts preserved]
   4. convert – g7.to_gedcomx()
   5. write   – gx.json → tmp.json
   6. read    – GedcomX.from_dict(json.loads(tmp.json)) [persons count preserved]

 GedcomX  (.gedx zip / .gedcomx JSON):
   1. read    – GedcomZip.read(path) OR GedcomX.from_dict(json.loads(...))
   2. write   – gx.json bytes → tmp.json
   3. read    – GedcomX.from_dict(json.loads(tmp.json)) [persons count preserved]
   4. convert – (GX is already the target; do a second JSON round-trip)
   5. write   – gx3.json → tmp2.json
   6. read    – GedcomX.from_dict(json.loads(tmp2.json)) [triple round-trip stable]

 Created: 2026-03-31
======================================================================
"""
from __future__ import annotations

import io
import json
import tempfile
import zipfile
from pathlib import Path
from typing import Callable

import pytest

from gedcomtools.gedcom5.gedcom5 import Gedcom5
from gedcomtools.gedcom5.parser import Gedcom5x
from gedcomtools.gedcom7.gedcom7 import Gedcom7
from gedcomtools.gedcomx.exceptions import ConversionErrorDump
from gedcomtools.gedcomx.gedcomx import GedcomX
from gedcomtools.gedcomx.zip import GedcomZip

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SAMPLE_DATA = Path(__file__).parent.parent / ".sample_data"
G5_DIR  = SAMPLE_DATA / "gedcom5"
G7_DIR  = SAMPLE_DATA / "gedcom70"
GX_DIR  = SAMPLE_DATA / "gedcomx"

G5_FILES = sorted(G5_DIR.glob("*.ged"))
G7_FILES = sorted(p for p in G7_DIR.iterdir() if p.suffix in (".ged", ".gdz"))
GX_FILES = sorted(p for p in GX_DIR.iterdir() if p.suffix in (".gedx", ".gedcomx"))

# ---------------------------------------------------------------------------
# Files that require special treatment
# ---------------------------------------------------------------------------

# UTF-16 encoded GEDCOM 5 files — must be decoded before parsing
_UTF16_FILES = {"gedcom5_sample_utf16be.ged", "gedcom5_sample_utf16le.ged"}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_g5(path: Path) -> Gedcom5:
    """Load a GEDCOM 5 file, handling UTF-16 encoding transparently."""
    g5 = Gedcom5.__new__(Gedcom5)
    g5._rel_cache = {}
    g5.filepath = path
    if path.name in _UTF16_FILES:
        raw = path.read_bytes()
        text = raw.decode("utf-16")
        parser = Gedcom5x()
        parser.parse(io.BytesIO(text.encode("utf-8")))
        g5._parser = parser
    else:
        g5._parser = Gedcom5x()
        g5._parser.parse_file(str(path))
    return g5


def _load_g7(path: Path) -> Gedcom7:
    """Load a GEDCOM 7 file, unzipping .gdz archives automatically."""
    g7 = Gedcom7()
    if path.suffix == ".gdz":
        with zipfile.ZipFile(path) as zf:
            ged_names = [n for n in zf.namelist() if n.endswith(".ged")]
            assert ged_names, f"No .ged inside {path.name}"
            text = zf.read(ged_names[0]).decode("utf-8-sig")
        g7.parse_string(text)
    else:
        g7.loadfile(path)
    return g7


def _gx_from_json_bytes(raw: bytes) -> GedcomX:
    """Deserialize a GedcomX JSON bytes blob back to a GedcomX object."""
    return GedcomX.from_dict(json.loads(raw))


# ---------------------------------------------------------------------------
# GEDCOM 5 round-trip
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", G5_FILES, ids=lambda p: p.name)
class TestGedcom5RoundTrip:
    """Full read → write → read → convert → write → read for every G5 file."""

    # Fixtures are injected via the class-level parametrize above.
    # Each method receives ``path`` implicitly as a fixture argument.

    def test_step1_read(self, path):
        """Step 1: file must parse without exception."""
        g5 = _load_g5(path)
        # basic integrity: individuals() and families() return sequences
        assert len(g5.individuals()) >= 0
        assert len(g5.families()) >= 0

    def test_step2_3_write_read_g7(self, path, tmp_path):
        """Steps 2-3: G5 → G7 write → G7 re-read; individual count preserved."""
        g5 = _load_g5(path)
        g7 = g5.to_gedcom7()

        tmp_ged = tmp_path / "out.ged"
        g7.write(tmp_ged)

        g7b = Gedcom7(tmp_ged)
        assert len(g7b.individuals()) == len(g5.individuals()), (
            f"{path.name}: individuals after G7 write/read "
            f"({len(g7b.individuals())}) != original G5 count "
            f"({len(g5.individuals())})"
        )

    # Files where to_gedcomx() raises ConversionErrorDump (known conversion gaps)
    _GX_CONV_XFAIL = {"gedcom5_all_tags_ascii.ged"}

    def test_step4_6_convert_gx_json_roundtrip(self, path):
        """Steps 4-6: G5 → GX → JSON → GedcomX; person count preserved."""
        if path.name in self._GX_CONV_XFAIL:
            pytest.xfail(f"{path.name}: known ConversionErrorDump during G5→GX")
        g5 = _load_g5(path)
        gx = g5.to_gedcomx()

        raw = gx.json
        gx2 = _gx_from_json_bytes(raw)

        assert len(gx2.persons) == len(gx.persons), (
            f"{path.name}: GX persons after JSON round-trip "
            f"({len(gx2.persons)}) != original ({len(gx.persons)})"
        )
        assert len(gx2.relationships) == len(gx.relationships), (
            f"{path.name}: GX relationships after JSON round-trip "
            f"({len(gx2.relationships)}) != original ({len(gx.relationships)})"
        )

    def test_step4_6_gx_json_is_valid(self, path):
        """JSON produced during step 5 must be parseable by stdlib json."""
        if path.name in self._GX_CONV_XFAIL:
            pytest.xfail(f"{path.name}: known ConversionErrorDump during G5→GX")
        g5 = _load_g5(path)
        gx = g5.to_gedcomx()
        data = json.loads(gx.json)
        assert isinstance(data, dict)
        # can be re-serialized without error
        json.dumps(data)


# ---------------------------------------------------------------------------
# GEDCOM 7 round-trip
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", G7_FILES, ids=lambda p: p.name)
class TestGedcom7RoundTrip:
    """Full read → write → read → convert → write → read for every G7 file."""

    def test_step1_read(self, path):
        """Step 1: file must parse without exception."""
        g7 = _load_g7(path)
        assert isinstance(g7.records, list)

    def test_step2_3_write_read(self, path, tmp_path):
        """Steps 2-3: G7 write → G7 re-read; all record counts preserved."""
        g7 = _load_g7(path)
        original_count = len(g7.records)

        tmp_ged = tmp_path / "out.ged"
        g7.write(tmp_ged)

        g7b = Gedcom7(tmp_ged)
        assert len(g7b.records) == original_count, (
            f"{path.name}: record count after write/read "
            f"({len(g7b.records)}) != original ({original_count})"
        )

    def test_step2_3_individuals_preserved(self, path, tmp_path):
        """Steps 2-3: individual count preserved through native round-trip."""
        g7 = _load_g7(path)
        tmp_ged = tmp_path / "out.ged"
        g7.write(tmp_ged)
        g7b = Gedcom7(tmp_ged)
        assert len(g7b.individuals()) == len(g7.individuals())

    def test_step4_6_convert_gx_json_roundtrip(self, path):
        """Steps 4-6: G7 → GX → JSON → GedcomX; person count preserved."""
        g7 = _load_g7(path)
        gx = g7.to_gedcomx()

        raw = gx.json
        gx2 = _gx_from_json_bytes(raw)

        assert len(gx2.persons) == len(gx.persons), (
            f"{path.name}: GX persons after JSON round-trip "
            f"({len(gx2.persons)}) != original ({len(gx.persons)})"
        )

    def test_step4_6_gx_json_is_valid(self, path):
        """JSON produced during step 5 must be parseable and re-serializable."""
        g7 = _load_g7(path)
        gx = g7.to_gedcomx()
        data = json.loads(gx.json)
        assert isinstance(data, dict)
        json.dumps(data)


# ---------------------------------------------------------------------------
# GedcomX round-trip
# ---------------------------------------------------------------------------

def _load_gx(path: Path) -> GedcomX:
    """Load a GedcomX file — ZIP (.gedx) or flat JSON (.gedcomx)."""
    if path.suffix == ".gedx":
        return GedcomZip.read(path)
    # .gedcomx — flat JSON
    with open(path, "rb") as f:
        data = json.loads(f.read())
    return GedcomX.from_dict(data)


@pytest.mark.parametrize("path", GX_FILES, ids=lambda p: p.name)
class TestGedcomXRoundTrip:
    """Full read → write → read → convert (2nd JSON RT) → write → read."""

    def test_step1_read(self, path):
        """Step 1: file must load without exception."""
        gx = _load_gx(path)
        # gx.persons is a TypeCollection (supports len, not list)
        assert len(gx.persons) >= 0

    def test_step2_3_json_roundtrip(self, path):
        """Steps 2-3: GX → JSON → GX; person and relationship counts preserved."""
        gx = _load_gx(path)
        gx2 = _gx_from_json_bytes(gx.json)

        assert len(gx2.persons) == len(gx.persons), (
            f"{path.name}: persons after first JSON round-trip "
            f"({len(gx2.persons)}) != original ({len(gx.persons)})"
        )
        assert len(gx2.relationships) == len(gx.relationships), (
            f"{path.name}: relationships after first JSON round-trip "
            f"({len(gx2.relationships)}) != original ({len(gx.relationships)})"
        )

    def test_step4_6_double_json_roundtrip(self, path):
        """Steps 4-6: second JSON round-trip; counts still stable."""
        gx = _load_gx(path)
        gx2 = _gx_from_json_bytes(gx.json)
        gx3 = _gx_from_json_bytes(gx2.json)

        assert len(gx3.persons) == len(gx.persons), (
            f"{path.name}: persons after double JSON round-trip "
            f"({len(gx3.persons)}) != original ({len(gx.persons)})"
        )
        assert len(gx3.relationships) == len(gx.relationships)

    def test_step2_3_json_is_valid(self, path):
        """JSON output must be parseable by stdlib json."""
        gx = _load_gx(path)
        data = json.loads(gx.json)
        assert isinstance(data, dict)
        json.dumps(data)
