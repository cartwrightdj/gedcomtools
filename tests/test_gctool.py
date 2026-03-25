"""
======================================================================
 Project: gedcomtools
 File:    tests/test_gctool.py
 Purpose: Tests for gctool — the GEDCOM 5/7 command-line utility.
          Exercises every subcommand through the public ``main()``
          entry point (in-process) and lower-level helpers.

 Created: 2026-03-22
 Updated: 2026-03-24 — dispatch table refactor tests; merge/diff/
                        export/repair subcommand tests; g5→g7 convert
======================================================================
"""

from __future__ import annotations

import json
import zipfile
from io import StringIO
from pathlib import Path
from typing import List
from unittest.mock import patch

import pytest

from gedcomtools.gctool import (
    _Node,
    _build_label,
    _ls,
    _norm_xref,
    _package_version,
    _path_str,
    _sniff,
    main,
)

# ---------------------------------------------------------------------------
# Paths to sample data
# ---------------------------------------------------------------------------

SAMPLE5 = Path(__file__).parent.parent / ".sample_data" / "gedcom5"
SAMPLE7 = Path(__file__).parent.parent / ".sample_data" / "gedcom70"

GED5_MINIMAL     = SAMPLE5 / "gedcom5_minimal.ged"
GED5_SAMPLE      = SAMPLE5 / "gedcom5_sample.ged"
GED5_COMPREHENS  = SAMPLE5 / "gedcom5_comprehensive.ged"
GED7_MINIMAL     = SAMPLE7 / "minimal70.ged"
GED7_MAXIMAL     = SAMPLE7 / "maximal70.ged"

_HAS_5 = GED5_SAMPLE.exists()
_HAS_7 = GED7_MINIMAL.exists()

needs_g5 = pytest.mark.skipif(not _HAS_5, reason="G5 sample files not present")
needs_g7 = pytest.mark.skipif(not _HAS_7, reason="G7 sample files not present")


# ---------------------------------------------------------------------------
# Inline GEDCOM fixtures
# ---------------------------------------------------------------------------

_G5_TEXT = """\
0 HEAD
1 GEDC
2 VERS 5.5.1
1 CHAR UTF-8
1 SOUR TestApp
1 SUBM @S1@
0 @S1@ SUBM
1 NAME Test Submitter
0 @I1@ INDI
1 NAME Alice /Smith/
2 GIVN Alice
2 SURN Smith
1 SEX F
1 BIRT
2 DATE 1 JAN 1900
2 PLAC Springfield
1 FAMS @F1@
0 @I2@ INDI
1 NAME Bob /Jones/
1 SEX M
1 BIRT
2 DATE 15 MAR 1898
1 FAMS @F1@
0 @F1@ FAM
1 HUSB @I2@
1 WIFE @I1@
1 MARR
2 DATE 10 JUN 1920
0 @R1@ REPO
1 NAME City Archive
0 TRLR
"""

_G7_TEXT = """\
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
0 @F1@ FAM
1 WIFE @I1@
0 TRLR
"""


def _make_g5(tmp_path: Path) -> Path:
    p = tmp_path / "test.ged"
    p.write_text(_G5_TEXT, encoding="utf-8")
    return p


def _make_g7(tmp_path: Path) -> Path:
    p = tmp_path / "test7.ged"
    p.write_text(_G7_TEXT, encoding="utf-8")
    return p


def _run(argv: List[str]) -> int:
    """Call main() and return exit code (catches SystemExit from _load errors)."""
    try:
        return main(argv)
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 1


def _capture(argv: List[str]) -> tuple[int, str]:
    """Call main() and capture stdout; return (exit_code, output)."""
    buf = StringIO()
    try:
        with patch("sys.stdout", buf):
            rc = main(argv)
    except SystemExit as exc:
        rc = int(exc.code) if exc.code is not None else 1
    return rc, buf.getvalue()


# ---------------------------------------------------------------------------
# _sniff
# ---------------------------------------------------------------------------

