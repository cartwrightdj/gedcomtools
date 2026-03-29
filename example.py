"""
======================================================================
 Project: gedcomtools
 File:    test.py
 Purpose: Demo script — runs a GEDCOM 5 file through every conversion
          step and prints what is happening at each stage.
======================================================================
"""
import os
os.environ.setdefault("LOG_CONSOLE", "0")

from collections import Counter
from pathlib import Path

SAMPLE = Path(__file__).parent / ".sample_data" / "gedcom5" / ".djc.ged"

# Max rows to print in list sections before truncating
_LIST_LIMIT = 10

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _issue_table(issues, title="Validation issues"):
    """Print a summary table of validation issues grouped by code."""
    errors   = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]
    print(f"  {title}: {len(issues)} total  "
          f"(errors={len(errors)}, warnings={len(warnings)})")
    if not issues:
        print("  No issues found.")
        return

    # Count by (severity, code)
    counts = Counter((i.severity, i.code) for i in issues)
    rows = sorted(counts.items(), key=lambda x: (-x[1], x[0][0]))

    # Column widths
    max_code = max(len(code) for (_, code), _ in rows)
    col = max(max_code, 8)

    print()
    print(f"    {'Sev':<8} {'Code':<{col}}  {'Count':>6}  Example")
    print(f"    {'-'*8} {'-'*col}  {'-'*6}  {'-'*40}")
    for (sev, code), n in rows:
        example = next((i.message for i in issues if i.code == code), "")
        if len(example) > 60:
            example = example[:57] + "..."
        print(f"    {sev:<8} {code:<{col}}  {n:>6}  {example}")

    # Root-cause notes
    _print_root_causes({code for (_, code), _ in rows})


_ROOT_CAUSE_NOTES = {
    "invalid_date_format": (
        "Date values do not match GEDCOM date grammar — "
        "e.g. '1999-2017' (ISO range) should be 'BET 1999 AND 2017'."
    ),
    "illegal_substructure": (
        "Extension tags (e.g. _WLNK) carry substructures (TITL, NOTE) "
        "that the GEDCOM 7 spec does not define for them. "
        "The converter preserves the extension but the validator flags unknown children."
    ),
    "line_too_long": (
        "PAGE (source citation page) values exceed the 255-char recommended "
        "line length. The data is preserved but oversized."
    ),
    "dangling_pointer": (
        "Source xrefs referenced by SOUR citations do not exist in the "
        "converted file — likely records dropped during G5→G7 conversion "
        "or originally missing from the source file."
    ),
    "orphaned_record": (
        "OBJE records defined in the file but not cited by any other record. "
        "These are data quality issues in the source file, not conversion errors."
    ),
    "cardinality_exceeded": (
        "SEX tag appears more than once on an INDI record. "
        "Duplicate SEX entries in the source file — GEDCOM 7 allows exactly one."
    ),
}


def _print_root_causes(codes):
    found = {c: _ROOT_CAUSE_NOTES[c] for c in codes if c in _ROOT_CAUSE_NOTES}
    if not found:
        return
    print()
    print("  Root causes:")
    for code, note in found.items():
        print(f"    [{code}]")
        # wrap at 72 chars
        words = note.split()
        line, prefix = "      ", "      "
        for word in words:
            if len(line) + len(word) + 1 > 76:
                print(line)
                line = prefix + word
            else:
                line = (line + " " + word).lstrip() if line == prefix else line + " " + word
        if line.strip():
            print(line)

