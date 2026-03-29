# gedcomtools

A comprehensive Python toolkit for parsing, converting, validating, and analyzing
genealogical data using the **GEDCOM 5.x**, **GEDCOM 7**, and **GEDCOM X** data models.

---

> **ALPHA SOFTWARE — v0.7.3-dev**
>
> `gedcomtools` is under active development. Public APIs, data models, and serialization
> formats may change between releases without notice. It is not yet recommended for
> production use. Feedback and bug reports are welcome.

---

## What's New (development)

### GML graph export

A new `gml.py` module exports a GedcomX object graph to **GML (Graph Modelling Language)**,
readable by Gephi, yEd, NetworkX, and other graph tools. Persons become nodes; Couple and
ParentChild relationships become directed edges.

```python
from gedcomtools.gedcomx.gml import to_gml

gml_text = to_gml(gx)
with open("family.gml", "w") as f:
    f.write(gml_text)
```

Node attributes: `id`, `label` (primary name), `gender`, `birth_year`, `birth_place`,
`death_year`, `death_place`, `living`. Edge attributes: `source`, `target`, `label`
(relationship type), `rel_type`.

### Expanded `gxcli` interactive shell

The `gxcli` REPL was significantly expanded with new commands:

| Command | Description |
|---|---|
| `ahnentafel` / `ahnen` | Ancestor numbering — set, add, tree, export (decimal/binary/GEDCOM formats) |
| `grep` PATTERN | Recursive regex search across entire object tree |
| `schema` | Browse schema: `here`, `class`, `find`, `where`, `bases`, `toplevel`, `json`, `diff` |
| `bookmark` / `bm` | Named bookmarks for quick navigation |
| `dump` | Serialize current node to JSON |
| `resolve` | Resolve resource references at current node |
| `write` FORMAT | Export to `gx`, `zip`, `jsonl`, or `adbg` format |
| `log` LEVEL | Set runtime log level |
| `cfg` | Persistent configuration (set/get/tree/import/export) |
| `ext` | Load, unload, and trust plugins |

### OBJE multimedia support

GEDCOM `OBJE` (multimedia object) records are now handled in both the G5→GX and G7→GX
converters. `OBJE` records produce `SourceDescription(resourceType=DigitalArtifact)` with
MIME type detection from the file extension.

### PEDI and ABBR tag support

- `PEDI` (pedigree linkage type: `adopted`, `birth`, `foster`, `sealing`) is now preserved
  as a qualifier on `ParentChild` relationships in both the G7→GX and G5→GX paths.
- `ABBR` (source abbreviation) is stored as a note on `SourceDescription`.

### Improved date parsing (G5 → G7)

The GEDCOM 5 → GEDCOM 7 date converter (`g5tog7.py`) now handles a wider range of
date formats including approximate dates (`ABT`, `CAL`, `EST`), date ranges
(`BEF`, `AFT`, `BET … AND …`), and French Republican / Hebrew calendar indicators.

### Model correctness fixes

- **`Agent.__eq__`** redesigned: person reference takes priority (if set, equality
  is determined entirely by person match); falls back to case-insensitive name overlap
  when person is `None`. `Agent.__hash__ = None` — mutable objects are no longer
  accidentally hashable.
- **`Conclusion.__hash__ = None`** — consistent with value-based `__eq__` and mutable
  list fields (`sources`, `notes`).
- **`Identifier.values`** — mutable default `[]` replaced with `Field(default_factory=list)`.
  Previously all `Identifier` instances without an explicit `values` argument shared the
  same list.
- **`Agent.sorted_names`** — new read-only property returning names sorted alphabetically
  (case-insensitive). `names[0]` primary-name order is preserved in the stored list.

### Type annotation improvements

Forward-reference circular imports resolved via `TYPE_CHECKING` guards and
`model_rebuild()` calls, replacing several `Optional[Any]` fields with proper types:

| Field | Before | After |
|---|---|---|
| `Relationship.person1` / `.person2` | `Optional[Any]` | `Optional[Union[Person, Resource]]` |
| `EventRole.person` | `Optional[Any]` | `Optional[Union[Person, Resource]]` |
| `PlaceDescription.jurisdiction` | `Optional[Any]` | `Optional[Union[Resource, PlaceDescription]]` |
| `PlaceDescription.spatialDescription` | `Optional[Any]` | `Optional[PlaceReference]` |

### Event conversion bug fix