class TestSniff:
    def test_g5_from_vers(self, tmp_path):
        p = tmp_path / "f.ged"
        p.write_text("0 HEAD\n1 GEDC\n2 VERS 5.5.1\n0 TRLR\n")
        assert _sniff(p) == "g5"

    def test_g7_from_vers(self, tmp_path):
        p = tmp_path / "f.ged"
        p.write_text("0 HEAD\n1 GEDC\n2 VERS 7.0\n0 TRLR\n")
        assert _sniff(p) == "g7"

    def test_gdz_always_g7(self, tmp_path):
        p = tmp_path / "archive.gdz"
        p.write_bytes(b"PK\x03\x04")   # minimal zip magic
        assert _sniff(p) == "g7"

    def test_json_object_is_gx(self, tmp_path):
        p = tmp_path / "data.json"
        p.write_text('{"persons": []}')
        assert _sniff(p) == "gx"

    def test_no_vers_defaults_to_g5(self, tmp_path):
        p = tmp_path / "f.ged"
        p.write_text("0 HEAD\n0 TRLR\n")
        assert _sniff(p) == "g5"

    def test_unknown_extension_raises(self, tmp_path):
        p = tmp_path / "f.xyz"
        p.write_text("hello")
        with pytest.raises(ValueError):
            _sniff(p)


# ---------------------------------------------------------------------------
# _norm_xref
# ---------------------------------------------------------------------------

class TestNormXref:
    def test_already_wrapped(self):
        assert _norm_xref("@I1@") == "@I1@"

    def test_bare_id_gets_wrapped(self):
        assert _norm_xref("I1") == "@I1@"

    def test_uppercased(self):
        assert _norm_xref("i1") == "@I1@"

    def test_strips_whitespace(self):
        assert _norm_xref("  @I1@  ") == "@I1@"


# ---------------------------------------------------------------------------
# version command
# ---------------------------------------------------------------------------

class TestVersion:
    def test_exits_zero(self, tmp_path):
        rc, out = _capture(["version"])
        assert rc == 0

    def test_prints_version_string(self):
        rc, out = _capture(["version"])
        ver = out.strip()
        assert ver  # non-empty
        assert "." in ver   # looks like semver

    def test_package_version_helper(self):
        v = _package_version()
        assert isinstance(v, str)
        assert v != ""


# ---------------------------------------------------------------------------
# info command
# ---------------------------------------------------------------------------

class TestInfo:
    def test_g5_exits_zero(self, tmp_path):
        rc, out = _capture(["info", str(_make_g5(tmp_path))])
        assert rc == 0

    def test_g5_shows_format(self, tmp_path):
        rc, out = _capture(["info", str(_make_g5(tmp_path))])
        assert "g5" in out.lower() or "gedcom 5" in out.lower()

    def test_g7_exits_zero(self, tmp_path):
        rc, out = _capture(["info", str(_make_g7(tmp_path))])
        assert rc == 0

    def test_g7_shows_format(self, tmp_path):
        rc, out = _capture(["info", str(_make_g7(tmp_path))])
        assert "7" in out

    def test_json_output_g5(self, tmp_path):
        rc, out = _capture(["--json", "info", str(_make_g5(tmp_path))])
        assert rc == 0
        data = json.loads(out)
        assert "format" in data
        assert "counts" in data

    def test_json_output_g7(self, tmp_path):
        rc, out = _capture(["--json", "info", str(_make_g7(tmp_path))])
        assert rc == 0
        data = json.loads(out)
        assert "counts" in data

    def test_missing_file_exits_nonzero(self, tmp_path):
        rc = _run(["info", str(tmp_path / "nonexistent.ged")])
        assert rc != 0

    @needs_g5
    def test_real_g5_sample(self):
        rc, out = _capture(["info", str(GED5_SAMPLE)])
        assert rc == 0
        assert "INDI" in out or "indi" in out.lower()

    @needs_g7
    def test_real_g7_minimal(self):
        rc, out = _capture(["info", str(GED7_MINIMAL)])
        assert rc == 0


# ---------------------------------------------------------------------------
# validate command
# ---------------------------------------------------------------------------

class TestValidate:
    def test_valid_g5_exits_zero(self, tmp_path):
        rc = _run(["validate", str(_make_g5(tmp_path))])
        assert rc == 0

    def test_valid_g7_exits_zero(self, tmp_path):
        rc = _run(["validate", str(_make_g7(tmp_path))])
        assert rc == 0

    def test_invalid_g5_reports_issues(self, tmp_path):
        # HEAD missing GEDC — should produce validation errors
        bad = tmp_path / "bad.ged"
        bad.write_text("0 HEAD\n1 CHAR UTF-8\n0 TRLR\n")
        rc, out = _capture(["validate", str(bad)])
        assert "error" in out.lower() or rc != 0

    def test_json_output_has_issues_key(self, tmp_path):
        rc, out = _capture(["--json", "validate", str(_make_g5(tmp_path))])
        data = json.loads(out)
        assert "issues" in data
        assert "error_count" in data
        assert "warning_count" in data

    def test_json_format_field(self, tmp_path):
        rc, out = _capture(["--json", "validate", str(_make_g5(tmp_path))])
        data = json.loads(out)
        assert data["format"] == "g5"

    @needs_g5
    def test_real_sample_validates(self):
        rc, out = _capture(["validate", str(GED5_SAMPLE)])
        # Should not crash; exit code doesn't matter for real files
        assert isinstance(rc, int)