def main() -> None:
    """Run the end-to-end demo pipeline and print each conversion step."""

    # ---------------------------------------------------------------------------
    # Step 1: Parse GEDCOM 5
    # ---------------------------------------------------------------------------
    print("=" * 60)
    print("STEP 1 — Parse GEDCOM 5")
    print("=" * 60)

    from gedcomtools.gedcom5.gedcom5 import Gedcom5

    g5 = Gedcom5(SAMPLE)
    version     = g5.detect_gedcom_version()
    individuals = g5.individual_details()
    families    = g5.family_details()
    sources     = g5.sources()

    print(f"  File       : {SAMPLE.name}")
    print(f"  Version    : GEDCOM {version}")
    print(f"  Individuals: {len(individuals)}")
    print(f"  Families   : {len(families)}")
    print(f"  Sources    : {len(sources)}")

    print()
    print(f"  Individuals (first {_LIST_LIMIT}):")
    for p in individuals[:_LIST_LIMIT]:
        birth = p.birth_year or "?"
        death = p.death_year or "?"
        print(f"    {p.xref:15s}  {p.full_name or '(no name)':30s}  b.{birth}  d.{death}")
    if len(individuals) > _LIST_LIMIT:
        print(f"    … and {len(individuals) - _LIST_LIMIT} more")

    print()
    print(f"  Families (first {_LIST_LIMIT}):")
    for f in families[:_LIST_LIMIT]:
        husb = f.husband_xref or "(none)"
        wife = f.wife_xref   or "(none)"
        year = f.marriage_year or "?"
        print(f"    {f.xref:15s}  HUSB={husb:15s}  WIFE={wife:15s}  married={year}  children={len(f.children_xrefs)}")
    if len(families) > _LIST_LIMIT:
        print(f"    … and {len(families) - _LIST_LIMIT} more")

    # ---------------------------------------------------------------------------
    # Step 2: Validate GEDCOM 5
    # ---------------------------------------------------------------------------
    print()
    print("=" * 60)
    print("STEP 2 — Validate GEDCOM 5")
    print("=" * 60)

    _issue_table(g5.validate(), "GEDCOM 5 validation")

    # ---------------------------------------------------------------------------
    # Step 3: Convert GEDCOM 5 → GEDCOM 7
    # ---------------------------------------------------------------------------
    print()
    print("=" * 60)
    print("STEP 3 — Convert GEDCOM 5 → GEDCOM 7  (unknown_tags='drop')")
    print("=" * 60)

    g7 = g5.to_gedcom7(unknown_tags="drop")

    g7_individuals = g7.individual_details()
    g7_families    = g7.family_details()
    g7_sources     = g7.sources()
    g7_version     = g7.detect_gedcom_version()

    print(f"  Result type : {type(g7).__name__}")
    print(f"  Version     : GEDCOM {g7_version}")
    print(f"  Individuals : {len(g7_individuals)}")
    print(f"  Families    : {len(g7_families)}")
    print(f"  Sources     : {len(g7_sources)}")

    print()
    print(f"  Individuals (first {_LIST_LIMIT}):")
    for p in g7_individuals[:_LIST_LIMIT]:
        birth = p.birth_year or "?"
        death = p.death_year or "?"
        print(f"    {p.xref:15s}  {p.full_name or '(no name)':30s}  b.{birth}  d.{death}")
    if len(g7_individuals) > _LIST_LIMIT:
        print(f"    … and {len(g7_individuals) - _LIST_LIMIT} more")

    # ---------------------------------------------------------------------------
    # Step 4: Validate GEDCOM 7  — issue table with root-cause notes
    # ---------------------------------------------------------------------------
    print()
    print("=" * 60)
    print("STEP 4 — Validate GEDCOM 7")
    print("=" * 60)

    _issue_table(g7.validate(), "GEDCOM 7 validation after G5→G7 conversion")

    # ---------------------------------------------------------------------------
    # Step 5: Convert GEDCOM 7 → GedcomX
    # ---------------------------------------------------------------------------
    print()
    print("=" * 60)
    print("STEP 5 — Convert GEDCOM 7 → GedcomX")
    print("=" * 60)

    gx = g7.to_gedcomx()

    print(f"  Result type         : {type(gx).__name__}")
    print(f"  Persons             : {len(gx.persons)}")
    print(f"  Relationships       : {len(gx.relationships)}")
    print(f"  Source descriptions : {len(gx.sourceDescriptions)}")
    print(f"  Agents              : {len(gx.agents)}")
    print(f"  Places              : {len(gx.places)}")

    unhandled = getattr(gx, "_import_unhandled_tags", {})
    if unhandled:
        top = sorted(unhandled.items(), key=lambda x: -x[1])[:8]
        print(f"  Unhandled G7 tags   : {dict(top)}")

    print()
    print(f"  Persons (first {_LIST_LIMIT}):")
    for person in list(gx.persons)[:_LIST_LIMIT]:
        name = (person.names[0].nameForms[0].fullText
                if person.names and person.names[0].nameForms else "(no name)")
        gender = (person.gender.type.value.split("/")[-1]
                  if person.gender and person.gender.type else "?")
        print(f"    {person.id:15s}  {name:30s}  gender={gender}")
    if len(gx.persons) > _LIST_LIMIT:
        print(f"    … and {len(gx.persons) - _LIST_LIMIT} more")

    print()
    from gedcomtools.gedcomx.relationship import RelationshipType
    couple_rels = [r for r in gx.relationships if r.type == RelationshipType.Couple]
    pc_rels     = [r for r in gx.relationships if r.type == RelationshipType.ParentChild]
    print(f"  Relationships breakdown:")
    print(f"    Couple      : {len(couple_rels)}")
    print(f"    ParentChild : {len(pc_rels)}")

    # ---------------------------------------------------------------------------
    # Step 6: Convert GEDCOM 5 directly → GedcomX  (shortcut path)
    # ---------------------------------------------------------------------------
    print()
    print("=" * 60)
    print("STEP 6 — Convert GEDCOM 5 directly → GedcomX  (shortcut path)")
    print("=" * 60)

    gx_direct = g5.to_gedcomx()

    print(f"  Result type         : {type(gx_direct).__name__}")
    print(f"  Persons             : {len(gx_direct.persons)}")
    print(f"  Relationships       : {len(gx_direct.relationships)}")
    print(f"  Source descriptions : {len(gx_direct.sourceDescriptions)}")

    # ---------------------------------------------------------------------------
    # Step 7: Serialize GedcomX → JSON
    # ---------------------------------------------------------------------------
    print()
    print("=" * 60)
    print("STEP 7 — Serialize GedcomX to JSON")
    print("=" * 60)

    raw     = gx.json
    size_kb = len(raw) / 1024

    print(f"  JSON bytes  : {len(raw):,}")
    print(f"  JSON size   : {size_kb:.1f} KB")
    print()
    print("  First 300 characters of JSON:")
    print("  " + raw[:300].decode("utf-8"))

    print()
    print("=" * 60)
    print("Done.")
    print("=" * 60)


if __name__ == "__main__":
    main()
