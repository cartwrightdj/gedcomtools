"""Tests for Gedcom5.gml() / Gedcom5.write_gml() and
Gedcom7.gml() / Gedcom7.write_gml() facade methods, plus GML spec
compliance checks.

GML string encoding follows Himsolt 1997:
  - &quot;  for embedded double-quotes
  - &amp;  for ampersands
  - &#NNN; for non-ASCII / control characters
  - Backslash has no special meaning — passed through unchanged
  - [ ] have no special meaning inside quoted strings
"""
from __future__ import annotations

import re
import tempfile
from pathlib import Path

import pytest

from gedcomtools.gedcom5.gedcom5 import Gedcom5
from gedcomtools.gedcom7.gedcom7 import Gedcom7

# ---------------------------------------------------------------------------
# Sample data paths (tests that need them are skipped if absent)
# ---------------------------------------------------------------------------

_SAMPLE = Path(__file__).parent.parent / ".sample_data"
_G5_TINY = _SAMPLE / "gedcom5" / "gedcom5_sample.ged"
_G5_LARGE = _SAMPLE / "gedcom5" / "gedcom5_european_royalty_large.ged"
_G5_DJC = _SAMPLE / "gedcom5" / ".djc.ged"
_G70_DIR = _SAMPLE / "gedcom70"


# ---------------------------------------------------------------------------
# Minimal in-memory fixtures
# ---------------------------------------------------------------------------

_G5_INLINE = """\
0 HEAD
1 SOUR TEST
2 VERS 1.0
1 GEDC
2 VERS 5.5.1
1 CHAR UTF-8
0 @I1@ INDI
1 NAME Alice /Smith/
1 SEX F
1 BIRT
2 DATE 1 JAN 1925
2 PLAC London, England
1 DEAT
2 DATE 12 MAR 2000
0 @I2@ INDI
1 NAME Bob /Jones/
1 SEX M
1 BIRT
2 DATE 5 MAY 1923
1 DEAT
2 DATE 8 AUG 1998
0 @I3@ INDI
1 NAME Carol /Jones/
1 SEX F
1 BIRT
2 DATE 3 JUL 1952
0 @F1@ FAM
1 HUSB @I2@
1 WIFE @I1@
1 MARR
2 DATE 14 FEB 1950
1 CHIL @I3@
0 TRLR
"""