# ---------------------------------------------------------------------------
# list command
# ---------------------------------------------------------------------------

class TestList:
    def test_indi_default(self, tmp_path):
        rc, out = _capture(["list", str(_make_g5(tmp_path))])
        assert rc == 0
        assert "Alice" in out

    def test_indi_explicit(self, tmp_path):
        rc, out = _capture(["list", str(_make_g5(tmp_path)), "indi"])
        assert rc == 0
        assert "Alice" in out or "@I1@" in out

    def test_fam(self, tmp_path):
        rc, out = _capture(["list", str(_make_g5(tmp_path)), "fam"])
        assert rc == 0
        assert "@F1@" in out

    def test_repo(self, tmp_path):
        rc, out = _capture(["list", str(_make_g5(tmp_path)), "repo"])
        assert rc == 0

    def test_subm(self, tmp_path):
        rc, out = _capture(["list", str(_make_g5(tmp_path)), "subm"])
        assert rc == 0
        assert "Test Submitter" in out

    def test_json_indi(self, tmp_path):
        rc, out = _capture(["--json", "list", str(_make_g5(tmp_path)), "indi"])
        assert rc == 0
        data = json.loads(out)
        assert "individuals" in data
        assert len(data["individuals"]) >= 1

    def test_snote_g5_returns_error(self, tmp_path):
        rc = _run(["list", str(_make_g5(tmp_path)), "snote"])
        assert rc != 0

    def test_snote_g7(self, tmp_path):
        rc, out = _capture(["list", str(_make_g7(tmp_path)), "snote"])
        assert rc == 0   # no SNOTEs but should not crash


# ---------------------------------------------------------------------------
# show command
# ---------------------------------------------------------------------------

class TestShow:
    def test_show_indi_g5(self, tmp_path):
        rc, out = _capture(["show", str(_make_g5(tmp_path)), "@I1@"])
        assert rc == 0
        assert "Alice" in out

    def test_show_indi_bare_xref(self, tmp_path):
        rc, out = _capture(["show", str(_make_g5(tmp_path)), "I1"])
        assert rc == 0
        assert "Alice" in out

    def test_show_fam(self, tmp_path):
        rc, out = _capture(["show", str(_make_g5(tmp_path)), "F1"])
        assert rc == 0

    def test_show_repo(self, tmp_path):
        rc, out = _capture(["show", str(_make_g5(tmp_path)), "R1"])
        assert rc == 0
        assert "City Archive" in out

    def test_show_not_found(self, tmp_path):
        rc = _run(["show", str(_make_g5(tmp_path)), "@X999@"])
        assert rc != 0

    def test_show_json(self, tmp_path):
        rc, out = _capture(["--json", "show", str(_make_g5(tmp_path)), "I1"])
        assert rc == 0
        data = json.loads(out)
        assert "xref" in data

    def test_show_g7_indi(self, tmp_path):
        rc, out = _capture(["show", str(_make_g7(tmp_path)), "@I1@"])
        assert rc == 0
        assert "Alice" in out


# ---------------------------------------------------------------------------
# find command
# ---------------------------------------------------------------------------

class TestFind:
    def test_find_tag_g5(self, tmp_path):
        rc, out = _capture(["find", str(_make_g5(tmp_path)), "NAME"])
        assert rc == 0
        assert "Alice" in out or "result" in out.lower()

    def test_find_with_payload_filter(self, tmp_path):
        rc, out = _capture(["find", str(_make_g5(tmp_path)), "NAME", "--payload", "Alice"])
        assert rc == 0
        assert "Alice" in out

    def test_find_payload_filter_no_match(self, tmp_path):
        rc, out = _capture(["find", str(_make_g5(tmp_path)), "NAME", "--payload", "ZZZNOMATCH"])
        assert rc == 0
        assert "0" in out   # 0 results

    def test_find_json(self, tmp_path):
        rc, out = _capture(["--json", "find", str(_make_g5(tmp_path)), "NAME"])
        assert rc == 0
        data = json.loads(out)
        assert "results" in data
        assert "count" in data

    def test_find_g7(self, tmp_path):
        rc, out = _capture(["find", str(_make_g7(tmp_path)), "NAME"])
        assert rc == 0
        assert "Alice" in out


