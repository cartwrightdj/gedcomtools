"""
======================================================================
 Project: gedcomtools
 File:    gedcomx/gml.py
 Purpose: Export a GedcomX object graph to GML (Graph Modelling
          Language), readable by Gephi, yEd, NetworkX, and other
          graph tools.

 Created: 2026-03-25
======================================================================

Design
------
Persons become **nodes**; Couple and ParentChild relationships become
directed **edges** (person1 → person2).  Each node and edge carries
a small set of genealogically useful attributes so the graph can be
styled and filtered by name, gender, birth/death year, etc.

Node attributes
  id          Sequential integer (GML requires integer node IDs).
  label       Display name (full text of the primary NameForm).
  gender      "Male" | "Female" | "Unknown" | "Intersex".
  birth_year  Four-digit integer, or omitted if unknown.
  birth_place Place name string, or omitted.
  death_year  Four-digit integer, or omitted if unknown.
  death_place Place name string, or omitted.
  living      1 if the living flag is True, 0 otherwise.

Edge attributes
  source / target  Node IDs for person1 and person2.
  label            "Couple" | "ParentChild".
  marriage_year    (Couple only) year of first Marriage fact, if known.
  divorce_year     (Couple only) year of first Divorce fact, if known.

GML string quoting follows the informal standard used by Gephi/yEd:
double-quoted, with backslash-escaped backslashes and double-quotes.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from .gedcomx import GedcomX


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _gml_str(value: str) -> str:
    """Encode *value* as a GML string literal.

    The GML spec (Himsolt 1997) uses HTML/XML entity references — NOT
    backslash escapes.  Backslash has no special meaning in GML; using ``\"``
    terminates the string early because the parser sees a literal backslash
    then a closing double-quote.

    Encoding rules applied:
    * ``"``   → ``&quot;``  (only character that would close the literal)
    * ``&``   → ``&amp;``   (introduces entity references)
    * non-printable / non-ASCII → ``&#NNN;`` numeric entity
    * All other printable ASCII including ``[ ] \\`` → passed through unchanged
    """
    out: list[str] = []
    for ch in value:
        if ch == '"':
            out.append("&quot;")
        elif ch == "&":
            out.append("&amp;")
        elif ord(ch) < 32 or ord(ch) > 126:
            out.append(f"&#{ord(ch)};")
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


def _year_from_date(date_obj) -> Optional[int]:
    """Extract the four-digit year from a GedcomX Date object."""
    if date_obj is None:
        return None
    formal = getattr(date_obj, "formal", None)
    if formal:
        # GedcomX formal dates: +YYYY, +YYYY-MM, +YYYY-MM-DD, A+YYYY…
        m = re.match(r"[A\[/]*[+\-]?(\d{4})", formal.lstrip())
        if m:
            return int(m.group(1))
    original = getattr(date_obj, "original", None)
    if original:
        m = re.search(r"\b(\d{4})\b", original)
        if m:
            return int(m.group(1))
    return None


def _place_name(place_ref) -> Optional[str]:
    """Extract a place name string from a PlaceReference."""
    if place_ref is None:
        return None
    original = getattr(place_ref, "original", None)
    if original:
        return original
    desc = getattr(place_ref, "description", None)
    if desc is not None:
        names = getattr(desc, "names", None)
        if names:
            tv = names[0]
            return getattr(tv, "value", None) or getattr(tv, "text", None)
    return None


def _resolve_person_id(ref) -> Optional[str]:
    """Return the GedcomX person id from a Person object or Resource ref."""
    if ref is None:
        return None
    # Person object has both .id and .names
    if hasattr(ref, "names"):
        return getattr(ref, "id", None)
    # Resource: prefer fragment of .resource URI, fall back to .resourceId
    uri = getattr(ref, "resource", None)
    if uri is not None:
        frag = getattr(uri, "fragment", None)
        if frag:
            return frag
    rid = getattr(ref, "resourceId", None)
    if rid:
        return rid
    return getattr(ref, "id", None)


def _person_label(person) -> str:
    """Return the display name for *person*, or a placeholder if absent."""
    names = getattr(person, "names", None)
    if names:
        for name in names:
            forms = getattr(name, "nameForms", None)
            if forms and forms[0]:
                text = getattr(forms[0], "fullText", None)
                if text:
                    return text
    return f"({getattr(person, 'id', '?')})"


def _gender_label(person) -> Optional[str]:
    gender = getattr(person, "gender", None)
    if gender is None:
        return None
    gtype = getattr(gender, "type", None)
    if gtype is None:
        return None
    name = getattr(gtype, "name", None)
    return name  # "Male", "Female", "Unknown", "Intersex"


def _first_fact_of_type(facts: list, *type_names: str):
    """Return the first Fact whose FactType.name matches one of *type_names*."""
    for fact in facts:
        ftype = getattr(fact, "type", None)
        fname = getattr(ftype, "name", "") if ftype else ""
        if fname in type_names:
            return fact
    return None


# ---------------------------------------------------------------------------
# GML block builders
# ---------------------------------------------------------------------------

def _node_block(gml_id: int, person) -> str:
    # Gephi's GML importer pre-allocates each node's attribute row based on
    # columns seen so far.  If a later node introduces a new column, calling
    # row.set(newIndex, value) on the already-sized list throws
    # IndexOutOfBoundsException.  The fix is to emit ALL attributes on every
    # node, using an empty string "" as a sentinel for absent values so that
    # every node has the same column set.
    facts = getattr(person, "facts", []) or []
    birth = _first_fact_of_type(facts, "Birth")
    death = _first_fact_of_type(facts, "Death")
    living = getattr(person, "living", None)

    by = _year_from_date(getattr(birth, "date", None)) if birth else None
    bp = _place_name(getattr(birth, "place", None)) if birth else None
    dy = _year_from_date(getattr(death, "date", None)) if death else None
    dp = _place_name(getattr(death, "place", None)) if death else None
    gender = _gender_label(person)

    lines: List[str] = [
        "  node [",
        f"    id {gml_id}",
        f"    label {_gml_str(_person_label(person))}",
        f"    gender {_gml_str(gender or '')}",
        f"    birth_year {_gml_str(str(by) if by is not None else '')}",
        f"    birth_place {_gml_str(bp or '')}",
        f"    death_year {_gml_str(str(dy) if dy is not None else '')}",
        f"    death_place {_gml_str(dp or '')}",
        f"    living {_gml_str('true' if living else 'false')}",
        "  ]",
    ]
    return "\n".join(lines)


def _edge_block(
    source: int,
    target: int,
    label: str,
    *,
    marriage_year: Optional[int] = None,
    divorce_year: Optional[int] = None,
) -> str:
    # Emit all attributes on every edge (same reasoning as _node_block —
    # Gephi's row pre-allocation bug requires a consistent attribute set).
    lines: List[str] = [
        "  edge [",
        f"    source {source}",
        f"    target {target}",
        f"    label {_gml_str(label)}",
        f"    marriage_year {_gml_str(str(marriage_year) if marriage_year is not None else '')}",
        f"    divorce_year {_gml_str(str(divorce_year) if divorce_year is not None else '')}",
        "  ]",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public exporter
# ---------------------------------------------------------------------------

class GedcomXGmlExporter:
    """Serialize a :class:`~gedcomtools.gedcomx.GedcomX` graph to GML.

    Example::

        from gedcomtools.gedcomx.gml import GedcomXGmlExporter

        exporter = GedcomXGmlExporter()
        exporter.write(gx, "family.gml")
        text = exporter.export(gx)
    """

    def export(self, gx: "GedcomX") -> str:
        """Serialize *gx* to a GML string.

        Args:
            gx: Populated GedcomX object.

        Returns:
            Complete GML content as a ``str``.
        """
        # Build a stable integer-ID → person mapping
        id_map: Dict[str, int] = {}
        node_blocks: List[str] = []

        for idx, person in enumerate(gx.persons):
            pid = getattr(person, "id", None) or str(idx)
            id_map[pid] = idx
            node_blocks.append(_node_block(idx, person))

        edge_blocks: List[str] = []

        for rel in gx.relationships:
            p1_gx_id = _resolve_person_id(getattr(rel, "person1", None))
            p2_gx_id = _resolve_person_id(getattr(rel, "person2", None))
            if p1_gx_id not in id_map or p2_gx_id not in id_map:
                continue  # dangling reference — skip

            src = id_map[p1_gx_id]
            tgt = id_map[p2_gx_id]
            rtype = getattr(rel, "type", None)
            rname = getattr(rtype, "name", "Unknown") if rtype else "Unknown"

            kwargs: dict = {}
            facts = getattr(rel, "facts", []) or []
            if rname == "Couple":
                marr = _first_fact_of_type(facts, "Marriage", "CommonLawMarriage",
                                           "CivilUnion", "DomesticPartnership")
                if marr:
                    kwargs["marriage_year"] = _year_from_date(
                        getattr(marr, "date", None)
                    )
                div = _first_fact_of_type(facts, "Divorce", "Annulment",
                                          "Separation")
                if div:
                    kwargs["divorce_year"] = _year_from_date(
                        getattr(div, "date", None)
                    )

            edge_blocks.append(_edge_block(src, tgt, rname, **kwargs))

        sections = ["graph [", "  directed 1"]
        sections.extend(node_blocks)
        sections.extend(edge_blocks)
        sections.append("]")
        return "\n".join(sections) + "\n"

    def write(
        self,
        gx: "GedcomX",
        filepath: str | Path,
        *,
        encoding: str = "utf-8",
    ) -> None:
        """Write *gx* to a GML file.

        Args:
            gx:       Populated GedcomX object.
            filepath: Destination path.  Parent directory must exist.
            encoding: File encoding (default UTF-8).

        Raises:
            FileNotFoundError: If the parent directory does not exist.
        """
        dest = Path(filepath)
        content = self.export(gx)
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        try:
            tmp.write_text(content, encoding=encoding)
            tmp.replace(dest)
        except FileNotFoundError as exc:
            tmp.unlink(missing_ok=True)
            raise FileNotFoundError(
                f"Cannot write to {dest}: parent directory does not exist."
            ) from exc
        except Exception:
            tmp.unlink(missing_ok=True)
            raise