_G7_INLINE = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NAME Alice /Smith/
1 SEX F
0 @I2@ INDI
1 NAME Bob /Jones/
1 SEX M
0 @F1@ FAM
1 HUSB @I2@
1 WIFE @I1@
0 TRLR
"""


def _g5() -> Gedcom5:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".ged", encoding="utf-8", delete=False
    ) as f:
        f.write(_G5_INLINE)
        path = Path(f.name)
    return Gedcom5(path)


def _g7() -> Gedcom7:
    g = Gedcom7()
    g.parse_string(_G7_INLINE)
    return g


# ---------------------------------------------------------------------------
# Helpers shared by spec-compliance checks
# ---------------------------------------------------------------------------

_NODE_ATTRS = {"label", "gender", "birth_year", "birth_place",
               "death_year", "death_place", "living"}
_EDGE_ATTRS = {"source", "target", "label", "marriage_year", "divorce_year"}


def _extract_blocks(gml: str, kind: str) -> list[str]:
    """Return raw text for each ``node [...]`` or ``edge [...]`` block."""
    return re.findall(rf"  {kind} \[.*?  \]", gml, re.DOTALL)


def _attr_keys(block: str) -> set[str]:
    """Return the set of attribute key names found in a GML block."""
    return {m.group(1) for m in re.finditer(r"^\s+([a-z_]+) ", block, re.MULTILINE)}


# ---------------------------------------------------------------------------
# Gedcom5 — gml()
# ---------------------------------------------------------------------------

class TestGedcom5Gml:
    def test_returns_str(self):
        assert isinstance(_g5().gml(), str)

    def test_starts_with_graph(self):
        assert _g5().gml().startswith("graph [")

    def test_directed_flag(self):
        assert "directed 1" in _g5().gml()

    def test_ends_with_bracket(self):
        assert _g5().gml().strip().endswith("]")

    def test_has_nodes(self):
        assert _g5().gml().count("node [") >= 1

    def test_has_edges(self):
        assert _g5().gml().count("edge [") >= 1

    def test_node_count_matches_persons(self):
        g = _g5()
        out = g.gml()
        assert out.count("node [") == len(list(g.to_gedcomx().persons))

    def test_no_backslash_escapes(self):
        assert '\\"' not in _g5().gml()

    def test_no_bare_integer_custom_attrs(self):
        out = _g5().gml()
        for key in ("birth_year", "death_year", "living", "marriage_year", "divorce_year"):
            for line in out.splitlines():
                s = line.strip()
                if s.startswith(key + " "):
                    val = s[len(key) + 1:]
                    assert val.startswith('"'), f"{key} value not quoted: {val!r}"

    def test_identity_with_direct_exporter(self):
        g = _g5()
        assert g.gml() == g.to_gedcomx().gml()

    def test_names_present(self):
        out = _g5().gml()
        assert "Alice Smith" in out
        assert "Bob Jones" in out

    def test_empty_gedcom5_produces_valid_gml(self):
        out = Gedcom5().gml()
        assert "graph [" in out
        assert "node [" not in out
        assert "edge [" not in out


# ---------------------------------------------------------------------------
# Gedcom5 — write_gml()
# ---------------------------------------------------------------------------

class TestGedcom5WriteGml:
    def test_write_creates_file(self, tmp_path):
        dest = tmp_path / "out.gml"
        _g5().write_gml(dest)
        assert dest.exists()

    def test_write_content_matches_gml(self, tmp_path):
        g = _g5()
        dest = tmp_path / "out.gml"
        g.write_gml(dest)
        assert dest.read_text(encoding="utf-8") == g.gml()

    def test_write_missing_directory_raises(self, tmp_path):
        dest = tmp_path / "nonexistent" / "out.gml"
        with pytest.raises(FileNotFoundError):
            _g5().write_gml(dest)

    def test_write_no_tmp_leftover_on_error(self, tmp_path):
        dest = tmp_path / "nonexistent" / "out.gml"
        try:
            _g5().write_gml(dest)
        except FileNotFoundError:
            pass
        assert not list(tmp_path.rglob("*.tmp"))

    def test_write_accepts_str_path(self, tmp_path):
        dest = str(tmp_path / "out.gml")
        _g5().write_gml(dest)
        assert Path(dest).exists()


# ---------------------------------------------------------------------------
# Gedcom7 — gml()
# ---------------------------------------------------------------------------

class TestGedcom7Gml:
    def test_returns_str(self):
        assert isinstance(_g7().gml(), str)

    def test_starts_with_graph(self):
        assert _g7().gml().startswith("graph [")

    def test_directed_flag(self):
        assert "directed 1" in _g7().gml()

    def test_ends_with_bracket(self):
        assert _g7().gml().strip().endswith("]")

    def test_has_nodes(self):
        assert _g7().gml().count("node [") >= 1

    def test_node_count_matches_persons(self):
        g = _g7()
        out = g.gml()
        assert out.count("node [") == len(list(g.to_gedcomx().persons))

    def test_no_backslash_escapes(self):
        assert '\\"' not in _g7().gml()

    def test_no_bare_integer_custom_attrs(self):
        out = _g7().gml()
        for key in ("birth_year", "death_year", "living", "marriage_year", "divorce_year"):
            for line in out.splitlines():
                s = line.strip()
                if s.startswith(key + " "):
                    val = s[len(key) + 1:]
                    assert val.startswith('"'), f"{key} value not quoted: {val!r}"

    def test_identity_with_direct_exporter(self):
        g = _g7()
        assert g.gml() == g.to_gedcomx().gml()

    def test_names_present(self):
        out = _g7().gml()
        assert "Alice Smith" in out
        assert "Bob Jones" in out

    def test_empty_gedcom7_produces_valid_gml(self):
        out = Gedcom7().gml()
        assert "graph [" in out
        assert "node [" not in out
        assert "edge [" not in out


# ---------------------------------------------------------------------------
# Gedcom7 — write_gml()
# ---------------------------------------------------------------------------

class TestGedcom7WriteGml:
    def test_write_creates_file(self, tmp_path):
        dest = tmp_path / "out.gml"
        _g7().write_gml(dest)
        assert dest.exists()

    def test_write_content_matches_gml(self, tmp_path):
        g = _g7()
        dest = tmp_path / "out.gml"
        g.write_gml(dest)
        assert dest.read_text(encoding="utf-8") == g.gml()

    def test_write_missing_directory_raises(self, tmp_path):
        dest = tmp_path / "nonexistent" / "out.gml"
        with pytest.raises(FileNotFoundError):
            _g7().write_gml(dest)

    def test_write_no_tmp_leftover_on_error(self, tmp_path):
        dest = tmp_path / "nonexistent" / "out.gml"
        try:
            _g7().write_gml(dest)
        except FileNotFoundError:
            pass
        assert not list(tmp_path.rglob("*.tmp"))

    def test_write_accepts_str_path(self, tmp_path):
        dest = str(tmp_path / "out.gml")
        _g7().write_gml(dest)
        assert Path(dest).exists()


# ---------------------------------------------------------------------------
# GML spec compliance (Himsolt 1997)
# ---------------------------------------------------------------------------

class TestGmlSpecCompliance:
    """Verify that GML output from both facades follows the Himsolt 1997 spec.

    Key rules:
    * Strings use HTML entity references — NOT backslash escapes.
    * Only two characters must be escaped: ``"`` (→ ``&quot;``) and
      ``&`` (→ ``&amp;``).  Non-ASCII and control chars use ``&#NNN;``.
    * ``id``, ``source``, ``target`` must be bare (unquoted) integers.
    * All custom string attributes must be quoted so Gephi's attribute
      list builder can cast them to String without ClassCastException.
    * Every node must carry the same set of attributes so Gephi's
      row pre-allocation never under-sizes a node's value list.
    * Every edge must carry the same set of attributes for the same reason.
    """

    # -- G5 output used throughout this class --
    @pytest.fixture(scope="class")
    def g5_out(self):
        return _g5().gml()

    # -- G7 output used throughout this class --
    @pytest.fixture(scope="class")
    def g7_out(self):
        return _g7().gml()

    # ---- encoding correctness ----

    def test_g5_no_backslash_quote(self, g5_out):
        assert '\\"' not in g5_out, "backslash-escaped quote found — use &quot; instead"

    def test_g7_no_backslash_quote(self, g7_out):
        assert '\\"' not in g7_out

    def test_g5_quot_entity_for_embedded_quote(self):
        """A name containing a double-quote must produce &quot;."""
        from gedcomtools.gedcomx.gml import GedcomXGmlExporter
        from gedcomtools.gedcomx.gedcomx import GedcomX
        from gedcomtools.gedcomx.person import Person
        from gedcomtools.gedcomx.name import Name, NameForm
        gx = GedcomX()
        p = Person(id="@I1@")
        p.add_name(Name(nameForms=[NameForm(fullText='Isabelle "Belle" Knaval')]))
        gx.add_person(p)
        out = GedcomXGmlExporter().export(gx)
        assert "&quot;" in out
        assert '\\"' not in out

    def test_g5_amp_entity_for_ampersand(self):
        """A name containing & must produce &amp;."""
        from gedcomtools.gedcomx.gml import GedcomXGmlExporter
        from gedcomtools.gedcomx.gedcomx import GedcomX
        from gedcomtools.gedcomx.person import Person
        from gedcomtools.gedcomx.name import Name, NameForm
        gx = GedcomX()
        p = Person(id="@I1@")
        p.add_name(Name(nameForms=[NameForm(fullText="Smith & Jones")]))
        gx.add_person(p)
        out = GedcomXGmlExporter().export(gx)
        assert "&amp;" in out

    def test_g5_non_ascii_uses_numeric_entity(self):
        """Non-ASCII characters must appear as &#NNN; numeric entities."""
        from gedcomtools.gedcomx.gml import GedcomXGmlExporter
        from gedcomtools.gedcomx.gedcomx import GedcomX
        from gedcomtools.gedcomx.person import Person
        from gedcomtools.gedcomx.name import Name, NameForm
        gx = GedcomX()
        p = Person(id="@I1@")
        p.add_name(Name(nameForms=[NameForm(fullText="Ångström")]))
        gx.add_person(p)
        out = GedcomXGmlExporter().export(gx)
        # No raw non-ASCII bytes in the output
        assert all(ord(c) <= 127 for c in out), "raw non-ASCII character found in GML output"
        assert "&#" in out

    def test_g5_control_char_uses_numeric_entity(self):
        """Control characters (newline, tab) must appear as &#NNN;."""
        from gedcomtools.gedcomx.gml import GedcomXGmlExporter
        from gedcomtools.gedcomx.gedcomx import GedcomX
        from gedcomtools.gedcomx.person import Person
        from gedcomtools.gedcomx.name import Name, NameForm
        gx = GedcomX()
        p = Person(id="@I1@")
        p.add_name(Name(nameForms=[NameForm(fullText="Line1\nLine2")]))
        gx.add_person(p)
        out = GedcomXGmlExporter().export(gx)
        assert "&#10;" in out
        assert "\\n" not in out

    # ---- integer attributes ----

    def test_g5_id_is_bare_integer(self, g5_out):
        ids = re.findall(r"^\s+id (\S+)", g5_out, re.MULTILINE)
        assert ids, "no id attributes found"
        for v in ids:
            assert v.isdigit(), f"id value not a bare integer: {v!r}"

    def test_g5_source_target_are_bare_integers(self, g5_out):
        for key in ("source", "target"):
            vals = re.findall(rf"^\s+{key} (\S+)", g5_out, re.MULTILINE)
            for v in vals:
                assert v.isdigit(), f"{key} value not a bare integer: {v!r}"

    def test_g7_id_is_bare_integer(self, g7_out):
        ids = re.findall(r"^\s+id (\S+)", g7_out, re.MULTILINE)
        assert ids
        for v in ids:
            assert v.isdigit(), f"id value not a bare integer: {v!r}"

    # ---- uniform node attributes (Gephi row pre-allocation) ----

    def test_g5_all_nodes_have_same_attrs(self, g5_out):
        blocks = _extract_blocks(g5_out, "node")
        assert blocks, "no node blocks found"
        attr_sets = [_attr_keys(b) for b in blocks]
        reference = attr_sets[0]
        for i, s in enumerate(attr_sets[1:], 1):
            assert s == reference, (
                f"node {i} has different attributes than node 0: "
                f"missing={reference - s}, extra={s - reference}"
            )

    def test_g5_node_attrs_complete(self, g5_out):
        blocks = _extract_blocks(g5_out, "node")
        assert blocks
        keys = _attr_keys(blocks[0])
        missing = _NODE_ATTRS - keys
        assert not missing, f"node block missing attributes: {missing}"

    def test_g7_all_nodes_have_same_attrs(self, g7_out):
        blocks = _extract_blocks(g7_out, "node")
        assert blocks
        attr_sets = [_attr_keys(b) for b in blocks]
        reference = attr_sets[0]
        for i, s in enumerate(attr_sets[1:], 1):
            assert s == reference, (
                f"node {i} attributes differ from node 0: "
                f"missing={reference - s}, extra={s - reference}"
            )

    # ---- uniform edge attributes (Gephi row pre-allocation) ----

    def test_g5_all_edges_have_same_attrs(self, g5_out):
        blocks = _extract_blocks(g5_out, "edge")
        if not blocks:
            pytest.skip("no edges in output")
        attr_sets = [_attr_keys(b) for b in blocks]
        reference = attr_sets[0]
        for i, s in enumerate(attr_sets[1:], 1):
            assert s == reference, (
                f"edge {i} has different attributes than edge 0: "
                f"missing={reference - s}, extra={s - reference}"
            )

    def test_g5_edge_attrs_complete(self, g5_out):
        blocks = _extract_blocks(g5_out, "edge")
        if not blocks:
            pytest.skip("no edges in output")
        keys = _attr_keys(blocks[0])
        missing = _EDGE_ATTRS - keys
        assert not missing, f"edge block missing attributes: {missing}"

    def test_g7_all_edges_have_same_attrs(self, g7_out):
        blocks = _extract_blocks(g7_out, "edge")
        if not blocks:
            pytest.skip("no edges in output")
        attr_sets = [_attr_keys(b) for b in blocks]
        reference = attr_sets[0]
        for i, s in enumerate(attr_sets[1:], 1):
            assert s == reference

    # ---- brackets inside strings are fine (spec allows them) ----

    def test_g5_brackets_allowed_in_string_values(self):
        """Brackets do NOT need escaping per the GML spec."""
        from gedcomtools.gedcomx.gml import GedcomXGmlExporter
        from gedcomtools.gedcomx.gedcomx import GedcomX
        from gedcomtools.gedcomx.person import Person
        from gedcomtools.gedcomx.name import Name, NameForm
        gx = GedcomX()
        p = Person(id="@I1@")
        p.add_name(Name(nameForms=[NameForm(fullText="John [Sir] Smith")]))
        gx.add_person(p)
        out = GedcomXGmlExporter().export(gx)
        assert "John [Sir] Smith" in out