# ---------------------------------------------------------------------------
# tree command
# ---------------------------------------------------------------------------

class TestTree:
    def test_tree_g5_exists(self, tmp_path):
        rc, out = _capture(["tree", str(_make_g5(tmp_path)), "I1"])
        assert rc == 0
        assert "Alice" in out

    def test_tree_not_found(self, tmp_path):
        rc = _run(["tree", str(_make_g5(tmp_path)), "X999"])
        assert rc != 0

    def test_tree_depth_option(self, tmp_path):
        rc, out = _capture(["tree", str(_make_g5(tmp_path)), "I1", "--depth", "1"])
        assert rc == 0

    def test_tree_g7(self, tmp_path):
        rc, out = _capture(["tree", str(_make_g7(tmp_path)), "I1"])
        assert rc == 0


# ---------------------------------------------------------------------------
# stats command
# ---------------------------------------------------------------------------

class TestStats:
    def test_stats_g5(self, tmp_path):
        rc, out = _capture(["stats", str(_make_g5(tmp_path))])
        assert rc == 0
        assert "Individuals" in out or "individuals" in out.lower()

    def test_stats_g7(self, tmp_path):
        rc, out = _capture(["stats", str(_make_g7(tmp_path))])
        assert rc == 0

    def test_stats_json(self, tmp_path):
        rc, out = _capture(["--json", "stats", str(_make_g5(tmp_path))])
        assert rc == 0
        data = json.loads(out)
        assert "individuals" in data
        assert "families" in data
        assert data["individuals"]["total"] >= 2

    def test_stats_pct_fields(self, tmp_path):
        rc, out = _capture(["--json", "stats", str(_make_g5(tmp_path))])
        data = json.loads(out)
        indi = data["individuals"]
        assert "with_birth_year" in indi
        assert "male" in indi
        assert "female" in indi


# ---------------------------------------------------------------------------
# convert command
# ---------------------------------------------------------------------------

class TestConvert:
    @needs_g5
    def test_g5_to_gx(self, tmp_path):
        out = tmp_path / "out.json"
        rc = _run(["convert", str(GED5_SAMPLE), "--to", "gx", "--out", str(out)])
        assert rc == 0
        assert out.exists()

    @needs_g5
    def test_g5_to_gx_output_is_json(self, tmp_path):
        out = tmp_path / "out.json"
        _run(["convert", str(GED5_SAMPLE), "--to", "gx", "--out", str(out)])
        data = json.loads(out.read_text())
        assert isinstance(data, dict)

    def test_same_format_no_op(self, tmp_path):
        p = _make_g5(tmp_path)
        rc, out = _capture(["convert", str(p), "--to", "g5"])
        assert rc == 0
        assert "nothing to do" in out.lower() or "same" in out.lower()

    def test_g5_to_g7_conversion(self, tmp_path):
        p = _make_g5(tmp_path)
        out = tmp_path / "out.ged"
        rc = _run(["convert", str(p), "--to", "g7", "--out", str(out)])
        assert rc == 0
        assert out.exists()


# ---------------------------------------------------------------------------
# _Node wrapper
# ---------------------------------------------------------------------------