`handle_even` in `conversion.py` used the wrong `object_map` index (`record.level`
instead of `record.level-1`) when creating an `EventRole` for an unknown EVEN type,
silently assigning the wrong object (e.g. a `Note`) as the person. The fix adds the
same parent-type guards (`Person` / `SourceDescription`) that the known-type branches
already used.

---

## What's New in v0.7.2

### GEDCOM 7 → GedcomX converter

A new `Gedcom7Converter` converts a parsed GEDCOM 7 file directly to GedcomX.
It uses the pre-assembled `Detail` objects from `gedcom7/models.py` so no
level-tracking stack is needed.

```python
from gedcomtools.gedcom7.gedcom7 import Gedcom7

g7 = Gedcom7("family.ged")
gx = g7.to_gedcomx()           # returns GedcomX
with open("family.json", "wb") as f:
    f.write(gx.json)
```

Or use the converter directly:

```python
from gedcomtools.gedcom7.g7togx import Gedcom7Converter

gx = Gedcom7Converter().convert(g7)
```

**What is converted:**

| GEDCOM 7 | GedcomX |
|---|---|
| `INDI` | `Person` (id = xref) |
| `INDI.NAME` + parts | `Name` / `NameForm` / `NamePart` (Given, Surname, Prefix, Suffix) |
| `INDI.NAME.TRAN` | additional `NameForm` with `lang` |
| `INDI.SEX` M/F/X/U | `Gender` (Male/Female/Intersex/Unknown) |
| `INDI.BIRT/DEAT/BURI/…` | `Fact` with `Date`, `PlaceReference`, source citations |
| `INDI.OCCU/TITL/RELI/NATI` | attribute `Fact` with `value` |
| `FAM` (HUSB + WIFE) | `Relationship(type=Couple)` with marriage/divorce facts |
| `FAM.CHIL` | `Relationship(type=ParentChild)` per parent × child |
| `SOUR` | `SourceDescription` with title, notes, repository link |
| `REPO` | `Agent` with name, address, phone, email, homepage |
| `SUBM` | `Agent` with name, address, contact info |
| `OBJE` | `SourceDescription(resourceType=DigitalArtifact)` |
| `SNOTE` | `SourceDescription(resourceType=Record)` carrying the note text |
| `HEAD.DATE` / `HEAD.SUBM` | `GedcomX.attribution` |
| Place names | deduplicated `PlaceDescription`; facts reference via `{"resource": "#id"}` |

### Facade conversion methods

All three parsers now expose conversion methods that return the correct
high-level type — not a raw list, not a dict:

```python
# Gedcom5
g5 = Gedcom5("family.ged")
g7 = g5.to_gedcom7()           # → Gedcom7
gx = g5.to_gedcomx()           # → GedcomX

# Gedcom7
g7 = Gedcom7("family.ged")
gx = g7.to_gedcomx()           # → GedcomX

# Full chain
gx = Gedcom5("family.ged").to_gedcom7().to_gedcomx()
```

`to_gedcom7()` previously returned a raw `List[GedcomStructure]`. It now
returns a fully constructed `Gedcom7` object (with tag index), so all
`Gedcom7` accessors (`individuals()`, `validate()`, `write()`, etc.) work
immediately on the result.

### Return-type test suite

A new `tests/test_conversion_return_types.py` module verifies that every
conversion method returns the correct type. Each test includes both a positive
`isinstance` check and a negative check (not a `list`, not a `dict`) so
regressions like the `to_gedcom7()` list-return bug are caught immediately.

---

## What's New in v0.7.1

### GEDCOM 5 → GEDCOM 7 converter

A new `Gedcom5to7` converter translates GEDCOM 5.x files to GEDCOM 7 format.
The converter is available via the `gedcomtools convert` CLI or directly in Python:

```python
from gedcomtools.gedcom5.gedcom5 import Gedcom5
from gedcomtools.gedcom5.g5tog7 import Gedcom5to7
from gedcomtools.gedcom7.writer import Gedcom7Writer

g5 = Gedcom5("family.ged")
conv = Gedcom5to7(unknown_tags="convert")   # or "drop"
records = conv.convert(g5)
for w in conv.warnings:
    print(f"  warning: {w}")
Gedcom7Writer().write(records, "family7.ged")
```

The `unknown_tags` option controls vendor and non-standard G5 tags
(`RIN`, `FSID`, `AFN`, `WWW`, `ADR4`–`ADR6`):

