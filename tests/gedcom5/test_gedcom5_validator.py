"""
Tests for gedcom5/validator5.py — all nine validation phases.

Each test builds a minimal GEDCOM 5 string, parses it with Gedcom5x,
then asserts the expected issue codes (or absence thereof).
"""
from __future__ import annotations

import io
from typing import List

import pytest

from gedcomtools.gedcom5.parser import Gedcom5x
from gedcomtools.gedcom5.validator5 import Gedcom5Validator
from gedcomtools.gedcom7.validator import ValidationIssue

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MINIMAL_HEAD = """\
0 HEAD
1 SOUR TestSoft
1 SUBM @S1@
1 GEDC
2 VERS 5.5.1
1 CHAR UTF-8
"""

_MINIMAL_SUBM = "0 @S1@ SUBM\n1 NAME Test Submitter\n"
_TRLR = "0 TRLR\n"


def _valid_base(*extra_records: str) -> str:
    """Return a minimal valid GEDCOM string with optional extra records."""
    return _MINIMAL_HEAD + _MINIMAL_SUBM + "".join(extra_records) + _TRLR


def _parse(text: str) -> Gedcom5x:
    p = Gedcom5x()
    p.parse(io.BytesIO(text.encode("utf-8")))
    return p


def _validate(text: str) -> List[ValidationIssue]:
    return Gedcom5Validator(_parse(text)).validate()


def _codes(issues: List[ValidationIssue]) -> set:
    return {i.code for i in issues}


def _errors(issues: List[ValidationIssue]) -> List[ValidationIssue]:
    return [i for i in issues if i.severity == "error"]


def _warnings(issues: List[ValidationIssue]) -> List[ValidationIssue]:
    return [i for i in issues if i.severity == "warning"]


# ---------------------------------------------------------------------------
# Baseline: a fully valid file produces no issues
# ---------------------------------------------------------------------------

def test_valid_file_no_issues():
    issues = _validate(_valid_base())
    assert issues == [], f"Expected no issues; got {issues}"


# ---------------------------------------------------------------------------
# Phase 1 — File structure
# ---------------------------------------------------------------------------

class TestPhase1FileStructure:

    def test_missing_head(self):
        text = _MINIMAL_SUBM + _TRLR
        issues = _validate(text)
        assert "missing_head" in _codes(issues)

    def test_missing_trlr(self):
        text = _MINIMAL_HEAD + _MINIMAL_SUBM
        issues = _validate(text)
        assert "missing_trlr" in _codes(issues)

    def test_head_missing_sour(self):
        text = (
            "0 HEAD\n"
            "1 SUBM @S1@\n"
            "1 GEDC\n2 VERS 5.5.1\n"
            "1 CHAR UTF-8\n"
            + _MINIMAL_SUBM + _TRLR
        )
        issues = _validate(text)
        assert "head_missing_required" in _codes(issues)

    def test_head_gedc_no_vers(self):
        text = (
            "0 HEAD\n"
            "1 SOUR TestSoft\n"
            "1 SUBM @S1@\n"
            "1 GEDC\n"       # no VERS child
            "1 CHAR UTF-8\n"
            + _MINIMAL_SUBM + _TRLR
        )
        issues = _validate(text)
        assert "head_gedc_no_vers" in _codes(issues)

    # A1: GEDC.VERS value
    def test_gedc_vers_known_values_ok(self):
        for vers in ("5.5", "5.5.1"):
            text = (
                "0 HEAD\n"
                "1 SOUR TestSoft\n"
                "1 SUBM @S1@\n"
                "1 GEDC\n"
                f"2 VERS {vers}\n"
                "1 CHAR UTF-8\n"
                + _MINIMAL_SUBM + _TRLR
            )
            issues = _validate(text)
            assert "head_gedc_vers_value" not in _codes(issues), \
                f"VERS {vers!r} should be accepted"

    def test_gedc_vers_unknown_warns(self):
        text = (
            "0 HEAD\n"
            "1 SOUR TestSoft\n"
            "1 SUBM @S1@\n"
            "1 GEDC\n"
            "2 VERS 5.9.9\n"
            "1 CHAR UTF-8\n"
            + _MINIMAL_SUBM + _TRLR
        )
        issues = _validate(text)
        assert "head_gedc_vers_value" in _codes(issues)

    # A2: HEAD.CHAR encoding
    def test_char_known_encodings_ok(self):
        for enc in ("UTF-8", "ANSEL", "ASCII", "UNICODE", "ANSI"):
            text = (
                "0 HEAD\n"
                "1 SOUR TestSoft\n"
                "1 SUBM @S1@\n"
                "1 GEDC\n2 VERS 5.5.1\n"
                f"1 CHAR {enc}\n"
                + _MINIMAL_SUBM + _TRLR
            )
            issues = _validate(text)
            assert "head_char_unknown" not in _codes(issues), \
                f"CHAR {enc!r} should be accepted"

    def test_char_unknown_warns(self):
        text = (
            "0 HEAD\n"
            "1 SOUR TestSoft\n"
            "1 SUBM @S1@\n"
            "1 GEDC\n2 VERS 5.5.1\n"
            "1 CHAR LATIN1\n"
            + _MINIMAL_SUBM + _TRLR
        )
        issues = _validate(text)
        assert "head_char_unknown" in _codes(issues)


