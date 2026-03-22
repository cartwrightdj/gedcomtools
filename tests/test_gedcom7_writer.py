"""Tests for gedcom7/writer.py — Gedcom7Writer."""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from gedcomtools.gedcom7 import Gedcom7
from gedcomtools.gedcom7.writer import Gedcom7Writer
from gedcomtools.gedcom7.structure import GedcomStructure

SAMPLE_DIR = Path(__file__).parent.parent / ".sample_data" / "gedcom70"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MINIMAL = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 TRLR
"""

_INDI_TEXT = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NAME Alice /Smith/
2 GIVN Alice
2 SURN Smith
1 SEX F
1 BIRT
2 DATE 1 JAN 1900
2 PLAC Springfield
0 TRLR
"""


def _parse(text: str) -> Gedcom7:
    g = Gedcom7()
    g.parse_string(text)
    return g


def _roundtrip(text: str) -> str:
    g = _parse(text)
    writer = Gedcom7Writer()
    return writer.serialize(g.records)


# ---------------------------------------------------------------------------
# Basic serialization
# ---------------------------------------------------------------------------

class TestSerializeBasic:
    def test_minimal_roundtrip(self):
        out = _roundtrip(_MINIMAL)
        assert "0 HEAD" in out
        assert "0 TRLR" in out

    def test_xref_preserved(self):
        out = _roundtrip(_INDI_TEXT)
        assert "0 @I1@ INDI" in out

    def test_payload_preserved(self):
        out = _roundtrip(_INDI_TEXT)
        assert "1 NAME Alice /Smith/" in out

    def test_sub_records_preserved(self):
        out = _roundtrip(_INDI_TEXT)
        assert "2 GIVN Alice" in out
        assert "2 SURN Smith" in out

    def test_line_endings_lf(self):
        writer = Gedcom7Writer(line_ending="\n")
        g = _parse(_MINIMAL)
        out = writer.serialize(g.records)
        assert "\r\n" not in out
        assert "\n" in out

    def test_line_endings_crlf(self):
        writer = Gedcom7Writer(line_ending="\r\n")
        g = _parse(_MINIMAL)
        out = writer.serialize(g.records)
        assert "\r\n" in out

    def test_no_bom_default(self):
        writer = Gedcom7Writer()
        g = _parse(_MINIMAL)
        out = writer.serialize(g.records)
        assert not out.startswith("\ufeff")

    def test_bom_option(self):
        writer = Gedcom7Writer(bom=True)
        g = _parse(_MINIMAL)
        out = writer.serialize(g.records)
        assert out.startswith("\ufeff")

    def test_no_conc_emitted(self):
        out = _roundtrip(_INDI_TEXT)
        for line in out.splitlines():
            assert " CONC " not in line


# ---------------------------------------------------------------------------
# CONT line re-splitting
# ---------------------------------------------------------------------------