| Value | Behaviour |
|---|---|
| `"drop"` *(default)* | Tags are silently discarded |
| `"convert"` | Tags are renamed to `_TAG` extension tags and declared in `HEAD.SCHMA` |

### Unified `gedcomtools convert` CLI

A single entry-point replaces the previous format-specific CLI tools:

```bash
# GEDCOM 5 → GEDCOM X JSON
gedcomtools convert family.ged family.json -gx

# GEDCOM 5 → GEDCOM 7
gedcomtools convert family.ged family7.ged -g7

# Preserve vendor tags as extension tags during G5→G7
gedcomtools convert family.ged family7.ged -g7 --on-unknown convert
```

Source format is detected automatically from file content (the `2 VERS` header
tag) and extension. The `--on-unknown` flag only applies to the G5→G7 path.

### Pydantic migration: broken resource references — and the fix

The v0.7.0 Pydantic migration introduced a serialization regression in the
GEDCOM X layer. Cross-references that should have been written as compact
`{"resource": "#id"}` pointers were instead being inlined as full copies of the
referenced object — causing output JSON files to be an order of magnitude larger
than expected and breaking the spec-required reference model.

**Root causes:**

1. **`_GXModel` short-circuit placed too early.** `Serialization.serialize`
   detected pydantic models and immediately called `model_dump()`, bypassing the
   field-type lookup that was responsible for deciding when to emit a resource
   reference instead of an inline object. Any field typed `Optional[Any]` (a
   common migration escape-hatch) also lost its union type information at runtime,
   so the lookup silently fell through.

2. **`GedcomX._serializer` / `_as_dict` bypassed the serializer.** The container
   object had its own serialization path that called `model_dump()` recursively,
   never reaching `Resource._of_object`.

3. **`IdentifierList._serializer` used Python-mode `model_dump()`.** URIs were
   returned as Python objects instead of JSON-compatible strings, causing
   `TypeError: Type is not JSON serializable: URI` downstream.

**Fixes applied:**

- **`_RESOURCE_REF_FIELDS`** — an explicit table of `{class_name: {field_names}}`
  that must always serialize as resource references, regardless of annotation.
  The full MRO is walked so inherited fields (e.g. `Conclusion.analysis` on
  `Person`) are covered.
- **`_normalize_field_type`** — strips `Optional[X]` wrappers and resolves union
  types (preferring `Resource` when it appears) before the field-type dispatch.
- **Short-circuit removed** — the `_GXModel` fast-path now sits *after* the
  field-type loop as a fallback for pydantic models with no registered schema
  fields, not before it.
- **`GedcomX._to_dict()`** — replaces `_serializer` / `_as_dict`; calls
  `Serialization.serialize()` for each item in every collection so the full
  resource-ref path is always taken.
- **`IdentifierList._serializer`** — fixed to `model_dump(mode="json")` so URIs
  are serialized to strings.
- **`Resource._of_object` hardened** — now handles `dict` inputs (already-
  serialized refs that appear on a second round-trip) and objects with no `id`
  attribute (logs a warning and continues instead of raising `AttributeError`).

A regression test (`TestConversionLarge.test_json_size_within_expected_range`)
was added: it serializes the Royal92 large real-world file and asserts the output
stays under 5 MB. Inlining all objects instead of using resource references
pushes the same file above 40 MB, making size a reliable canary for this class
of bug.

---

## What's New in v0.7.0

### Migration to Pydantic v2

The entire GEDCOM X object model (`gedcomtools.gedcomx`) has been rewritten on
**Pydantic v2**. The previous implementation used plain Python classes with manual
`__init__` and `to_dict` methods. Pydantic brings:

- **Automatic validation** — type errors and structural violations are caught at
  assignment time, not silently at serialization.
- **Zero type errors** — the full model passes Pyright strict-mode with 0 errors.
- **`model_validate` / `model_dump`** — standard round-trip serialization replaces
  bespoke `from_dict` / `to_dict` plumbing.
- **`model_post_init`** — replaces fragile `__post_init__` patterns and ensures
  computed fields (e.g. URI fragments) are always in sync.
- **Pydantic `Field` defaults** — mutable defaults (lists, dicts) are now safe;
  no more shared-state bugs from `default=[]`.
- **`model_validator(mode="before")`** — input normalization (e.g. URI parsing)
  runs before field assignment, keeping models clean.
- **`ConfigDict`** — fine-grained control over immutability, extra fields, and
  arbitrary types where needed (e.g. `TypeCollection`).

