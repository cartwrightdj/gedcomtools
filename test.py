"""
======================================================================
 Project: gedcomtools
 File:    test.py
 Purpose: Demo script — runs a GEDCOM 5 file through every conversion
          step and prints what is happening at each stage.
======================================================================
"""
from pathlib import Path

SAMPLE = Path(__file__).parent / ".sample_data" / "gedcom5" / ".djc.ged"

# ---------------------------------------------------------------------------
# Step 1: Parse GEDCOM 5
# ---------------------------------------------------------------------------
print("=" * 60)
print("STEP 1 — Parse GEDCOM 5")
print("=" * 60)

from gedcomtools.gedcom5.gedcom5 import Gedcom5

g5 = Gedcom5(SAMPLE)
version = g5.detect_gedcom_version()
individuals = g5.individual_details()
families    = g5.family_details()
sources     = g5.sources()

print(f"  File       : {SAMPLE.name}")
print(f"  Version    : GEDCOM {version}")
print(f"  Individuals: {len(individuals)}")
print(f"  Families   : {len(families)}")
print(f"  Sources    : {len(sources)}")

print()
print("  Individuals:")
for p in individuals:
    birth = p.birth_year or "?"
    death = p.death_year or "?"
    print(f"    {p.xref:10s}  {p.full_name or '(no name)':30s}  b.{birth}  d.{death}")

print()
print("  Families:")
for f in families:
    husb = f.husband_xref or "(none)"
    wife = f.wife_xref   or "(none)"
    year = f.marriage_year or "?"
    print(f"    {f.xref:10s}  HUSB={husb:10s}  WIFE={wife:10s}  married={year}  children={len(f.children_xrefs)}")

# ---------------------------------------------------------------------------
# Step 2: Validate GEDCOM 5
# ---------------------------------------------------------------------------
print()
print("=" * 60)
print("STEP 2 — Validate GEDCOM 5")
print("=" * 60)

issues = g5.validate()
errors   = [i for i in issues if i.severity == "error"]
warnings = [i for i in issues if i.severity == "warning"]

print(f"  Issues total : {len(issues)}  (errors={len(errors)}, warnings={len(warnings)})")

if errors:
    print()
    print("  Errors:")
    for i in errors[:10]:
        print(f"    [{i.code}] {i.message}")
    if len(errors) > 10:
        print(f"    … and {len(errors) - 10} more")

if warnings:
    print()
    print("  Warnings:")
    for i in warnings[:5]:
        print(f"    [{i.code}] {i.message}")
    if len(warnings) > 5:
        print(f"    … and {len(warnings) - 5} more")

if not issues:
    print("  No issues found.")

# ---------------------------------------------------------------------------
# Step 3: Convert GEDCOM 5 → GEDCOM 7  (unknown tags = drop)
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
print("  Individuals (from G7):")
for p in g7_individuals:
    birth = p.birth_year or "?"
    death = p.death_year or "?"
    print(f"    {p.xref:10s}  {p.full_name or '(no name)':30s}  b.{birth}  d.{death}")

# ---------------------------------------------------------------------------
# Step 4: Validate GEDCOM 7
# ---------------------------------------------------------------------------
print()
print("=" * 60)
print("STEP 4 — Validate GEDCOM 7")
print("=" * 60)

g7_issues   = g7.validate()
g7_errors   = [i for i in g7_issues if i.severity == "error"]
g7_warnings = [i for i in g7_issues if i.severity == "warning"]

print(f"  Issues total : {len(g7_issues)}  (errors={len(g7_errors)}, warnings={len(g7_warnings)})")

if g7_errors:
    print()
    print("  Errors:")
    for i in g7_errors[:10]:
        print(f"    [{i.code}] {i.message}")
    if len(g7_errors) > 10:
        print(f"    … and {len(g7_errors) - 10} more")

if g7_warnings:
    print()
    print("  Warnings (first 5):")
    for i in g7_warnings[:5]:
        print(f"    [{i.code}] {i.message}")
    if len(g7_warnings) > 5:
        print(f"    … and {len(g7_warnings) - 5} more")

if not g7_issues:
    print("  No issues found.")

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
    print(f"  Unhandled tags      : {dict(list(unhandled.items())[:5])}")

print()
print("  Persons:")
for person in gx.persons:
    name = person.names[0].nameForms[0].fullText if person.names and person.names[0].nameForms else "(no name)"
    gender = person.gender.type.value.split("/")[-1] if person.gender and person.gender.type else "?"
    print(f"    {person.id:10s}  {name:30s}  gender={gender}")

print()
print("  Relationships (first 10):")
from gedcomtools.gedcomx.relationship import RelationshipType
for rel in list(gx.relationships)[:10]:
    rtype  = rel.type.value.split("/")[-1] if rel.type else "?"
    p1     = rel.person1.resource.fragment if rel.person1 and rel.person1.resource else "?"
    p2     = rel.person2.resource.fragment if rel.person2 and rel.person2.resource else "?"
    print(f"    {rtype:15s}  {p1} ↔ {p2}")

# ---------------------------------------------------------------------------
# Step 6: Also convert GEDCOM 5 directly → GedcomX
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

assert False
# ---------------------------------------------------------------------------
# Step 7: Serialize GedcomX → JSON
# ---------------------------------------------------------------------------
print()
print("=" * 60)
print("STEP 7 — Serialize GedcomX to JSON")
print("=" * 60)

raw = gx.json
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