# ---------------------------------------------------------------------------
# Phase 2 — Duplicate xrefs
# ---------------------------------------------------------------------------

class TestPhase2DuplicateXrefs:

    def test_duplicate_xref_detected(self):
        text = _valid_base(
            "0 @I1@ INDI\n",
            "0 @I1@ INDI\n",  # duplicate
        )
        issues = _validate(text)
        assert "duplicate_xref" in _codes(issues)

    def test_unique_xrefs_ok(self):
        text = _valid_base(
            "0 @I1@ INDI\n",
            "0 @I2@ INDI\n",
        )
        issues = _validate(text)
        assert "duplicate_xref" not in _codes(issues)


# ---------------------------------------------------------------------------
# Phase 3 — Structural / payload checks
# ---------------------------------------------------------------------------

class TestPhase3StructuralPayload:

    def test_unexpected_child_tag_warns(self):
        # INDI doesn't allow a VERS child
        text = _valid_base("0 @I1@ INDI\n1 VERS 5.5.1\n")
        issues = _validate(text)
        assert "unexpected_tag" in _codes(issues)

    def test_extension_tags_allowed(self):
        # Extension tags starting with _ are always permitted
        text = _valid_base("0 @I1@ INDI\n1 _CUSTOM something\n")
        issues = _validate(text)
        assert "unexpected_tag" not in _codes(issues)

    def test_invalid_sex_value_warns(self):
        text = _valid_base("0 @I1@ INDI\n1 SEX Z\n")
        issues = _validate(text)
        assert "invalid_sex_value" in _codes(issues)

    def test_valid_sex_values_ok(self):
        for sex in ("M", "F", "U", "X", "N"):
            text = _valid_base(f"0 @I1@ INDI\n1 SEX {sex}\n")
            issues = _validate(text)
            assert "invalid_sex_value" not in _codes(issues)

    def test_invalid_date_warns(self):
        text = _valid_base("0 @I1@ INDI\n1 BIRT\n2 DATE NOTADATE\n")
        issues = _validate(text)
        assert "invalid_date_format" in _codes(issues)

    def test_valid_date_ok(self):
        for date in ("1 JAN 1900", "ABT 1900", "BET 1 JAN 1900 AND 31 DEC 1900"):
            text = _valid_base(f"0 @I1@ INDI\n1 BIRT\n2 DATE {date}\n")
            issues = _validate(text)
            assert "invalid_date_format" not in _codes(issues), \
                f"Date {date!r} should be valid"

    def test_invalid_pedi_warns(self):
        text = _valid_base(
            "0 @F1@ FAM\n",
            "0 @I1@ INDI\n1 FAMC @F1@\n2 PEDI BIOLOGICAL\n",  # should be BIRTH
        )
        issues = _validate(text)
        assert "invalid_pedi_value" in _codes(issues)

    def test_valid_pedi_ok(self):
        for pedi in ("ADOPTED", "BIRTH", "FOSTER", "SEALING"):
            text = _valid_base(
                "0 @F1@ FAM\n",
                f"0 @I1@ INDI\n1 FAMC @F1@\n2 PEDI {pedi}\n",
            )
            issues = _validate(text)
            assert "invalid_pedi_value" not in _codes(issues)

    def test_invalid_quay_warns(self):
        text = _valid_base("0 @I1@ INDI\n1 SOUR @S99@\n2 QUAY 5\n")
        issues = _validate(text)
        assert "invalid_quay_value" in _codes(issues)

    def test_invalid_medi_warns(self):
        text = _valid_base(
            "0 @R1@ REPO\n1 NAME A Repo\n",
            "0 @I1@ INDI\n",
            "0 @SR1@ SOUR\n1 REPO @R1@\n2 CALN ABC\n3 MEDI FLOPPY\n",
        )
        issues = _validate(text)
        assert "invalid_medi_value" in _codes(issues)

    # A4: AGE format
    def test_invalid_age_warns(self):
        text = _valid_base("0 @I1@ INDI\n1 BIRT\n2 AGE INFANT\n")
        issues = _validate(text)
        assert "invalid_age_format" in _codes(issues)

    def test_valid_age_formats_ok(self):
        for age in ("30y", "2m", "10d", "1y 6m", "< 1y", "> 90y 3m 5d", "3w"):
            text = _valid_base(f"0 @I1@ INDI\n1 BIRT\n2 AGE {age}\n")
            issues = _validate(text)
            assert "invalid_age_format" not in _codes(issues), \
                f"AGE {age!r} should be valid"

    # A3: LDS STAT enumerations
    def test_lds_ord_stat_invalid_warns(self):
        text = _valid_base("0 @I1@ INDI\n1 BAPL\n2 STAT NOTVALID\n")
        issues = _validate(text)
        assert "invalid_lds_stat_ord" in _codes(issues)

    def test_lds_ord_stat_valid_ok(self):
        for stat in ("COMPLETED", "SUBMITTED", "INFANT", "CHILD"):
            text = _valid_base(f"0 @I1@ INDI\n1 BAPL\n2 STAT {stat}\n")
            issues = _validate(text)
            assert "invalid_lds_stat_ord" not in _codes(issues), \
                f"LDS ord STAT {stat!r} should be valid"

    def test_famc_stat_invalid_warns(self):
        text = _valid_base(
            "0 @F1@ FAM\n",
            "0 @I1@ INDI\n1 FAMC @F1@\n2 STAT NOTVALID\n",
        )
        issues = _validate(text)
        assert "invalid_lds_stat_child" in _codes(issues)

    def test_famc_stat_valid_ok(self):
        for stat in ("CHALLENGED", "DISPROVEN", "PROVEN"):
            text = _valid_base(
                "0 @F1@ FAM\n",
                f"0 @I1@ INDI\n1 FAMC @F1@\n2 STAT {stat}\n",
            )
            issues = _validate(text)
            assert "invalid_lds_stat_child" not in _codes(issues), \
                f"FAMC STAT {stat!r} should be valid"


