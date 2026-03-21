# gedcomtools

A comprehensive Python toolkit for parsing, converting, validating, and analyzing
genealogical data using the **GEDCOM 5.x**, **GEDCOM 7**, and **GEDCOM X** data models.

`gedcomtools` provides:
- GEDCOM 5.x parser and high-level facade
- GEDCOM 7 parser, 18-phase validator, serializer, and interactive CLI
- GEDCOM X structured object model
- GEDCOM 5.x → GEDCOM X conversion
- CLI tooling (`gxcli`, `g7cli`, `validate7`)
- Advanced logging via `loggingkit`
- Graph export utilities

Designed for historical records processing, genealogy research, and archival data pipelines.

---

## Features

- ✅ GEDCOM 5.x parser (`gedcom5`)
- ✅ GEDCOM 7 parser, 18-phase validator, serializer, and high-level models (`gedcom7`)
- ✅ GEDCOM X pydantic object model (`gedcomx`) — complete, 0 type errors
- ✅ GEDCOM X per-property validation (`validate()` on every model)
- ✅ Converter (GEDCOM 5.x → GEDCOM X)
- ✅ CLI tools (`gxcli`, `g7cli`, `validate7`)
- ✅ Structured logging (`loggingkit`) with `GEDCOMTOOLS_DEBUG` env var support
- ✅ Sub-loggers (conversion, parser, io, etc.)
- ✅ Runtime log inspection
- ✅ Extensible schema system
- ✅ Source, person, family, relationship modeling
- ✅ Place and event normalization with multi-language translation support
- ✅ Metadata and attribution handling
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
├── gedcomx/                # GEDCOM X object model and conversion (in progress)
├── graph.py                # Graph export (persons, relationships)
├── loggingkit.py           # Structured logging framework
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
from gedcomtools.gedcomx import GedcomX, GedcomConverter

converter = GedcomConverter()
gx = converter.Gedcom5x_GedcomX(ged)
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

The project uses `loggingkit` for structured logging.

```python
from gedcomtools.loggingkit import setup_logging, LoggerSpec

mgr = setup_logging("gedcomtools")
mgr.get_sublogger(LoggerSpec(name="conversion"))
mgr.get_sublogger(LoggerSpec(name="parser"))
```

Library modules use:

```python
from gedcomtools.loggingkit import get_log

log = get_log("conversion")
log.info("Starting conversion")
```

---

## Design Goals

- Centralized logging control
- Library-safe imports (no logging side effects)
- Extensible schema support
- Accurate GEDCOM X modeling
- Robust error reporting
- CLI + API parity
- Clear separation of concerns

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
