# gedcomtools

A comprehensive Python toolkit for converting, processing, and analyzing genealogical data using the **GEDCOM X**, and **GEDCOM 5.x** data models.

`gedcomtools` provides:
- GEDCOM 5.x → GEDCOM X conversion
- Structured object models for GEDCOM X
- CLI tooling (`gxcli`) for batch processing
- Advanced logging via `loggingkit`
- Utilities for parsing, normalization, and validation

Designed for historical records processing, genealogy research, and archival data pipelines.

---

## Features

- ✅ GEDCOM 5.x parser
- ✅ GEDCOM X object model
- ✅ Converter (GEDCOM 5.x → GEDCOM X)
- ✅ CLI tool (`gxcli`)
- ✅ Structured logging (`loggingkit`)
- ✅ Sub-loggers (conversion, parser, io, etc.)
- ✅ Runtime log inspection
- ✅ Extensible schema system
- ✅ Source, person, family, relationship modeling
- ✅ Place and event normalization
- ✅ Metadata and attribution handling

---

## Project Structure

```
gedcomtools/
├── gxcli/                  # CLI application
├── loggingkit.py           # Structured logging framework
├── converter.py            # GEDCOM → GEDCOM X converter
├── gedcom/                 # GEDCOM 5.x parsing layer
├── schemas/                # Schema & extensibility system
├── person.py
├── family.py
├── relationship.py
├── source_description.py
├── place_description.py
└── ...
```

---

## Installation

```bash
pip install gedcomtools
```

Or from source:

```bash
git clone https://github.com/yourrepo/gedcomtools.git
cd gedcomtools
pip install -e .
```

---

## CLI Usage (`gxcli`)

Initialize logging and run a conversion:

```bash
gxcli convert input.ged output.json
```

Enable debug logging:

```bash
gxcli log conversion DEBUG
gxcli convert input.ged output.json
```

Show configured loggers:

```bash
gxcli log
```

---

## Programmatic Usage

### Convert GEDCOM 5.x → GEDCOM X

```python
from gedcomtools.converter import GedcomConverter
from gedcomtools.gedcom.gedcom5x import Gedcom5x

ged = Gedcom5x("family.ged")
converter = GedcomConverter()

gx = converter.Gedcom5x_GedcomX(ged)
```

---

## Logging

The project uses `loggingkit` for structured logging.

CLI initializes logging:

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

Show configured logs:

```python
print(mgr.dump_loggers())
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

## Extensibility

You can add support for custom GEDCOM tags via schema plugins:

```python
@schema_property_plugin(name="custom_field")
def custom_field(self) -> str:
    return self.data.get("CUSTOM")
```

---

## Error Handling

All conversion errors provide:
- Tag context
- Object stack dump
- Structured log output

Example:

```python
ConversionErrorDump
```

---

## Roadmap

- [ ] GEDCOM 7 support
- [ ] JSON-LD export
- [ ] Validation rules
- [ ] Graph database export (ArangoDB)
- [ ] RAG pipeline integration
- [ ] Performance optimizations
- [ ] Full test suite

---

## License

MIT License

---

## Author

David J. Cartwright

---

## Philosophy

> Build genealogy tooling like infrastructure: structured, observable, extensible.

---

If you're using `gedcomtools` in research or production, please report issues and contribute improvements.