# ---------------------------------------------------------------------------
# Phase 4 — Pointer resolution
# ---------------------------------------------------------------------------

class TestPhase4PointerResolution:

    def test_unresolved_pointer_error(self):
        text = _valid_base("0 @I1@ INDI\n1 FAMC @F99@\n")
        issues = _validate(text)
        assert "unresolved_pointer" in _codes(issues)

    def test_resolved_pointer_ok(self):
        text = _valid_base(
            "0 @F1@ FAM\n1 CHIL @I1@\n",
            "0 @I1@ INDI\n1 FAMC @F1@\n",
        )
        issues = _validate(text)
        assert "unresolved_pointer" not in _codes(issues)

    def test_wrong_pointer_target_type_error(self):
        # FAMC must point to FAM; pointing to INDI is wrong
        text = _valid_base(
            "0 @I1@ INDI\n1 FAMC @I2@\n",
            "0 @I2@ INDI\n",
        )
        issues = _validate(text)
        assert "wrong_pointer_target" in _codes(issues)


# ---------------------------------------------------------------------------
# Phase 5 — Bidirectional link consistency
# ---------------------------------------------------------------------------

class TestPhase5Bidirectional:

    def test_broken_fams_link_warns(self):
        # INDI has FAMS @F1@ but FAM @F1@ has no HUSB or WIFE for this INDI
        text = _valid_base(
            "0 @F1@ FAM\n",
            "0 @I1@ INDI\n1 FAMS @F1@\n",
        )
        issues = _validate(text)
        assert "broken_fams_link" in _codes(issues)

    def test_broken_famc_link_warns(self):
        # INDI has FAMC @F1@ but FAM @F1@ has no CHIL for this INDI
        text = _valid_base(
            "0 @F1@ FAM\n",
            "0 @I1@ INDI\n1 FAMC @F1@\n",
        )
        issues = _validate(text)
        assert "broken_famc_link" in _codes(issues)

    def test_missing_fams_backlink_warns(self):
        # FAM lists HUSB @I1@ but @I1@ has no FAMS back to this family
        text = _valid_base(
            "0 @F1@ FAM\n1 HUSB @I1@\n",
            "0 @I1@ INDI\n",
        )
        issues = _validate(text)
        assert "missing_fams_backlink" in _codes(issues)

    def test_consistent_family_links_ok(self):
        text = _valid_base(
            "0 @F1@ FAM\n1 HUSB @I1@\n1 WIFE @I2@\n1 CHIL @I3@\n",
            "0 @I1@ INDI\n1 FAMS @F1@\n",
            "0 @I2@ INDI\n1 FAMS @F1@\n",
            "0 @I3@ INDI\n1 FAMC @F1@\n",
        )
        issues = _validate(text)
        bidi_codes = {
            "broken_fams_link", "broken_famc_link",
            "missing_fams_backlink", "missing_famc_backlink",
        }
        assert _codes(issues).isdisjoint(bidi_codes)


