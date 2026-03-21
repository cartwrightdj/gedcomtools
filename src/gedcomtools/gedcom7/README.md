# gedcom7

GEDCOM 7 parser, validator, serializer, and interactive CLI for the
**gedcomtools** project.

---

## Contents

| Module | Purpose |
|---|---|
| `gedcom7.py` | Parser, tree builder, and validation entry point (`Gedcom7`) |
| `structure.py` | In-memory tree node (`GedcomStructure`) |
| `validator.py` | Multi-phase structural and semantic validator |
| `writer.py` | Serializer — `GedcomStructure` trees → GEDCOM 7 text |
| `models.py` | High-level dataclasses (`IndividualDetail`, `FamilyDetail`, …) |
| `specification.py` | Tag rules, payload types, cardinality, and enumerations |
| `g7interop.py` | Tag ↔ URI mapping and extension tag registration |
| `exceptions.py` | Exception hierarchy (`GedcomError`, `GedcomParseError`, …) |
| `g7cli.py` | Interactive browser/editor shell (`g7cli`) |
| `validate7.py` | CLI validator entry point (`validate7`) |

---

## Quick start

```python
from gedcomtools.gedcom7 import Gedcom7

# Load and validate
g = Gedcom7("family.ged")
issues = g.validate()
for issue in issues:
    print(f"[{issue.severity}] {issue.code}: {issue.message}")

# Write back out
g.write("family_out.ged")
```

Parse from a string or iterable of lines:

```python
g = Gedcom7()
g.parse_string("0 HEAD\n1 GEDC\n2 VERS 7.0\n0 TRLR")

g2 = Gedcom7()
g2.parse_lines(open("family.ged"))
```

---

## Gedcom7

```python
class Gedcom7(filepath=None)
```

| Method / attribute | Description |
|---|---|
| `loadfile(path)` | Load a GEDCOM file from disk. Raises `GedcomParseError` on I/O failure. |
| `parse_string(text)` | Parse a complete GEDCOM 7 string. Resets all state. |
| `parse_lines(lines)` | Parse from any iterable of lines. Resets all state. |
| `validate()` | Run the full validator. Returns `List[GedcomValidationError]`. Non-GEDCOM-7 files return a single `not_gedcom7` error instead of false positives. |
| `detect_gedcom_version()` | Return the version string from `HEAD.GEDC.VERS`, or `None`. |
| `write(path, *, line_ending, bom)` | Write records to a GEDCOM 7 file via `Gedcom7Writer`. |
| `to_dict()` | Serialize the whole file to a nested dictionary. |
| `records` | `List[GedcomStructure]` — top-level records. |
| `errors` | Parse-time errors accumulated during load. |
| `g["INDI"]` | Return all top-level `INDI` records. |
| `g[0]` | Access records by index. |

---

## GedcomStructure

Single node in the parsed GEDCOM tree.

```python
node.level            # int — GEDCOM line level
node.tag              # str — uppercase tag, e.g. "INDI"
node.xref_id          # Optional[str] — e.g. "@I1@"
node.payload          # str — payload text (CONT lines merged with \n)
node.payload_is_pointer  # bool
node.parent           # Optional[GedcomStructure]
node.children         # List[GedcomStructure]
node.line_num         # Optional[int] — source line number
node.uri              # Optional[str] — resolved gedcom.io URI
node.extension        # bool — True for _UNDERSCORE tags

node.depth            # int — nesting depth (0 for top-level)
node.get_path()       # "/HEAD/GEDC/VERS" style path string
node.get_ancestor(tag)  # first matching ancestor, or None

node.get_children(tag)  # List[GedcomStructure] — direct children
node.first_child(tag)   # Optional[GedcomStructure] — first match
node["NAME"]            # same as get_children("NAME")
node.add_child(child)   # attach an existing node as a child
node.to_dict()          # nested dict (level, tag, payload, children, …)
```

---

