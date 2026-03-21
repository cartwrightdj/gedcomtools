# gedcomtools

A comprehensive Python toolkit for parsing, converting, validating, and analyzing
genealogical data using the **GEDCOM 5.x**, **GEDCOM 7**, and **GEDCOM X** data models.

---

> **ALPHA SOFTWARE — v0.7.0**
>
> `gedcomtools` is under active development. Public APIs, data models, and serialization
> formats may change between releases without notice. It is not yet recommended for
> production use. Feedback and bug reports are welcome.

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
- ✅ `GedcomZip` — package a GEDCOM X graph into a portable zip archive
- ✅ O(1) collection lookups by id, URI, and name
- ✅ `ResolveStats` — reference resolution telemetry
- ✅ CLI tools (`gxcli`, `g7cli`, `validate7`)
- ✅ Structured logging (`glog`) with `GEDCOMTOOLS_DEBUG` env var support
- ✅ Sub-loggers (conversion, parser, io, etc.)
- ✅ Extensible schema / extension system
- ✅ Source, person, family, relationship modeling
- ✅ Place and event normalization with multi-language translation support
- ✅ Metadata and attribution handling
- ✅ 884 tests, 0 failures
- 🔧 GEDCOM 5.x → GEDCOM 7 converter — planned
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

### Convert GEDCOM 5.x → GEDCOM X

```python
from gedcomtools.gedcom5.parser import Gedcom5x
from gedcomtools.gedcomx.conversion import GedcomConverter

p = Gedcom5x()
p.parse_file("family.ged")

gx = GedcomConverter().Gedcom5x_GedcomX(p)

# Serialize to JSON bytes
json_bytes = gx.json
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

- [ ] GEDCOM 5.x → GEDCOM 7 converter
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
