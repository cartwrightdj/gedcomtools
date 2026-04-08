"""
======================================================================
 Project: gedcomtools
 File:    tests/test_g5tog7.py
 Purpose: Tests for Gedcom5to7 (GEDCOM 5 → GEDCOM 7) converter.
          Covers: warnings content, HEAD.SCHMA population on
          unknown_tags='convert', and G5→G7→write→reload round-trip.

 Created: 2026-04-07
======================================================================
"""
from __future__ import annotations

import io
from pathlib import Path

import pytest

from gedcomtools.gedcom5.parser import Gedcom5x
from gedcomtools.gedcom5.g5tog7 import Gedcom5to7
from gedcomtools.gedcom7.gedcom7 import Gedcom7
from gedcomtools.gedcom7.writer import Gedcom7Writer

SAMPLE_DATA = Path(__file__).parent.parent / ".sample_data" / "gedcom5"
GED_TINY    = SAMPLE_DATA / "gedcom5_sample.ged"
GED_COMP    = SAMPLE_DATA / "gedcom5_comprehensive.ged"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse(text: str) -> Gedcom5x:
    p = Gedcom5x()
    p.parse(io.BytesIO(text.encode("utf-8")))
    return p


def _convert(text: str, **kwargs) -> tuple[list, list[str]]:
    """Parse GEDCOM 5 text and convert to G7 records, returning (records, warnings)."""
    conv = Gedcom5to7(**kwargs)
    records = conv.convert(_parse(text))
    return records, conv.warnings


# ---------------------------------------------------------------------------
# Minimal valid G5 skeletons
# ---------------------------------------------------------------------------

_HEAD = """\
0 HEAD
1 GEDC
2 VERS 5.5.1
1 CHAR UTF-8
"""
_TRLR = "0 TRLR\n"


def _g5(*body: str, char: str = "UTF-8") -> str:
    head = f"0 HEAD\n1 GEDC\n2 VERS 5.5.1\n1 CHAR {char}\n"
    return head + "".join(body) + _TRLR


# ---------------------------------------------------------------------------
# TestWarnings — converter produces correct warning messages
# ---------------------------------------------------------------------------