The migration also cleaned up a large amount of dead code, removed private file
references from git history, and consolidated the logging layer into `glog.py`.

### New functionality in v0.7.0

#### TRAN (Translation / Transliteration) support
GEDCOM 5.5.1 `TRAN` tags are now converted to GEDCOM X:
- `NAME TRAN` → additional `NameForm` with `lang` set from the `LANG` child tag
- `NOTE TRAN` → sibling `Note` with translated text and `lang`
- `TITL TRAN` → translated `TextValue`
- `FORM` under `TRAN` (script hint) is preserved on `NameForm.fullText`

#### `GedcomZip` packaging
GEDCOM X objects can be packaged into a standard zip archive:

```python
from gedcomtools.gedcomx.zip import GedcomZip

with GedcomZip("export.zip") as gz:
    gz.add_object_as_resource(gx)
```

#### O(1) collection lookups
`TypeCollection` now maintains three indexes (`_id_index`, `_uri_index`,
`_name_index`) so `by_id()`, `by_uri()`, and `by_name()` are constant-time
regardless of collection size. The name index uses `dict[str, dict[int, T]]`
(keyed by `id(item)`) to avoid requiring pydantic models to be hashable.

#### `ResolveStats` telemetry
Reference resolution now returns a `ResolveStats` dataclass with counters for
total refs, cache hits/misses, successes, failures, and timing:

```python
from gedcomtools.gedcomx.serialization import Serialization, ResolveStats

stats = ResolveStats()
Serialization._resolve_structure(gx, gx._resolve, stats=stats)
print(stats.resolved_ok, stats.resolved_fail)
```

#### Flexible date/coordinate types
Several fields that GEDCOM populates with human-readable strings are now typed
to accept both structured objects and raw strings:

| Field | Previous type | Now |
|---|---|---|
| `Attribution.modified` / `.created` | `datetime` | `Union[datetime, str]` |
| `SourceDescription.published` / `.created` / `.modified` | `Date` | `Union[Date, str]` |
| `PlaceDescription.latitude` / `.longitude` | `float` | `Union[float, str]` |

This eliminates serialization warnings from GEDCOM files that store dates like
`"23 Jun 2008"` or coordinates like `"N40.896"`.

#### Expanded test suite — 884 tests
New test modules added this release:

| File | Coverage |
|---|---|
| `tests/gedcom5/test_gedcom5_official.py` | All 6 local `555*.GED` sample files; UTF-16 BE/LE encoding; live download from `gedcom.org` |
| `tests/test_gedcom5_individual.py` | `IndividualRecord` API: names, gender, birth/death data, flags |
| `tests/test_gedcomx_roundtrip.py` | GEDCOM 5 → GedcomX → JSON → GedcomX round-trip; double round-trip stability; reference resolution |
| `tests/test_gedcomx_validation_rules.py` | Pydantic mirror-model validation rules for Person, Name, Relationship, Resource |
| `tests/test_zip.py` | `GedcomZip` archive structure, content validity, context manager |

---

## Features

- ✅ GEDCOM 5.x parser (`gedcom5`)
- ✅ GEDCOM 7 parser, 18-phase validator, serializer, and high-level models (`gedcom7`)
- ✅ GEDCOM X **Pydantic v2** object model (`gedcomx`) — complete, 0 Pyright errors
- ✅ GEDCOM X per-property validation (`validate()` on every model)
- ✅ Converter — GEDCOM 5.x → GEDCOM X (including TRAN, FONE, multi-language names)
- ✅ Converter — GEDCOM 5.x → GEDCOM 7 (vendor tag drop/convert via `--on-unknown`)
- ✅ Converter — GEDCOM 7 → GedcomX (`Gedcom7Converter` / `g7.to_gedcomx()`)
- ✅ Facade conversion methods on all parsers — `to_gedcom7()`, `to_gedcomx()` return correct types
- ✅ Full conversion chain: `Gedcom5 → Gedcom7 → GedcomX` in one expression
- ✅ `gedcomtools convert` unified CLI — auto-detects source format, supports g5→gx and g5→g7
- ✅ `GedcomZip` — package a GEDCOM X graph into a portable zip archive
- ✅ O(1) collection lookups by id, URI, and name
- ✅ `ResolveStats` — reference resolution telemetry
- ✅ Correct `{"resource": "#id"}` pointer serialization — resource references are never inlined
- ✅ CLI tools (`gedcomtools`, `gxcli`, `g7cli`, `validate7`)
- ✅ Structured logging (`glog`) with `GEDCOMTOOLS_DEBUG` env var support
- ✅ Sub-loggers (conversion, parser, io, etc.)
- ✅ Extensible schema / extension system with TrustLevel plugin security
- ✅ Source, person, family, relationship modeling
- ✅ Place and event normalization with multi-language translation support
- ✅ Metadata and attribution handling
- ✅ OBJE multimedia record support (G5→GX and G7→GX)
- ✅ PEDI pedigree linkage and ABBR abbreviation tag support
- ✅ GML graph export — Gephi / yEd / NetworkX compatible
- ✅ Expanded `gxcli` — ahnentafel, grep, schema browser, bookmarks, plugin manager
- ✅ Correct `Agent.__eq__` — person-reference priority with name-overlap fallback
- ✅ ~1145 tests, 0 failures
- 🔧 GEDCOM X → GEDCOM 7 converter — planned
- 🔧 Graph database export (ArangoDB) — in progress