class TestContSplitting:
    def test_cont_lines_re_emitted(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @N1@ SNOTE First line
1 CONT Second line
1 CONT Third line
0 TRLR
"""
        out = _roundtrip(text)
        lines = out.splitlines()
        snote_idx = next(i for i, l in enumerate(lines) if "@N1@ SNOTE" in l)
        assert lines[snote_idx + 1].strip() == "1 CONT Second line"
        assert lines[snote_idx + 2].strip() == "1 CONT Third line"

    def test_cont_empty_segment(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @N1@ SNOTE Line one
1 CONT
1 CONT Line three
0 TRLR
"""
        out = _roundtrip(text)
        assert "1 CONT\n" in out or "1 CONT\r\n" in out

    def test_cont_level_incremented(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NOTE Line one
2 CONT Line two
0 TRLR
"""
        out = _roundtrip(text)
        # NOTE is level 1, so CONT should be level 2
        assert "2 CONT Line two" in out


# ---------------------------------------------------------------------------
# Round-trip fidelity
# ---------------------------------------------------------------------------

class TestRoundTrip:
    def test_parse_serialize_parse_same_records(self):
        g1 = _parse(_INDI_TEXT)
        writer = Gedcom7Writer()
        serialized = writer.serialize(g1.records)
        g2 = _parse(serialized)
        # same number of top-level records
        assert len(g1.records) == len(g2.records)
        # same tags in same order
        assert [r.tag for r in g1.records] == [r.tag for r in g2.records]

    def test_indi_payload_preserved(self):
        g1 = _parse(_INDI_TEXT)
        writer = Gedcom7Writer()
        out = writer.serialize(g1.records)
        g2 = _parse(out)
        name1 = g1["INDI"][0].first_child("NAME").payload
        name2 = g2["INDI"][0].first_child("NAME").payload
        assert name1 == name2

    def test_multiple_records_roundtrip(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NAME Alice /Smith/
0 @I2@ INDI
1 NAME Bob /Jones/
0 @F1@ FAM
1 WIFE @I1@
1 HUSB @I2@
0 TRLR
"""
        g1 = _parse(text)
        writer = Gedcom7Writer()
        out = writer.serialize(g1.records)
        g2 = _parse(out)
        assert len(g2["INDI"]) == 2
        assert len(g2["FAM"]) == 1


# ---------------------------------------------------------------------------
# Line-length warnings
# ---------------------------------------------------------------------------

class TestLineLengthWarnings:
    def test_no_warnings_for_short_lines(self):
        writer = Gedcom7Writer()
        g = _parse(_INDI_TEXT)
        writer.serialize(g.records)
        assert not writer.get_warnings()

    def test_warning_for_long_line(self):
        long_payload = "A" * 300
        text = f"""\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NOTE {long_payload}
0 TRLR
"""
        writer = Gedcom7Writer()
        g = _parse(text)
        writer.serialize(g.records)
        warnings = writer.get_warnings()
        assert warnings
        assert any("NOTE" in w for w in warnings)

    def test_warnings_reset_between_calls(self):
        long_payload = "A" * 300
        text = f"""\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NOTE {long_payload}
0 TRLR
"""
        writer = Gedcom7Writer()
        g_long = _parse(text)
        writer.serialize(g_long.records)
        assert writer.get_warnings()

        g_short = _parse(_INDI_TEXT)
        writer.serialize(g_short.records)
        assert not writer.get_warnings()


# ---------------------------------------------------------------------------
# write() to file
# ---------------------------------------------------------------------------

class TestWriteToFile:
    def test_write_creates_file(self, tmp_path):
        dest = tmp_path / "output.ged"
        g = _parse(_INDI_TEXT)
        writer = Gedcom7Writer()
        writer.write(g.records, dest)
        assert dest.exists()
        content = dest.read_text(encoding="utf-8")
        assert "0 HEAD" in content
        assert "0 TRLR" in content

    def test_write_missing_directory(self, tmp_path):
        dest = tmp_path / "nonexistent" / "output.ged"
        g = _parse(_MINIMAL)
        writer = Gedcom7Writer()
        with pytest.raises(FileNotFoundError):
            writer.write(g.records, dest)

    def test_write_roundtrip_file(self, tmp_path):
        dest = tmp_path / "roundtrip.ged"
        g1 = _parse(_INDI_TEXT)
        writer = Gedcom7Writer()
        writer.write(g1.records, dest)
        g2 = Gedcom7(dest)
        assert len(g1.records) == len(g2.records)

    def test_write_returns_warnings(self, tmp_path):
        """write() should return the same warnings list as get_warnings()."""
        dest = tmp_path / "out.ged"
        long_payload = "A" * 300
        text = f"0 HEAD\n1 GEDC\n2 VERS 7.0\n0 @I1@ INDI\n1 NOTE {long_payload}\n0 TRLR\n"
        g = _parse(text)
        writer = Gedcom7Writer()
        returned = writer.write(g.records, dest)
        assert returned == writer.get_warnings()
        assert returned  # long line should produce a warning

    def test_write_atomic_tmp_cleaned_on_error(self, tmp_path):
        """Temp file should not linger after a failed write."""
        dest = tmp_path / "nonexistent_dir" / "out.ged"
        g = _parse(_MINIMAL)
        writer = Gedcom7Writer()
        with pytest.raises(FileNotFoundError):
            writer.write(g.records, dest)
        # No .tmp file left behind
        assert not list(tmp_path.rglob("*.tmp"))


# ---------------------------------------------------------------------------
# Round-trip fidelity against official sample files
# ---------------------------------------------------------------------------

def _load_sample(path: Path) -> Gedcom7:
    g = Gedcom7()
    if path.suffix == ".gdz":
        with zipfile.ZipFile(path) as zf:
            ged_names = [n for n in zf.namelist() if n.endswith(".ged")]
            g.parse_string(zf.read(ged_names[0]).decode("utf-8-sig"))
    else:
        g.loadfile(path)
    return g


def _official_ged_files():
    if not SAMPLE_DIR.exists():
        return []
    return [p for p in SAMPLE_DIR.iterdir() if p.suffix in (".ged", ".gdz")]


@pytest.mark.parametrize("sample_path", _official_ged_files(), ids=lambda p: p.name)
def test_official_roundtrip(sample_path, tmp_path):
    """Parse → write → re-parse must produce structurally identical trees."""
    g1 = _load_sample(sample_path)
    writer = Gedcom7Writer()
    dest = tmp_path / "roundtrip.ged"
    writer.write(g1.records, dest)
    g2 = Gedcom7(dest)

    # Same number of top-level records
    assert len(g1.records) == len(g2.records), (
        f"{sample_path.name}: record count changed after round-trip "
        f"({len(g1.records)} → {len(g2.records)})"
    )
    # Same tag sequence
    assert [r.tag for r in g1.records] == [r.tag for r in g2.records], (
        f"{sample_path.name}: top-level tag order changed after round-trip"
    )
    # Same xref ids
    assert [r.xref_id for r in g1.records] == [r.xref_id for r in g2.records], (
        f"{sample_path.name}: xref ids changed after round-trip"
    )
    # Payloads of all nodes preserved (flatten both trees and compare)
    def _payloads(g):
        result = []
        def walk(nodes):
            for n in nodes:
                result.append((n.tag, n.payload))
                walk(n.children)
        walk(g.records)
        return result
    assert _payloads(g1) == _payloads(g2), (
        f"{sample_path.name}: node payloads differ after round-trip"
    )