class TestWarnings:
    def test_snote_promotion_warning(self):
        """Level-0 NOTE with xref → promoted to SNOTE, warning emitted."""
        text = _g5("0 @N1@ NOTE A shared note\n")
        _, warnings = _convert(text)
        assert any("promoted to SNOTE" in w for w in warnings), (
            f"Expected 'promoted to SNOTE' warning; got: {warnings}"
        )

    def test_snote_promotion_count(self):
        """Warning message includes count of promoted SNOTEs."""
        text = _g5(
            "0 @N1@ NOTE First note\n",
            "0 @N2@ NOTE Second note\n",
        )
        _, warnings = _convert(text)
        snote_warn = next(w for w in warnings if "promoted to SNOTE" in w)
        assert "2" in snote_warn

    def test_vendor_tag_drop_warning(self):
        """Vendor tag (RIN) with unknown_tags='drop' emits a drop warning."""
        text = _g5("0 @I1@ INDI\n1 NAME John /Doe/\n1 RIN 12345\n")
        _, warnings = _convert(text, unknown_tags="drop")
        assert any("'RIN' dropped" in w for w in warnings), (
            f"Expected RIN drop warning; got: {warnings}"
        )

    def test_vendor_tag_drop_count(self):
        """Drop warning includes occurrence count."""
        text = _g5(
            "0 @I1@ INDI\n1 NAME John /Doe/\n1 RIN 1\n",
            "0 @I2@ INDI\n1 NAME Jane /Doe/\n1 RIN 2\n",
        )
        _, warnings = _convert(text, unknown_tags="drop")
        drop_warn = next(w for w in warnings if "'RIN' dropped" in w)
        assert "2" in drop_warn

    def test_char_encoding_warning_ansel(self):
        """Non-UTF-8 CHAR value triggers a charset conversion warning."""
        text = _g5(char="ANSEL")
        _, warnings = _convert(text)
        assert any("ANSEL" in w for w in warnings), (
            f"Expected ANSEL charset warning; got: {warnings}"
        )

    def test_char_encoding_warning_mentions_utf8(self):
        """Charset warning mentions UTF-8 as the output encoding."""
        text = _g5(char="ASCII")
        _, warnings = _convert(text)
        warn = next((w for w in warnings if "ASCII" in w), None)
        assert warn is not None
        assert "UTF-8" in warn

    def test_no_char_warning_for_utf8(self):
        """No charset warning when CHAR is already UTF-8."""
        text = _g5(char="UTF-8")
        _, warnings = _convert(text)
        assert not any("UTF-8" in w and "was" in w for w in warnings)

    def test_extra_marr_warning(self):
        """Duplicate MARR on a FAM → extra MARR converted to EVEN TYPE MARR, warning emitted."""
        text = _g5(
            "0 @I1@ INDI\n1 SEX M\n",
            "0 @I2@ INDI\n1 SEX F\n",
            "0 @F1@ FAM\n1 HUSB @I1@\n1 WIFE @I2@\n"
            "1 MARR\n2 DATE 1 JAN 2000\n"
            "1 MARR\n2 DATE 15 MAR 2001\n",
        )
        _, warnings = _convert(text)
        assert any("extra MARR" in w for w in warnings), (
            f"Expected extra MARR warning; got: {warnings}"
        )

    def test_no_warnings_for_clean_file(self):
        """A minimal clean G5 file produces no converter warnings."""
        text = _g5("0 @I1@ INDI\n1 NAME John /Doe/\n")
        _, warnings = _convert(text)
        assert warnings == []

    def test_warnings_reset_between_convert_calls(self):
        """warnings list is cleared at the start of each convert() call."""
        conv = Gedcom5to7()
        # First call: file with vendor tag
        dirty = _g5("0 @I1@ INDI\n1 RIN 99\n")
        conv.convert(_parse(dirty))
        assert conv.warnings  # has warnings

        # Second call: clean file
        clean = _g5("0 @I1@ INDI\n1 NAME John /Doe/\n")
        conv.convert(_parse(clean))
        assert conv.warnings == []  # warnings cleared


# ---------------------------------------------------------------------------
# TestSchmaDeclaration — HEAD.SCHMA populated with unknown_tags='convert'
# ---------------------------------------------------------------------------

class TestSchmaDeclaration:
    def test_unknown_tags_drop_no_schma(self):
        """unknown_tags='drop' must NOT add HEAD.SCHMA (no extension tags declared)."""
        text = _g5("0 @I1@ INDI\n1 NAME John /Doe/\n1 RIN 12345\n")
        records, _ = _convert(text, unknown_tags="drop")
        head = next(r for r in records if r.tag == "HEAD")
        schma = head.first_child("SCHMA")
        assert schma is None, "HEAD.SCHMA must not exist when unknown_tags='drop'"

    def test_unknown_tags_convert_adds_schma(self):
        """unknown_tags='convert' must add HEAD.SCHMA when vendor tags are present."""
        text = _g5("0 @I1@ INDI\n1 NAME John /Doe/\n1 RIN 12345\n")
        records, _ = _convert(text, unknown_tags="convert")
        head = next(r for r in records if r.tag == "HEAD")
        schma = head.first_child("SCHMA")
        assert schma is not None, "HEAD.SCHMA must be present when unknown_tags='convert'"

    def test_schma_has_tag_entries(self):
        """HEAD.SCHMA must contain TAG declarations for each extension tag."""
        text = _g5("0 @I1@ INDI\n1 NAME John /Doe/\n1 RIN 12345\n")
        records, _ = _convert(text, unknown_tags="convert")
        head = next(r for r in records if r.tag == "HEAD")
        schma = head.first_child("SCHMA")
        assert schma is not None
        tag_nodes = [c for c in schma.children if c.tag == "TAG"]
        assert len(tag_nodes) > 0, "HEAD.SCHMA must have at least one TAG child"

    def test_schma_tag_payload_has_uri(self):
        """Each HEAD.SCHMA.TAG payload must be '<tag> <uri>' format."""
        text = _g5("0 @I1@ INDI\n1 NAME John /Doe/\n1 RIN 12345\n")
        records, _ = _convert(text, unknown_tags="convert")
        head = next(r for r in records if r.tag == "HEAD")
        schma = head.first_child("SCHMA")
        for tag_node in schma.children:
            assert tag_node.payload, f"TAG node has no payload: {tag_node}"
            parts = tag_node.payload.split(None, 1)
            assert len(parts) == 2, f"TAG payload not '<tag> <uri>': {tag_node.payload!r}"
            ext_tag, uri = parts
            assert ext_tag.startswith("_"), f"Extension tag should start with '_': {ext_tag!r}"
            assert uri.startswith("http"), f"URI should start with 'http': {uri!r}"

    def test_no_schma_for_clean_file(self):
        """No HEAD.SCHMA emitted when no extension tags were encountered."""
        text = _g5("0 @I1@ INDI\n1 NAME John /Doe/\n")
        records, _ = _convert(text, unknown_tags="convert")
        head = next(r for r in records if r.tag == "HEAD")
        schma = head.first_child("SCHMA")
        assert schma is None