---

## Project Structure

```
gedcomtools/
├── gedcom5/                # GEDCOM 5.x parsing layer
│   ├── gedcom5.py          # High-level facade (Gedcom5)
│   ├── parser.py           # Low-level parser engine (Gedcom5x)
│   ├── elements.py         # Typed element/record classes
│   ├── helpers.py          # Element query helpers
│   ├── tags.py             # GEDCOM 5.x tag constants
│   └── source.py           # Source record helpers
├── gedcom7/                # GEDCOM 7 parsing, validation, and serialization
│   ├── gedcom7.py          # Parser + Gedcom7 class
│   ├── structure.py        # In-memory tree node (GedcomStructure)
│   ├── validator.py        # 18-phase structural/semantic validator
│   ├── writer.py           # GEDCOM 7 serializer
│   ├── models.py           # High-level detail dataclasses
│   ├── specification.py    # Tag rules, cardinality, enumerations
│   ├── g7interop.py        # Tag ↔ URI mapping
│   ├── exceptions.py       # Exception hierarchy
│   ├── g7cli.py            # Interactive browser/editor shell
│   └── validate7.py        # validate7 CLI entry point
├── gedcomx/                # GEDCOM X object model (Pydantic v2)
│   ├── gedcomx.py          # GedcomX root object + TypeCollection
│   ├── conversion.py       # GEDCOM 5 → GEDCOM X converter
│   ├── serialization.py    # JSON serialize / deserialize + ResolveStats
│   ├── zip.py              # GedcomZip archive packaging
│   ├── person.py           # Person model
│   ├── relationship.py     # Relationship model
│   ├── name.py             # Name / NameForm / NamePart
│   ├── fact.py             # Fact / FactType
│   ├── source_description.py
│   ├── agent.py
│   ├── place_description.py
│   ├── attribution.py
│   └── ...                 # date, note, identifier, uri, resource, ...
├── glog.py                 # Structured logging (loguru-based)
├── cli.py                  # gedcomtools CLI entry point
└── utils/                  # Shared utilities
```

---

## Installation

```bash
pip install gedcomtools
```

Or from source:

```bash
git clone https://github.com/cartwrightdj/gedcomtools.git
cd gedcomtools
pip install -e .
```

---

## Quick Start

### Parse GEDCOM 5.x

```python
from gedcomtools.gedcom5 import Gedcom5

g = Gedcom5("family.ged")

for person in g.individual_details():
    print(person.full_name, person.birth_year, person.death_year)

for family in g.family_details():
    print(family.husband_xref, family.wife_xref, family.marriage_year)
```

### Parse and validate GEDCOM 7

```python
from gedcomtools.gedcom7 import Gedcom7

g = Gedcom7("family.ged")

issues = g.validate()
for issue in issues:
    print(f"[{issue.severity}] {issue.code}: {issue.message}")

# Write back out
g.write("family_out.ged")
```

### Convert between formats

All parsers expose `to_gedcom7()` and `to_gedcomx()` convenience methods
that return the correct high-level type:

```python
from gedcomtools.gedcom5.gedcom5 import Gedcom5
from gedcomtools.gedcom7.gedcom7 import Gedcom7

# GEDCOM 5 → GEDCOM 7
g5 = Gedcom5("family.ged")
g7 = g5.to_gedcom7()           # returns Gedcom7
g7.write("family7.ged")

# GEDCOM 5 → GedcomX
gx = g5.to_gedcomx()           # returns GedcomX
with open("family.json", "wb") as f:
    f.write(gx.json)

# GEDCOM 7 → GedcomX
g7 = Gedcom7("family7.ged")
gx = g7.to_gedcomx()           # returns GedcomX

# Full chain in one expression
gx = Gedcom5("family.ged").to_gedcom7().to_gedcomx()
```

### Round-trip JSON serialization

```python
import json
from gedcomtools.gedcomx.gedcomx import GedcomX
from gedcomtools.gedcomx.serialization import Serialization

data = json.loads(gx.json)
gx2 = Serialization.deserialize(data, GedcomX)

print(len(gx2.persons), "persons restored")
```

### Package as a GEDCOM X zip archive

```python
from gedcomtools.gedcomx.zip import GedcomZip

with GedcomZip("export.zip") as gz:
    gz.add_object_as_resource(gx)
```

### Validate a GEDCOM X object graph

Every model supports recursive validation with type and completeness checks:

```python
result = gx.validate()
for issue in result.errors:
    print(f"[error] {issue.path}: {issue.message}")
for issue in result.warnings:
    print(f"[warn]  {issue.path}: {issue.message}")
```

### Access GEDCOM 7 high-level models

```python
from gedcomtools.gedcom7 import Gedcom7
from gedcomtools.gedcom7.models import individual_detail

g = Gedcom7("family.ged")
for indi_node in g["INDI"]:
    p = individual_detail(indi_node)
    print(p.full_name, p.birth_year, p.death_year)
    # Access place translations (PLAC.TRAN)
    if p.birth and p.birth.place_translations:
        print(p.birth.place_translations.get("de"))
    # Access name translations (NAME.TRAN)
    for tran in (p.name.translations if p.name else []):
        print(f"  [{tran.lang}] {tran.display}")
```

---

## CLI Tools

### `gedcomtools convert` — format converter

```bash
# GEDCOM 5 → GEDCOM X JSON (auto-detects source format)
gedcomtools convert family.ged output.json -gx

# GEDCOM 5 → GEDCOM 7
gedcomtools convert family.ged output.ged -g7

# Drop vendor/non-standard tags during G5→G7 (default)
gedcomtools convert family.ged output.ged -g7 --on-unknown drop

# Rename vendor tags to _TAG extension tags instead of dropping them
gedcomtools convert family.ged output.ged -g7 --on-unknown convert
```

| Exit code | Meaning |
|---|---|
| 0 | Success |
| 1 | Source file not found |
| 2 | Cannot determine source format |
| 3 | Conversion not supported for this format pair |
| 4 | Conversion failed (parse or transform error) |
| 5 | I/O error writing output |

### `validate7` — GEDCOM 7 validator

```bash
validate7 family.ged
validate7 --lenient family.ged   # suppress undeclared extension tag errors
```

| Exit code | Meaning |
|---|---|
| 0 | Clean (warnings may still be printed) |
| 1 | One or more validation errors |
| 2 | Not a GEDCOM 7 file |
| 3 | File not found or cannot be read |

### `g7cli` — interactive GEDCOM 7 browser/editor

```bash
g7cli family.ged
```

Commands: `load`, `reload`, `write`, `validate`, `info`, `ls`, `cd`, `pwd`,
`show`, `find`, `set`, `add`, `rm`, `help`, `quit`.

### `gxcli` — GEDCOM X CLI

```bash
gxcli convert input.ged output.json
```

---

## Logging

The project uses `glog` (loguru-based) for structured logging.

```python
from gedcomtools.glog import get_logger

log = get_logger("conversion")
log.info("Starting conversion")
```

Set `GEDCOMTOOLS_DEBUG=1` in your environment to enable debug output.

---

## Design Goals

- Pydantic v2 throughout GEDCOM X — validation at the boundary, not at serialization
- Centralized logging control — no side effects on import
- Extensible schema support
- Accurate GEDCOM X modeling against the published specification
- Robust error reporting at every layer
- CLI + API parity
- Clear separation of concerns between parsing, conversion, and serialization

---

## Roadmap

- [ ] GEDCOM X → GEDCOM 7 converter
- [ ] JSON-LD export
- [ ] RAG pipeline integration
- [ ] Graph database export (ArangoDB)

---

## License

MIT License

---

## Author

David J. Cartwright

---

> Build genealogy tooling like infrastructure: structured, observable, extensible.