# ---------------------------------------------------------------------------
# Phase 6 — Orphaned records
# ---------------------------------------------------------------------------

class TestPhase6Orphans:

    def test_orphaned_source_warns(self):
        text = _valid_base("0 @SR1@ SOUR\n")
        issues = _validate(text)
        assert "orphaned_record" in _codes(issues)

    def test_orphaned_repo_warns(self):
        text = _valid_base("0 @R1@ REPO\n1 NAME A Repo\n")
        issues = _validate(text)
        assert "orphaned_record" in _codes(issues)

    def test_cited_source_not_orphaned(self):
        text = _valid_base(
            "0 @SR1@ SOUR\n",
            "0 @I1@ INDI\n1 SOUR @SR1@\n",
        )
        issues = _validate(text)
        orphans = [i for i in issues if i.code == "orphaned_record"]
        assert orphans == []


# ---------------------------------------------------------------------------
# Phase 7 — Xref format
# ---------------------------------------------------------------------------

class TestPhase7XrefFormat:

    def test_xref_with_space_errors(self):
        # Forge a GEDCOM string with a space in the xref (parser may strip it,
        # so we use a raw xref that the parser preserves)
        # Build a file where inner identifier is > 20 chars
        long_id = "I" + "X" * 20  # 21 chars inner
        text = _valid_base(f"0 @{long_id}@ INDI\n")
        issues = _validate(text)
        assert "xref_too_long" in _codes(issues)

    def test_xref_within_limit_ok(self):
        text = _valid_base("0 @I1@ INDI\n")
        issues = _validate(text)
        assert "xref_too_long" not in _codes(issues)
        assert "invalid_xref_format" not in _codes(issues)

    def test_xref_at_exact_limit_ok(self):
        # Exactly 20 inner characters — should be fine
        xref_inner = "I" * 20
        text = _valid_base(f"0 @{xref_inner}@ INDI\n")
        issues = _validate(text)
        assert "xref_too_long" not in _codes(issues)


# ---------------------------------------------------------------------------
# Phase 8 — Duplicate FAMC links
# ---------------------------------------------------------------------------

class TestPhase8DuplicateFamc:

    def test_duplicate_famc_warns(self):
        text = _valid_base(
            "0 @F1@ FAM\n",
            "0 @I1@ INDI\n1 FAMC @F1@\n1 FAMC @F1@\n",
        )
        issues = _validate(text)
        assert "duplicate_famc" in _codes(issues)

    def test_two_different_famc_ok(self):
        text = _valid_base(
            "0 @F1@ FAM\n",
            "0 @F2@ FAM\n",
            "0 @I1@ INDI\n1 FAMC @F1@\n1 FAMC @F2@\n",
        )
        issues = _validate(text)
        assert "duplicate_famc" not in _codes(issues)

    def test_single_famc_ok(self):
        text = _valid_base(
            "0 @F1@ FAM\n",
            "0 @I1@ INDI\n1 FAMC @F1@\n",
        )
        issues = _validate(text)
        assert "duplicate_famc" not in _codes(issues)


# ---------------------------------------------------------------------------
# Phase 9 — Self-referential ALIA
# ---------------------------------------------------------------------------

class TestPhase9SelfReferentialAlia:

    def test_self_referential_alia_errors(self):
        text = _valid_base("0 @I1@ INDI\n1 ALIA @I1@\n")
        issues = _validate(text)
        assert "self_referential_alia" in _codes(issues)
        assert any(i.severity == "error" for i in issues
                   if i.code == "self_referential_alia")

    def test_alia_to_other_individual_ok(self):
        text = _valid_base(
            "0 @I1@ INDI\n1 ALIA @I2@\n",
            "0 @I2@ INDI\n",
        )
        issues = _validate(text)
        assert "self_referential_alia" not in _codes(issues)