# ---------------------------------------------------------------------------
# TestRoundTrip — G5 → G7 → write → reload
# ---------------------------------------------------------------------------

class TestRoundTrip:
    @pytest.fixture(scope="class")
    def tiny_path(self):
        if not GED_TINY.exists():
            pytest.skip(f"Sample file not found: {GED_TINY}")
        return GED_TINY

    @pytest.fixture(scope="class")
    def comp_path(self):
        if not GED_COMP.exists():
            pytest.skip(f"Sample file not found: {GED_COMP}")
        return GED_COMP

    def test_roundtrip_produces_valid_g7(self, tiny_path, tmp_path):
        """G5 → G7 records → write → re-parse produces a loadable Gedcom7."""
        from gedcomtools.gedcom5.gedcom5 import Gedcom5
        g5 = Gedcom5(tiny_path)
        records = Gedcom5to7().convert(g5)
        dest = tmp_path / "out.ged"
        Gedcom7Writer().write(records, dest)
        g7 = Gedcom7(dest)
        assert len(g7.records) > 0

    def test_roundtrip_has_head_and_trlr(self, tiny_path, tmp_path):
        """Round-tripped file starts with HEAD and ends with TRLR."""
        from gedcomtools.gedcom5.gedcom5 import Gedcom5
        g5 = Gedcom5(tiny_path)
        records = Gedcom5to7().convert(g5)
        dest = tmp_path / "out.ged"
        Gedcom7Writer().write(records, dest)
        g7 = Gedcom7(dest)
        assert g7.records[0].tag == "HEAD"
        assert g7.records[-1].tag == "TRLR"

    def test_roundtrip_gedc_vers_is_70(self, tiny_path, tmp_path):
        """Round-tripped file HEAD.GEDC.VERS is 7.0."""
        from gedcomtools.gedcom5.gedcom5 import Gedcom5
        g5 = Gedcom5(tiny_path)
        records = Gedcom5to7().convert(g5)
        dest = tmp_path / "out.ged"
        Gedcom7Writer().write(records, dest)
        g7 = Gedcom7(dest)
        head = g7["HEAD"][0]
        gedc = head.first_child("GEDC")
        assert gedc is not None
        vers = gedc.first_child("VERS")
        assert vers is not None
        assert vers.payload == "7.0"

    def test_roundtrip_individual_count_matches(self, tiny_path, tmp_path):
        """Number of INDI records is preserved through the round-trip."""
        from gedcomtools.gedcom5.gedcom5 import Gedcom5
        g5 = Gedcom5(tiny_path)
        n_indi_before = len(g5.individuals())
        records = Gedcom5to7().convert(g5)
        dest = tmp_path / "out.ged"
        Gedcom7Writer().write(records, dest)
        g7 = Gedcom7(dest)
        assert len(g7.individuals()) == n_indi_before

    def test_roundtrip_individual_name_preserved(self, tiny_path, tmp_path):
        """First individual's NAME payload survives G5→G7→write→reload."""
        from gedcomtools.gedcom5.gedcom5 import Gedcom5
        from gedcomtools.gedcom5.parser import Gedcom5x
        # Get first individual's name from raw parse
        p = Gedcom5x()
        p.parse_file(str(tiny_path))
        indis = p.individuals
        if not indis:
            pytest.skip("No individuals in sample file")
        first_indi = indis[0]
        names = [c for c in first_indi.get_child_elements() if c.tag == "NAME"]
        if not names:
            pytest.skip("First individual has no NAME in sample file")
        g5_name = names[0].get_value()

        g5 = Gedcom5(tiny_path)
        records = Gedcom5to7().convert(g5)
        dest = tmp_path / "out.ged"
        Gedcom7Writer().write(records, dest)
        g7 = Gedcom7(dest)
        g7_names = [
            c.payload
            for indi in g7.individuals()
            for c in indi.children
            if c.tag == "NAME"
        ]
        assert g5_name in g7_names, (
            f"NAME {g5_name!r} not found in round-tripped individuals: {g7_names}"
        )

    def test_roundtrip_comprehensive_no_crash(self, comp_path, tmp_path):
        """Comprehensive G5 file converts and round-trips without error."""
        from gedcomtools.gedcom5.gedcom5 import Gedcom5
        g5 = Gedcom5(comp_path)
        records = Gedcom5to7().convert(g5)
        dest = tmp_path / "out.ged"
        Gedcom7Writer().write(records, dest)
        g7 = Gedcom7(dest)
        assert len(g7.records) > 2  # at least HEAD + something + TRLR

    def test_roundtrip_inline_snote(self, tmp_path):
        """Level-0 NOTE with xref is written as SNOTE and readable after reload."""
        text = _g5("0 @N1@ NOTE This is a shared note\n")
        records, _ = _convert(text)
        dest = tmp_path / "out.ged"
        Gedcom7Writer().write(records, dest)
        g7 = Gedcom7(dest)
        snotes = g7.shared_notes()
        assert len(snotes) == 1
        assert snotes[0].tag == "SNOTE"

    def test_roundtrip_inline_vendor_convert_mode(self, tmp_path):
        """unknown_tags='convert' round-trip: extension tag survives in G7 output."""
        text = _g5("0 @I1@ INDI\n1 NAME John /Doe/\n1 RIN 12345\n")
        records, _ = _convert(text, unknown_tags="convert")
        dest = tmp_path / "out.ged"
        Gedcom7Writer().write(records, dest)
        content = dest.read_text(encoding="utf-8")
        # Extension tag should have been renamed to _RIN
        assert "_RIN" in content

    def test_roundtrip_extra_marr_becomes_even(self, tmp_path):
        """Duplicate MARR on FAM is written as EVEN TYPE MARR after round-trip."""
        text = _g5(
            "0 @I1@ INDI\n1 SEX M\n",
            "0 @I2@ INDI\n1 SEX F\n",
            "0 @F1@ FAM\n1 HUSB @I1@\n1 WIFE @I2@\n"
            "1 MARR\n2 DATE 1 JAN 2000\n"
            "1 MARR\n2 DATE 15 MAR 2001\n",
        )
        records, _ = _convert(text)
        dest = tmp_path / "out.ged"
        Gedcom7Writer().write(records, dest)
        g7 = Gedcom7(dest)
        fam = g7["FAM"][0]
        marr_nodes = [c for c in fam.children if c.tag == "MARR"]
        even_nodes = [c for c in fam.children if c.tag == "EVEN"]
        assert len(marr_nodes) == 1, "Exactly one MARR should remain"
        assert len(even_nodes) == 1, "Duplicate MARR should become EVEN"
        even_type = even_nodes[0].first_child("TYPE")
        assert even_type is not None and even_type.payload == "MARR"