# ---------------------------------------------------------------------------
# Integration — real sample files
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _G5_TINY.exists(), reason="gedcom5 sample data not present")
class TestGedcom5GmlIntegration:
    def test_tiny_node_count(self):
        g = Gedcom5(_G5_TINY)
        gx = g.to_gedcomx()
        out = g.gml()
        assert out.count("node [") == len(list(gx.persons))

    def test_tiny_write_round_trip(self, tmp_path):
        g = Gedcom5(_G5_TINY)
        dest = tmp_path / "tiny.gml"
        g.write_gml(dest)
        assert dest.read_text(encoding="utf-8") == g.gml()

    def test_tiny_edge_count_at_most_rel_count(self):
        g = Gedcom5(_G5_TINY)
        gx = g.to_gedcomx()
        out = g.gml()
        assert out.count("edge [") <= len(list(gx.relationships))

    def test_tiny_no_raw_non_ascii(self):
        out = Gedcom5(_G5_TINY).gml()
        assert all(ord(c) <= 127 for c in out), "raw non-ASCII byte in GML output"

    def test_tiny_all_nodes_uniform(self):
        out = Gedcom5(_G5_TINY).gml()
        blocks = _extract_blocks(out, "node")
        ref = _attr_keys(blocks[0])
        for b in blocks[1:]:
            assert _attr_keys(b) == ref

    def test_tiny_all_edges_uniform(self):
        out = Gedcom5(_G5_TINY).gml()
        blocks = _extract_blocks(out, "edge")
        if not blocks:
            pytest.skip("no edges")
        ref = _attr_keys(blocks[0])
        for b in blocks[1:]:
            assert _attr_keys(b) == ref


@pytest.mark.skipif(
    not any(_G70_DIR.glob("*.ged")) if _G70_DIR.exists() else True,
    reason="gedcom70 sample data not present",
)
class TestGedcom7GmlIntegration:
    @pytest.fixture(scope="class")
    def g7_sample(self):
        path = next(_G70_DIR.glob("*.ged"))
        g = Gedcom7(path)
        return g

    def test_node_count_matches_persons(self, g7_sample):
        gx = g7_sample.to_gedcomx()
        out = g7_sample.gml()
        assert out.count("node [") == len(list(gx.persons))

    def test_write_round_trip(self, g7_sample, tmp_path):
        dest = tmp_path / "g7.gml"
        g7_sample.write_gml(dest)
        assert dest.read_text(encoding="utf-8") == g7_sample.gml()

    def test_no_raw_non_ascii(self, g7_sample):
        out = g7_sample.gml()
        assert all(ord(c) <= 127 for c in out)

    def test_all_nodes_uniform(self, g7_sample):
        out = g7_sample.gml()
        blocks = _extract_blocks(out, "node")
        if not blocks:
            pytest.skip("no nodes")
        ref = _attr_keys(blocks[0])
        for b in blocks[1:]:
            assert _attr_keys(b) == ref
