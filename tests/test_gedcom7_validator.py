"""Tests for the GEDCOM 7 multi-phase validator."""
from __future__ import annotations

import pytest

from gedcomtools.gedcom7 import Gedcom7, GedcomValidator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate(text: str, *, strict_extensions: bool = True):
    g = Gedcom7()
    g.parse_string(text)
    v = GedcomValidator(g.records, strict_extensions=strict_extensions)
    return v.validate()


def _codes(issues):
    return [i.code for i in issues]


def _errors(issues):
    return [i for i in issues if i.severity == "error"]


def _warnings(issues):
    return [i for i in issues if i.severity == "warning"]


_MINIMAL = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 TRLR
"""

_FULL_INDI = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NAME Alice /Smith/
1 SEX F
1 BIRT
2 DATE 1 JAN 1900
2 PLAC Springfield
0 TRLR
"""


# ---------------------------------------------------------------------------
# Phase 1: File structure
# ---------------------------------------------------------------------------

class TestFileStructure:
    def test_valid_minimal(self):
        issues = _validate(_MINIMAL)
        assert not _errors(issues)

    def test_missing_head(self):
        text = "0 TRLR\n"
        issues = _validate(text)
        assert "missing_head_first" in _codes(issues)

    def test_missing_trlr(self):
        text = "0 HEAD\n1 GEDC\n2 VERS 7.0\n"
        issues = _validate(text)
        assert "missing_trlr_last" in _codes(issues)

    def test_duplicate_head(self):
        text = "0 HEAD\n1 GEDC\n2 VERS 7.0\n0 HEAD\n1 GEDC\n2 VERS 7.0\n0 TRLR\n"
        issues = _validate(text)
        assert "invalid_head_count" in _codes(issues)

    def test_empty_file(self):
        issues = _validate("")
        assert "empty_file" in _codes(issues)

    def test_missing_gedc(self):
        text = "0 HEAD\n0 TRLR\n"
        issues = _validate(text)
        assert "missing_gedc" in _codes(issues)

    def test_missing_gedc_vers(self):
        text = "0 HEAD\n1 GEDC\n0 TRLR\n"
        issues = _validate(text)
        assert "missing_gedc_vers" in _codes(issues)

    def test_invalid_vers_format(self):
        text = "0 HEAD\n1 GEDC\n2 VERS abc\n0 TRLR\n"
        issues = _validate(text)
        assert "invalid_gedc_vers_format" in _codes(issues)

    def test_indi_without_xref(self):
        text = "0 HEAD\n1 GEDC\n2 VERS 7.0\n0 INDI\n0 TRLR\n"
        issues = _validate(text)
        assert "missing_xref_id" in _codes(issues)

    def test_head_with_xref(self):
        text = "0 @H1@ HEAD\n1 GEDC\n2 VERS 7.0\n0 TRLR\n"
        issues = _validate(text)
        assert "unexpected_xref_id" in _codes(issues)


# ---------------------------------------------------------------------------
# Phase 2: Xref format
# ---------------------------------------------------------------------------