## Gedcom7Writer

Stateless serializer. Re-usable across multiple files.

```python
from gedcomtools.gedcom7 import Gedcom7Writer

writer = Gedcom7Writer(line_ending="\n", bom=False)

# Write to file
writer.write(g.records, "output.ged")

# Serialize to string
text = writer.serialize(g.records)

# Check for long-line warnings (> 255 chars)
for w in writer.get_warnings():
    print(w)
```

**Notes:**
- CONT lines are merged into the parent payload as `\n` during parsing.
  The writer splits them back out automatically.
- CONC is never emitted — it was removed in GEDCOM 7.0.
- Future converters (GEDCOM 5 → 7, GEDCOMx → 7) build a
  `List[GedcomStructure]` and pass it directly to this writer.

---

## Validator

`GedcomValidator` runs 18 validation phases on a parsed tree.

```python
from gedcomtools.gedcom7 import GedcomValidator

validator = GedcomValidator(g.records, strict_extensions=True)
issues = validator.validate()   # List[ValidationIssue]

for issue in issues:
    print(f"[{issue.severity}] line {issue.line_num} [{issue.tag}] "
          f"{issue.code}: {issue.message}")
```

### Validation phases

| # | Phase | Error / Warning |
|---|---|---|
| 1 | File structure — HEAD first, TRLR last, GEDC.VERS present | error |
| 2 | Xref format — `@<no-spaces>@` | error |
| 3 | Duplicate xref detection | error |
| 4 | Level stepping — child must be parent + 1 | error |
| 5 | Tag legality — parent → child rules from `specification.py` | error |
| 6 | Cardinality — min/max child counts | error |
| 7 | Payload type — NONE / POINTER / TEXT / ENUM | error |
| 8 | Payload format — DATE (incl. INT), TIME, AGE, LATI, LONG, LANG, RESN | error |
| 9 | Enumeration values — SEX, QUAY, MEDI, PEDI, ROLE, RESN | error |
| 10 | Pointer target resolution — dangling pointer detection | error |
| 11 | `@VOID@` sentinel — allowed only on spec-defined pointer slots | warning |
| 12 | Bidirectional links — `INDI.FAMC` ↔ `FAM.CHIL`, `INDI.FAMS` ↔ `FAM.HUSB/WIFE` | error |
| 13 | Orphaned records — SOUR/REPO/OBJE/SNOTE/SUBM defined but never cited | warning |
| 14 | TRAN context — `TRAN` requires `LANG`; `FILE.TRAN` requires `FORM`; `NAME.TRAN` and `PLAC.TRAN` child restrictions | warning |
| 15 | Extension tag declaration — `HEAD.SCHMA.TAG` (bypassed with `--lenient`) | error |
| 16 | C0 control characters — NUL is an error; other C0 are warnings | error / warning |
| 17 | CONC deprecation — CONC was removed in GEDCOM 7.0 | warning |
| 18 | Line-length estimate — warning if > 255 chars | warning |

`validate()` returns early with a single `not_gedcom7` error if the file
is not GEDCOM 7.x, preventing thousands of false positives on GEDCOM 5
files.

### ValidationIssue fields

| Field | Type | Description |
|---|---|---|
| `code` | `str` | Stable machine-readable code |
| `message` | `str` | Human-readable description |
| `severity` | `str` | `"error"` or `"warning"` |
| `line_num` | `Optional[int]` | Source line number |
| `tag` | `Optional[str]` | Associated GEDCOM tag |

---

## g7interop — tag/URI helpers

```python
from gedcomtools.gedcom7 import (
    get_uri_for_tag,    # "INDI" → "https://gedcom.io/terms/v7/INDI"
    get_tag_for_uri,    # URI → tag
    is_known_tag,       # bool
    is_known_uri,       # bool
    register_tag_uri,   # register an extension tag URI at runtime
)
```