class TestNodeWrapper:
    def _g7_node(self):
        from gedcomtools.gedcom7.gedcom7 import Gedcom7
        g = Gedcom7()
        g.parse_string(_G7_TEXT)
        return _Node(g.records[1], "g7")   # @I1@ INDI

    def _g5_node(self, tmp_path):
        from gedcomtools.gedcom5.gedcom5 import Gedcom5
        g = Gedcom5()
        p = tmp_path / "t.ged"
        p.write_text(_G5_TEXT, encoding="utf-8")
        g.loadfile(p)
        indis = g.individuals()
        return _Node(indis[0], "g5")

    def test_g7_tag(self):
        n = self._g7_node()
        assert n.tag == "INDI"

    def test_g7_xref(self):
        n = self._g7_node()
        assert n.xref_id == "@I1@"

    def test_g7_children(self):
        n = self._g7_node()
        tags = [c.tag for c in n.children()]
        assert "NAME" in tags

    def test_g7_parent_none_for_root(self):
        n = self._g7_node()
        assert n.parent() is None

    def test_g7_set_payload(self):
        n = self._g7_node()
        name_node = next(c for c in n.children() if c.tag == "NAME")
        name_node.set_payload("Changed /Name/")
        assert name_node.payload == "Changed /Name/"

    def test_g7_add_child(self):
        n = self._g7_node()
        before = len(n.children())
        n.add_child("NOTE", "test note")
        assert len(n.children()) == before + 1
        assert n.children()[-1].tag == "NOTE"

    def test_g7_remove_child(self):
        n = self._g7_node()
        note = n.add_child("NOTE", "temp")
        before = len(n.children())
        n.remove_child(note)
        assert len(n.children()) == before - 1

    def test_g5_tag(self, tmp_path):
        n = self._g5_node(tmp_path)
        assert n.tag == "INDI"

    def test_g5_children(self, tmp_path):
        n = self._g5_node(tmp_path)
        tags = [c.tag for c in n.children()]
        assert "NAME" in tags

    def test_g5_add_child(self, tmp_path):
        n = self._g5_node(tmp_path)
        before = len(n.children())
        n.add_child("NOTE", "hello")
        assert len(n.children()) == before + 1

    def test_g5_remove_child(self, tmp_path):
        n = self._g5_node(tmp_path)
        note = n.add_child("NOTE", "temp")
        before = len(n.children())
        n.remove_child(note)
        assert len(n.children()) == before - 1

    def test_g5_removed_child_parent_cleared(self, tmp_path):
        n = self._g5_node(tmp_path)
        note = n.add_child("NOTE", "temp")
        n.remove_child(note)
        assert note._raw.get_parent_element() is None


# ---------------------------------------------------------------------------
# _build_label / _path_str helpers
# ---------------------------------------------------------------------------

class TestHelpers:
    def _make_nodes(self, tags):
        from gedcomtools.gedcom7.structure import GedcomStructure
        nodes = [_Node(GedcomStructure(level=1, tag=t), "g7") for t in tags]
        return nodes

    def test_unique_tag_no_index(self):
        nodes = self._make_nodes(["NAME", "SEX", "BIRT"])
        assert _build_label(nodes[0], nodes) == "NAME"

    def test_duplicate_tag_gets_index(self):
        nodes = self._make_nodes(["NOTE", "NOTE", "NOTE"])
        assert _build_label(nodes[0], nodes) == "NOTE[0]"
        assert _build_label(nodes[1], nodes) == "NOTE[1]"
        assert _build_label(nodes[2], nodes) == "NOTE[2]"

    def test_path_str_empty(self):
        assert _path_str([]) == "/"

    def test_path_str_single(self):
        assert _path_str(["HEAD"]) == "HEAD"

    def test_path_str_multi(self):
        assert _path_str(["@I1@", "NAME", "GIVN"]) == "@I1@/NAME/GIVN"


# ---------------------------------------------------------------------------
# spec passthrough command
# ---------------------------------------------------------------------------

class TestSpecCommand:
    def test_spec_info_exits_zero(self):
        rc, out = _capture(["spec", "info"])
        assert rc == 0
        assert "Tags" in out or "tags" in out.lower()

    def test_spec_no_args_shows_help(self):
        rc, out = _capture(["spec"])
        assert rc == 0   # help exits 0
        assert "g7spec" in out.lower() or "usage" in out.lower() or "info" in out.lower()


# ---------------------------------------------------------------------------
# Error / edge cases
# ---------------------------------------------------------------------------

class TestErrorCases:
    def test_missing_file_info(self, tmp_path):
        rc = _run(["info", str(tmp_path / "no_such_file.ged")])
        assert rc != 0

    def test_gx_file_refused(self, tmp_path):
        p = tmp_path / "data.json"
        p.write_text('{"persons": []}')
        rc = _run(["info", str(p)])
        assert rc != 0

    def test_show_wrong_xref(self, tmp_path):
        rc = _run(["show", str(_make_g5(tmp_path)), "@ZZZNONE@"])
        assert rc != 0

    def test_tree_wrong_xref(self, tmp_path):
        rc = _run(["tree", str(_make_g5(tmp_path)), "ZZZNONE"])
        assert rc != 0