class TestXrefFormat:
    def test_valid_xref(self):
        issues = _validate(_FULL_INDI)
        xref_errors = [i for i in issues if i.code == "invalid_xref_format"]
        assert not xref_errors

    def test_duplicate_xref(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NAME Alice /Smith/
0 @I1@ INDI
1 NAME Bob /Jones/
0 TRLR
"""
        issues = _validate(text)
        assert "duplicate_xref" in _codes(issues)


# ---------------------------------------------------------------------------
# Phase 3: Level stepping
# ---------------------------------------------------------------------------

class TestLevelStepping:
    def test_valid_levels(self):
        issues = _validate(_FULL_INDI)
        level_errors = [i for i in _errors(issues) if i.code == "invalid_level_step"]
        assert not level_errors


# ---------------------------------------------------------------------------
# Phase 4: Tag legality
# ---------------------------------------------------------------------------

class TestTagLegality:
    def test_illegal_top_level(self):
        text = "0 HEAD\n1 GEDC\n2 VERS 7.0\n0 NAME foo\n0 TRLR\n"
        issues = _validate(text)
        assert "illegal_top_level_record" in _codes(issues)

    def test_illegal_substructure(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 VERS 7.0
0 TRLR
"""
        issues = _validate(text)
        assert "illegal_substructure" in _codes(issues)

    def test_unknown_tag(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 UNKNOWNTAG foo
0 TRLR
"""
        issues = _validate(text, strict_extensions=False)
        assert "unknown_tag" in _codes(issues)

    def test_undeclared_extension_tag(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 _CUSTOM foo
0 TRLR
"""
        issues = _validate(text, strict_extensions=True)
        assert "undeclared_extension_tag" in _codes(issues)

    def test_declared_extension_tag_ok(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
1 SCHMA
2 TAG _CUSTOM https://example.com/custom
0 @I1@ INDI
1 _CUSTOM foo
0 TRLR
"""
        issues = _validate(text, strict_extensions=True)
        assert "undeclared_extension_tag" not in _codes(issues)


# ---------------------------------------------------------------------------
# Phase 5: Payload types
# ---------------------------------------------------------------------------

class TestPayloadType:
    def test_pointer_required(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 FAMC not-a-pointer
0 TRLR
"""
        issues = _validate(text)
        assert "pointer_required" in _codes(issues)

    def test_trlr_has_children(self):
        text = "0 HEAD\n1 GEDC\n2 VERS 7.0\n0 TRLR\n1 NAME foo\n"
        g = Gedcom7()
        g.parse_string(text)
        # Manually add a child to TRLR for testing
        from gedcomtools.gedcom7.structure import GedcomStructure
        trlr = g.records[-1]
        GedcomStructure(level=1, tag="NAME", payload="foo", parent=trlr)
        v = GedcomValidator(g.records)
        issues = v.validate()
        assert "trlr_has_children" in _codes(issues)


# ---------------------------------------------------------------------------
# Phase 6: Enumeration
# ---------------------------------------------------------------------------

class TestEnumeration:
    def test_valid_sex(self):
        issues = _validate(_FULL_INDI)
        enum_errors = [i for i in issues if i.code == "invalid_enumeration_value"]
        assert not enum_errors

    def test_invalid_sex(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 SEX Q
0 TRLR
"""
        issues = _validate(text)
        assert "invalid_enumeration_value" in _codes(issues)

    def test_valid_quay(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @S1@ SOUR
1 TITL A Source
0 @I1@ INDI
1 SOUR @S1@
2 QUAY 2
0 TRLR
"""
        issues = _validate(text)
        enum_errors = [i for i in issues if i.code == "invalid_enumeration_value"]
        assert not enum_errors

    def test_invalid_quay(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @S1@ SOUR
1 TITL A Source
0 @I1@ INDI
1 SOUR @S1@
2 QUAY 9
0 TRLR
"""
        issues = _validate(text)
        assert "invalid_enumeration_value" in _codes(issues)

    def test_invalid_medi(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @S1@ SOUR
1 TITL A Source
0 @I1@ INDI
1 SOUR @S1@
2 MEDI FLOPPY
0 TRLR
"""
        issues = _validate(text)
        assert "invalid_enumeration_value" in _codes(issues)


# ---------------------------------------------------------------------------
# Phase 7: Payload format (DATE, TIME, AGE, LATI, LONG, LANG, RESN)
# ---------------------------------------------------------------------------

class TestPayloadFormat:
    def test_valid_date(self):
        issues = _validate(_FULL_INDI)
        date_errors = [i for i in issues if i.code == "invalid_date_format"]
        assert not date_errors

    def test_invalid_date(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 BIRT
2 DATE NOTADATE
0 TRLR
"""
        issues = _validate(text)
        assert "invalid_date_format" in _codes(issues)

    def test_valid_date_qualifiers(self):
        for qualifier in ("ABT", "BEF", "AFT", "CAL", "EST"):
            text = f"""\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 BIRT
2 DATE {qualifier} 1900
0 TRLR
"""
            issues = _validate(text)
            date_errors = [i for i in issues if i.code == "invalid_date_format"]
            assert not date_errors, f"Failed for qualifier {qualifier!r}"

    def test_valid_date_range(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 RESI
2 DATE FROM 1900 TO 1910
0 TRLR
"""
        issues = _validate(text)
        date_errors = [i for i in issues if i.code == "invalid_date_format"]
        assert not date_errors

    def test_valid_date_int(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 BIRT
2 DATE INT about 1900 (estimate)
0 TRLR
"""
        issues = _validate(text)
        date_errors = [i for i in issues if i.code == "invalid_date_format"]
        assert not date_errors

    def test_invalid_lati(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 BIRT
2 PLAC Springfield
3 MAP
4 LATI 45.0
0 TRLR
"""
        issues = _validate(text)
        assert "invalid_lati_format" in _codes(issues)

    def test_valid_lati_long(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 BIRT
2 PLAC Springfield
3 MAP
4 LATI N45.5
4 LONG W93.0
0 TRLR
"""
        issues = _validate(text)
        assert "invalid_lati_format" not in _codes(issues)
        assert "invalid_long_format" not in _codes(issues)

    def test_invalid_lang(self):
        # Primary subtag must be 2-8 alpha chars; 'x' alone (1 char) is invalid
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NAME /Smith/
2 TRAN /Schmitt/
3 LANG toolonglanguage
0 TRLR
"""
        issues = _validate(text)
        assert "invalid_lang_format" in _codes(issues)

    def test_valid_resn(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 RESN CONFIDENTIAL
0 TRLR
"""
        issues = _validate(text)
        resn_errors = [i for i in issues if i.code == "invalid_resn_value"]
        assert not resn_errors

    def test_invalid_resn(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 RESN SECRET
0 TRLR
"""
        issues = _validate(text)
        assert "invalid_resn_value" in _codes(issues)

    def test_resn_multiple_values(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 RESN CONFIDENTIAL, LOCKED
0 TRLR
"""
        issues = _validate(text)
        resn_errors = [i for i in issues if i.code == "invalid_resn_value"]
        assert not resn_errors


# ---------------------------------------------------------------------------
# Phase 8: Pointer validation
# ---------------------------------------------------------------------------

class TestPointerValidation:
    def test_dangling_pointer(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 FAMC @F1@
0 TRLR
"""
        issues = _validate(text)
        assert "dangling_pointer" in _codes(issues)

    def test_valid_pointer(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 FAMS @F1@
0 @F1@ FAM
1 HUSB @I1@
0 TRLR
"""
        issues = _validate(text)
        assert "dangling_pointer" not in _codes(issues)

    def test_void_pointer_ok(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 FAMC @VOID@
0 TRLR
"""
        issues = _validate(text)
        assert "dangling_pointer" not in _codes(issues)

    def test_malformed_pointer(self):
        text = "0 HEAD\n1 GEDC\n2 VERS 7.0\n0 TRLR\n"
        g = Gedcom7()
        g.parse_string(text)
        from gedcomtools.gedcom7.structure import GedcomStructure
        indi = GedcomStructure(level=0, tag="INDI", xref_id="@I1@", parent=None)
        g.records.insert(-1, indi)
        GedcomStructure(level=1, tag="FAMC", payload="@@", payload_is_pointer=True, parent=indi)
        v = GedcomValidator(g.records)
        issues = v.validate()
        assert "malformed_pointer" in _codes(issues)


# ---------------------------------------------------------------------------
# Phase 9: Bidirectional links
# ---------------------------------------------------------------------------

class TestBidirectionalLinks:
    def test_famc_without_chil_back(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 FAMC @F1@
0 @F1@ FAM
0 TRLR
"""
        issues = _validate(text)
        bp = [i for i in issues if i.code == "missing_back_pointer" and i.tag == "FAMC"]
        assert bp

    def test_fams_without_spouse_back(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 FAMS @F1@
0 @F1@ FAM
0 TRLR
"""
        issues = _validate(text)
        bp = [i for i in issues if i.code == "missing_back_pointer" and i.tag == "FAMS"]
        assert bp

    def test_consistent_bidirectional_links(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 FAMS @F1@
0 @F1@ FAM
1 HUSB @I1@
0 TRLR
"""
        issues = _validate(text)
        bp = [i for i in issues if i.code == "missing_back_pointer"]
        assert not bp


# ---------------------------------------------------------------------------
# Phase 10: Orphaned records
# ---------------------------------------------------------------------------

class TestOrphanedRecords:
    def test_orphaned_sour(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @S1@ SOUR
1 TITL Unused Source
0 TRLR
"""
        issues = _validate(text)
        assert "orphaned_record" in _codes(issues)

    def test_cited_sour_not_orphaned(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @S1@ SOUR
1 TITL Used Source
0 @I1@ INDI
1 SOUR @S1@
0 TRLR
"""
        issues = _validate(text)
        orphans = [i for i in issues if i.code == "orphaned_record"]
        assert not orphans

    def test_orphaned_subm(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @SM1@ SUBM
1 NAME Orphaned Submitter
0 TRLR
"""
        issues = _validate(text)
        assert "orphaned_record" in _codes(issues)

    def test_head_subm_not_orphaned(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
1 SUBM @SM1@
0 @SM1@ SUBM
1 NAME Active Submitter
0 TRLR
"""
        issues = _validate(text)
        orphans = [i for i in issues if i.code == "orphaned_record"]
        assert not orphans


# ---------------------------------------------------------------------------
# TRAN context
# ---------------------------------------------------------------------------

class TestTranContext:
    def test_tran_missing_lang(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NAME /Smith/
2 TRAN /Schmitt/
0 TRLR
"""
        issues = _validate(text)
        assert "tran_missing_lang" in _codes(issues)

    def test_tran_invalid_parent(self):
        text = "0 HEAD\n1 GEDC\n2 VERS 7.0\n0 TRLR\n"
        g = Gedcom7()
        g.parse_string(text)
        from gedcomtools.gedcom7.structure import GedcomStructure
        indi = GedcomStructure(level=0, tag="INDI", xref_id="@I1@")
        g.records.insert(-1, indi)
        birt = GedcomStructure(level=1, tag="BIRT", parent=indi)
        GedcomStructure(level=2, tag="TRAN", payload="translated", parent=birt)
        v = GedcomValidator(g.records)
        issues = v.validate()
        assert "tran_invalid_parent" in _codes(issues)

    def test_plac_tran_only_lang_child(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 BIRT
2 PLAC Springfield
3 TRAN Springfeld
4 LANG de
4 NAME invalid_child
0 TRLR
"""
        issues = _validate(text)
        assert "tran_plac_invalid_child" in _codes(issues)

    def test_file_tran_missing_form_and_mime(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @O1@ OBJE
1 FILE photo.jpg
2 FORM jpg
2 TRAN photo.pdf
3 LANG en
0 TRLR
"""
        issues = _validate(text)
        tran_warns = [i for i in issues if i.code in ("tran_file_missing_form", "tran_file_missing_mime")]
        assert tran_warns


# ---------------------------------------------------------------------------
# @VOID@ context
# ---------------------------------------------------------------------------

class TestVoidPointer:
    def test_void_ok_on_famc(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 FAMC @VOID@
0 TRLR
"""
        issues = _validate(text)
        void_errors = [i for i in issues if i.code == "void_in_wrong_context"]
        assert not void_errors

    def test_void_wrong_context(self):
        text = "0 HEAD\n1 GEDC\n2 VERS 7.0\n0 TRLR\n"
        g = Gedcom7()
        g.parse_string(text)
        from gedcomtools.gedcom7.structure import GedcomStructure
        indi = GedcomStructure(level=0, tag="INDI", xref_id="@I1@")
        g.records.insert(-1, indi)
        GedcomStructure(level=1, tag="SEX", payload="@VOID@", payload_is_pointer=True, parent=indi)
        v = GedcomValidator(g.records)
        issues = v.validate()
        assert "void_in_wrong_context" in _codes(issues)