Extension tags declared in `HEAD.SCHMA.TAG` are automatically registered
when the file is parsed.

---

## Exceptions

```python
# preferred — exported from the package
from gedcomtools.gedcom7 import GedcomError, GedcomParseError

# or directly from the module
from gedcomtools.gedcom7.exceptions import GedcomError, GedcomParseError
```

`loadfile()` raises `GedcomParseError` on any `OSError` so callers can
distinguish I/O failures from parse-time issues stored in `g.errors`.
`GedcomError` is the common base class for all gedcom7 library errors.

---

## CLI tools

### `validate7`

```
validate7 [--lenient] <file.ged>
```

Validates a GEDCOM 7 file and prints all issues.

| Exit code | Meaning |
|---|---|
| 0 | Clean (warnings may still be printed) |
| 1 | One or more validation errors |
| 2 | Not a GEDCOM 7 file |
| 3 | File not found or cannot be read |

`--lenient` suppresses errors for undeclared extension tags (skips phase 15).

### `g7cli`

```
g7cli [file.ged]
```

Interactive browser and editor shell.

| Command | Description |
|---|---|
| `load <path>` | Load a GEDCOM 7 file (prompts if unsaved changes exist) |
| `reload` | Re-read the current file from disk, discarding in-memory changes |
| `write <path>` | Write current records to a file |
| `validate` | Run the full validator and print all issues |
| `info` | File summary with record counts per tag |
| `ls` | List children of the current node (or top-level records) |
| `cd <ref>` | Navigate by index, tag name, xref id (`@I1@`), `..`, or `/` |
| `pwd` | Print the current path |
| `show [--all]` | Show fields of the current node; `--all` also runs `ls` |
| `find <tag> [--payload <text>]` | Search the whole tree by tag; filter by payload substring |
| `set payload\|tag\|xref <val>` | Edit a field on the current node |
| `add <tag> [payload]` | Add a child (or top-level record before TRLR) |
| `rm <index>` | Remove a child by index |
| `help` | Show command reference |
| `quit` / `exit` | Exit (prompts if unsaved changes exist) |

A dirty flag tracks unsaved edits. Both `load` and `quit` prompt before
discarding in-memory changes. `reload` skips the prompt and always
re-reads from disk.

---

## High-level Models

`models.py` provides read-only snapshot dataclasses built from parsed
`GedcomStructure` trees. Construct them with the factory functions:

```python
from gedcomtools.gedcom7 import Gedcom7
from gedcomtools.gedcom7.models import (
    individual_detail, family_detail, source_detail,
    repository_detail, media_detail, shared_note_detail, submitter_detail,
)

g = Gedcom7("family.ged")

# Individual
p = individual_detail(g["INDI"][0])
print(p.full_name)        # "Alice Smith" (slashes stripped)
print(p.birth_year)       # 1900
print(p.death_year)       # 1975
print(p.age_at_death)     # 75
print(p.is_living)        # False
print(p.sex)              # "F"
print(p.occupation)       # "Carpenter"

# Name translations (NAME.TRAN)
for tran in p.name.translations:
    print(f"[{tran.lang}] {tran.display}")

# Place translations (PLAC.TRAN)
if p.birth:
    print(p.birth.place)                       # "Springfield"
    print(p.birth.place_translations.get("de")) # "Springfeld"

# Family
f = family_detail(g["FAM"][0])
print(f.husband_xref, f.wife_xref)
print(f.marriage_year, f.num_children)
```

### Detail classes

