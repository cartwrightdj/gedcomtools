"""Tests for the GEDCOM 7 parser (Gedcom7.parse_string / parse_gedcom_line)."""
from __future__ import annotations

import pytest

from gedcomtools.gedcom7 import Gedcom7, GedcomStructure


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MINIMAL = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 TRLR
"""


def _parse(text: str) -> Gedcom7:
    g = Gedcom7()
    g.parse_string(text)
    return g


# ---------------------------------------------------------------------------
# Basic structure
# ---------------------------------------------------------------------------

class TestMinimalFile:
    def test_parses_without_errors(self):
        g = _parse(_MINIMAL)
        assert not g.errors

    def test_record_count(self):
        g = _parse(_MINIMAL)
        assert len(g.records) == 2

    def test_head_first_trlr_last(self):
        g = _parse(_MINIMAL)
        assert g.records[0].tag == "HEAD"
        assert g.records[-1].tag == "TRLR"

    def test_gedc_child_of_head(self):
        g = _parse(_MINIMAL)
        head = g.records[0]
        assert head.first_child("GEDC") is not None

    def test_vers_payload(self):
        g = _parse(_MINIMAL)
        vers = g.records[0].first_child("GEDC").first_child("VERS")
        assert vers.payload == "7.0"


class TestIndexing:
    def test_getitem_by_tag(self):
        g = _parse(_MINIMAL)
        heads = g["HEAD"]
        assert len(heads) == 1
        assert heads[0].tag == "HEAD"

    def test_getitem_by_index(self):
        g = _parse(_MINIMAL)
        assert g[0].tag == "HEAD"

    def test_contains_tag(self):
        g = _parse(_MINIMAL)
        assert "HEAD" in g
        assert "INDI" not in g

    def test_len(self):
        g = _parse(_MINIMAL)
        assert len(g) == 2


# ---------------------------------------------------------------------------
# CONT line merging
# ---------------------------------------------------------------------------

class TestContMerging:
    def test_cont_merged_with_newline(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @N1@ SNOTE First line
1 CONT Second line
1 CONT Third line
0 TRLR
"""
        g = _parse(text)
        snote = g["SNOTE"][0]
        assert snote.payload == "First line\nSecond line\nThird line"

    def test_cont_empty_line(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @N1@ SNOTE Line one
1 CONT
1 CONT Line three
0 TRLR
"""
        g = _parse(text)
        snote = g["SNOTE"][0]
        assert snote.payload == "Line one\n\nLine three"


# ---------------------------------------------------------------------------
# Xref / pointer detection
# ---------------------------------------------------------------------------

class TestXrefAndPointers:
    def test_xref_id_parsed(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NAME John /Doe/
0 TRLR
"""
        g = _parse(text)
        indi = g["INDI"][0]
        assert indi.xref_id == "@I1@"

    def test_pointer_payload_flagged(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
0 @F1@ FAM
1 HUSB @I1@
0 TRLR
"""
        g = _parse(text)
        fam = g["FAM"][0]
        husb = fam.first_child("HUSB")
        assert husb.payload_is_pointer
        assert husb.payload == "@I1@"

    def test_non_pointer_text_not_flagged(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NAME John /Doe/
0 TRLR
"""
        g = _parse(text)
        name = g["INDI"][0].first_child("NAME")
        assert not name.payload_is_pointer

    def test_void_pointer(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 FAMC @VOID@
0 TRLR
"""
        g = _parse(text)
        famc = g["INDI"][0].first_child("FAMC")
        assert famc.payload_is_pointer
        assert famc.payload == "@VOID@"


# ---------------------------------------------------------------------------
# parse_gedcom_line unit tests
# ---------------------------------------------------------------------------

class TestParseGedcomLine:
    def test_level_tag(self):
        result = Gedcom7.parse_gedcom_line("0 HEAD")
        assert result["level"] == 0
        assert result["tag"] == "HEAD"
        assert result["payload"] == ""

    def test_level_tag_payload(self):
        result = Gedcom7.parse_gedcom_line("1 NAME John /Doe/")
        assert result["level"] == 1
        assert result["tag"] == "NAME"
        assert result["payload"] == "John /Doe/"

    def test_level_xref_tag(self):
        result = Gedcom7.parse_gedcom_line("0 @I1@ INDI")
        assert result["level"] == 0
        assert result["xref_id"] == "@I1@"
        assert result["tag"] == "INDI"

    def test_pointer_payload(self):
        result = Gedcom7.parse_gedcom_line("1 HUSB @I1@")
        assert result["payload"] == "@I1@"
        assert result["payload_is_pointer"] is True

    def test_blank_line_returns_none(self):
        assert Gedcom7.parse_gedcom_line("") is None
        assert Gedcom7.parse_gedcom_line("   ") is None

    def test_malformed_missing_tag(self):
        with pytest.raises(ValueError):
            Gedcom7.parse_gedcom_line("0")

    def test_malformed_non_numeric_level(self):
        with pytest.raises(ValueError):
            Gedcom7.parse_gedcom_line("X HEAD")

    def test_tag_uppercased(self):
        result = Gedcom7.parse_gedcom_line("0 head")
        assert result["tag"] == "HEAD"

    def test_bom_stripped(self):
        result = Gedcom7.parse_gedcom_line("\ufeff0 HEAD")
        assert result["level"] == 0
        assert result["tag"] == "HEAD"


# ---------------------------------------------------------------------------
# C0 control character detection
# ---------------------------------------------------------------------------

class TestControlCharacters:
    def test_nul_byte_is_error(self):
        text = "0 HEAD\n1 GEDC\n2 VERS 7.0\n0 TRLR\n"
        # Inject NUL into the first line
        text_with_nul = "\x000 HEAD\n1 GEDC\n2 VERS 7.0\n0 TRLR\n"
        g = _parse(text_with_nul)
        error_codes = [e.code for e in g.errors]
        assert "nul_character" in error_codes

    def test_other_c0_is_warning(self):
        text = "0 HEAD\n1 GEDC\n2 VERS 7.0\n0 \x01TRLR\n"
        g = _parse(text)
        error_codes = [e.code for e in g.errors]
        assert "control_character" in error_codes


# ---------------------------------------------------------------------------
# Multiple records / nesting
# ---------------------------------------------------------------------------

class TestMultipleRecords:
    def test_multiple_indi(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NAME Alice /Smith/
0 @I2@ INDI
1 NAME Bob /Jones/
0 TRLR
"""
        g = _parse(text)
        assert len(g["INDI"]) == 2

    def test_deep_nesting(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 BIRT
2 DATE 1 JAN 1900
2 PLAC Springfield
3 MAP
4 LATI N39.7
4 LONG W89.6
0 TRLR
"""
        g = _parse(text)
        birt = g["INDI"][0].first_child("BIRT")
        plac = birt.first_child("PLAC")
        map_node = plac.first_child("MAP")
        assert map_node is not None
        lati = map_node.first_child("LATI")
        assert lati.payload == "N39.7"

    def test_parse_string_resets_state(self):
        g = _parse(_MINIMAL + "0 @I1@ INDI\n")
        g.parse_string(_MINIMAL)
        assert "INDI" not in g