| Class | Factory | Key fields |
|---|---|---|
| `IndividualDetail` | `individual_detail(node)` | `names`, `sex`, `birth`, `death`, `burial`, `occupation`, `restriction`, `last_changed` |
| `FamilyDetail` | `family_detail(node)` | `husband_xref`, `wife_xref`, `children_xrefs`, `marriage`, `divorce` |
| `SourceDetail` | `source_detail(node)` | `title`, `author`, `publication`, `abbreviation`, `repository_refs` |
| `RepositoryDetail` | `repository_detail(node)` | `name`, `address`, `phone`, `email`, `website` |
| `MediaDetail` | `media_detail(node)` | `files` (list of `(path, form)` tuples), `title` |
| `SharedNoteDetail` | `shared_note_detail(node)` | `text`, `mime`, `language`, `source_citations` |
| `SubmitterDetail` | `submitter_detail(node)` | `name`, `address`, `phone`, `email`, `language` |

### EventDetail properties

| Property | Description |
|---|---|
| `year` | Four-digit year extracted from date string; handles `ABT`, `BEF`, dual-year `1800/01`, `INT` dates |
| `qualifier` | Date qualifier prefix: `ABT`, `BEF`, `AFT`, `CAL`, `EST`, `FROM`, `TO`, `BET`, `INT` |
| `age_years` | Year component extracted from AGE string (`"45y 3m"` → `45`) |
| `place_translations` | `Dict[str, str]` — BCP-47 lang → translated place name from `PLAC.TRAN` nodes |

### NameDetail fields

| Field | Description |
|---|---|
| `full` | Raw NAME payload including GEDCOM surname slashes |
| `display` | Clean name with slashes removed |
| `given`, `surname` | GIVN / SURN substructure values |
| `prefix`, `suffix` | NPFX / NSFX (name prefix / suffix) |
| `nickname` | NICK substructure value |
| `surname_prefix` | SPFX (de, van, von, …) |
| `name_type` | TYPE substructure value |
| `lang` | Language tag (set on translation entries) |
| `translations` | `List[NameDetail]` built from `NAME.TRAN` nodes, each with `lang` set |

### Write-back

Detail objects obtained through `Gedcom7.get_individual()` / `get_family()`
(or by passing `_save_fn`) support in-place editing:

```python
p = g.get_individual("@I1@")
p.occupation = "Blacksmith"
p.save()
g.write("updated.ged")
```

---

## Public API summary

```python
from gedcomtools.gedcom7 import (
    __version__,
    Gedcom7,
    GedcomStructure,
    GedcomValidationError,
    GedcomValidator,
    ValidationIssue,
    Gedcom7Writer,
    get_uri_for_tag,
    get_tag_for_uri,
    is_known_tag,
    is_known_uri,
    register_tag_uri,
    get_label,
    # High-level model detail classes
    IndividualDetail,
    FamilyDetail,
    SourceDetail,
    RepositoryDetail,
    MediaDetail,
    SharedNoteDetail,
    SubmitterDetail,
    EventDetail,
    NameDetail,
    SourceCitation,
    # Factory functions
    individual_detail,
    family_detail,
    source_detail,
    repository_detail,
    media_detail,
    shared_note_detail,
    submitter_detail,
)
```

---

## File structure

```
gedcom7/
├── __init__.py          Public API exports
├── gedcom7.py           Parser + Gedcom7 class
├── structure.py         Tree node (GedcomStructure)
├── specification.py     Tag rules and enumerations
├── validator.py         18-phase validator
├── writer.py            GEDCOM 7 serializer
├── models.py            High-level detail dataclasses + factory functions
├── g7interop.py         Tag/URI mapping
├── exceptions.py        Exception hierarchy
├── g7cli.py             Interactive shell
└── validate7.py         validate7 CLI entry point
```

---

## Conversion roadmap

The intended data-flow for future converters:

```
Gedcom5   ──parse──►  Element tree
                           │
                   gedcom5_to_g7.py  (planned)
                           │
                           ▼
                  List[GedcomStructure]
                           │
                      Gedcom7Writer
                           │
                           ▼
                       output.ged

GedcomX  ──parse──►  GedcomX object graph
                           │
                   gedcomx_to_g7.py  (planned)
                           │
                           ▼
                  List[GedcomStructure]
                           │
                      Gedcom7Writer
```
