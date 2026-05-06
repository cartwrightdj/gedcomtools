# UPDATES

Track of changes made to gedcomtools after v0.7.0.

---

## Code quality fixes — raises, dead code, security (2026-04-27)

### Fix — `_gedcom5x.py`: remove dead manual parse block and harden line loop

The `_records_from_file` parse loop contained a manual `str.split` pre-parse
block (lines that set `lvl`, `tag_str`, `value` from a plain split) immediately
before a call to `parse_gedcom7_line()` that unconditionally overwrote all five
variables.  The manual block was dead code in every branch and has been removed.

Additional cleanup in the same loop:

- A `raise ValueError` on lines that failed the regex (resulting in `lvl=None`)
  is replaced with `log.warning(...) + continue` so one malformed line no longer
  aborts the entire file load.
- Loop variable `l` renamed to `line_idx` (avoids visual ambiguity with `1`).
- Redundant `int(lvl)` cast removed (already confirmed `int` by `isinstance`).
- Stale commented-out `print(...)` debug line removed.

| File | Change |
|------|--------|
| `src/gedcomtools/_gedcom5x.py` | Remove dead pre-parse block; log.warning + continue on bad line; rename `l`; remove dead cast and debug print |

### Fix — `conclusion.py`: unknown ConfidenceLevel no longer raises on deserialize

`ConfidenceLevel.from_json()` raised `ValueError` for any unrecognised confidence
string.  Real-world genealogy exports (FamilySearch, Ancestry) occasionally contain
non-standard values; the raise aborted deserialization of the entire record.

The method now logs a `WARNING` and returns `None`, consistent with how other
optional fields handle unrecognised data.  A logger was added to the module.
The matching test was updated from `pytest.raises(ValueError)` to assert `None`.

| File | Change |
|------|--------|
| `src/gedcomtools/gedcomx/conclusion.py` | `ConfidenceLevel.from_json`: raise → log.warning + return None; add get_logger/log |
| `tests/test_confidence.py` | `test_unknown_string_raises` → `test_unknown_string_returns_none` |

### Security fix — `download_url_bytes()` scheme validation

`urllib.request.urlopen` accepts `file://` and `ftp://` URLs.  `download_url_bytes`
relied entirely on callers to validate the scheme via the separate `_is_url()`
helper before calling it.  Any call site that skipped that check could read
arbitrary local files or hit internal FTP servers.

The function now validates the scheme itself before opening any connection,
raising `ValueError` for anything other than `http` or `https`.

| File | Change |
|------|--------|
| `src/gedcomtools/utils/Utilities.py` | `download_url_bytes()`: validate scheme is http/https; raise ValueError otherwise |

### Fix — `identifier.py`: unreachable `elif` in `Identifier.model_post_init`

The inner branch `elif raw is not None:` was unreachable — the outer
`if raw is not None` already guaranteed `raw` was non-None inside the block.
Changed to a plain `else`.

| File | Change |
|------|--------|
| `src/gedcomtools/gedcomx/identifier.py` | `Identifier.model_post_init`: `elif raw is not None` → `else` |

---

## Feature — selective auto-ID for GedcomX conclusions (2026-04-18)

Top-level entities now auto-generate IDs; sub-elements default to `id=None`.

- `Conclusion.id` changed from `str = Field(default_factory=make_uid)` to
  `Optional[str] = None`.  Sub-elements (Name, Gender, Fact, EventRole, etc.)
  no longer receive auto-generated UUIDs unless the caller explicitly sets one.
- `Subject.id` overrides with `default_factory=make_uid`, so Person,
  Relationship, Event, Group, PlaceDescription, and
  ChildAndParentsRelationship still get auto-IDs.
- `Document.id` similarly overrides with `default_factory=make_uid` (Document
  is a top-level GedcomX collection member).
- `AutoIdModel` added to `identifier.py` as a shared base with
  `id: str = Field(default_factory=make_uid)`.  `Agent` and `SourceDescription`
  now inherit from `AutoIdModel` instead of `GedcomXModel` directly, removing
  their individual `id` field declarations.
- `Conclusion.model_post_init` now guards `URI(fragment=…)` construction so it
  is skipped when `id` is `None`, avoiding a pydantic validation error.
- `Conclusion._validate_self` relaxed: only errors if `id` is set to an empty
  string, not if it is `None`.
- `Fact`, `Name`, and `Gender` gained concrete `__eq__` methods that compare
  their type-specific fields (type, date, place, value / nameForms).  Without
  this, `add_fact` / `add_name` duplicate checks collapsed all id-less
  sub-elements of the same base-class fields into false duplicates.

---

## Bug fix — UTF-8 BOM handling in GEDCOM 5 readers (2026-04-17)

- `gedcom.py` — `read_gedcom_version()` was opened with `encoding="utf-8"`,
  causing `ValueError: invalid literal for int() with base 10: '\ufeff0'` on
  any BOM-prefixed GEDCOM file.  Fixed by switching to `encoding="utf-8-sig"`.
- `_gedcom5x.py` — `_records_from_file()` was opened with `encoding="utf-8"`
  and manually stripped the BOM character per-line in the parse loop.  Switched
  to `encoding="utf-8-sig"` so Python handles the BOM automatically; the
  redundant manual strip is removed.

---

## Release refresh — v0.7.5b3 (2026-04-25)

- Added symmetric custom deserialization hooks in `Serialization.deserialize()`
  so project types can provide `_deserializer(data)` or `from_json(data, None)`
  just as serialization already supports `_serializer`.
- Hardened public remote-loading paths with a shared bounded download helper
  that adds timeouts and response-size caps for GEDCOM and GedcomX URL loads.
- Tightened `pyright` and `pylint` configuration to ignore generated build and
  docs output so repo-level checks report maintained-source issues clearly.
- Rebuilt Sphinx docs and refreshed the release artifacts for the `v0.7.5b3`
  beta tag.

---

## Bug fixes — deserialization losses and spouse lookup (2026-04-12)

### Fix — `from_dict()` deserialization losses now captured in `conversion_warnings`

When `GedcomX.from_dict()` skipped an invalid record (because `model_validate`
raised), the failure was only logged as a warning.  Callers had no way to
programmatically detect how many records were silently dropped.

A new `_deser_skipped: Dict[str, int]` counter is initialised in `__init__`
and incremented for every skipped record, keyed by collection name
(``"persons"``, ``"relationships"``, etc.).  `conversion_warnings` is updated
to merge both sources:

* **GEDCOM tag losses** — uppercase tag names from the GEDCOM converter
  (unchanged).
* **Deserialization skips** — lowercase collection names from `from_dict()`.

Callers can now inspect either or both::

    gx = GedcomX.from_dict(data)
    if gx.conversion_warnings:
        print("Data lost during import:", gx.conversion_warnings)
        # e.g. {"persons": 2, "OBJE": 5}

### Fix — `get_spouses()` redundant `.upper()` self-exclusion

`get_spouses()` computed `norm_xref = xref.upper()` and then compared
``ptr_node.payload.upper() != norm_xref`` to exclude the individual from
their own spouse list.  Since `_record_by_xref` now resolves through
`_xref_index` (which stores pre-normalised keys), normalising the string again
was redundant.

The check is replaced with an object-identity comparison
(`candidate is not indi_node`), which is both cheaper and semantically
clearer: the exclusion is about the *object*, not the string form of its id.

| File | Change |
|------|--------|
| `src/gedcomtools/gedcomx/gedcomx.py` | `_deser_skipped` counter; `from_dict()` records per-collection skips; `conversion_warnings` merges both |
| `src/gedcomtools/gedcom7/gedcom7.py` | `get_spouses()`: identity check replaces string `.upper()` comparison |

---

## `change_id` / `change_uri` / `change_name` mutation helpers (2026-04-12)

### New — surgical index-safe property updates on `TypeCollection` and `GedcomX`

Mutating an item's `id`, `uri`, or `names` after it is already in a collection
required either `reindex()` (full three-index scan) or `replace()` (whole-item
swap).  Three new surgical methods update only the affected index entry:

**`TypeCollection.change_id(item, new_id)`**
Swaps the id-index entry, updates `item.id`, and keeps the auto-generated
`_uri.fragment` in sync.  Raises `ValueError` if `new_id` is already used by a
*different* item in the same collection.

**`TypeCollection.change_uri(item, new_uri)`**
Accepts a `URI` object, a plain string (wrapped automatically), or `None` to
clear.  Raises `ValueError` on URI collision with a different item.

**`TypeCollection.change_name(item, old_name, new_name)`**
Replaces the first name entry matching `old_name` and updates the name index.
Names are not collision-checked — multiple items may legitimately share a name.
Raises `ValueError` if `old_name` is not found on the item.

**`GedcomX.change_id / change_uri / change_name`**
Convenience wrappers that locate the right collection automatically via a new
`_find_collection(obj)` helper (searches all eight top-level collections by
object identity) and delegate to the corresponding `TypeCollection` method.

Typical usage::

    p = gx.persons.by_id("P1")
    gx.change_id(p, "P1_CORRECTED")           # id + index + _uri.fragment

    agent = gx.agents.by_name("Old Corp")[0]
    gx.change_name(agent, "Old Corp", "New Corp")

    gx.change_uri(p, "http://example.com/persons/p1")

All six methods carry full docstrings covering: what the method does, the three
accepted URI forms, edge cases (same-id no-op, ``None`` clearing, multi-name
items), what the method does *not* do (cross-reference updates), and runnable
examples.

| File | Change |
|------|--------|
| `src/gedcomtools/gedcomx/gedcomx.py` | `TypeCollection.change_id/uri/name`; `GedcomX._find_collection`, `_collections`, `change_id/uri/name`; enriched docstrings |
| `tests/test_gedcomx.py` | 16 new tests across `TestTypeCollectionChangeId/Uri/Name` and `TestGedcomXChangeMethods` |

---

## TypeCollection index safety (2026-04-12)

### Fix — `append()` rollback leaves zombie index entries

When `_update_indexes()` raised an exception part-way through (e.g. after
writing the id index but before finishing the name index), the existing rollback
only popped the item from `_items` — it did not clean up the partial index
writes.  Subsequent `by_id()` / `by_name()` / `by_uri()` calls would return the
half-indexed item even though it was no longer in the collection.

The rollback now calls `_remove_from_indexes(item)` before re-raising, so all
partial writes are cleaned up atomically.

### Fix — `reindex()` for safe in-place mutation of indexed properties

Mutating an item's `id`, `uri`, or `names` after it has been appended to a
collection silently staled the secondary indexes, causing `by_id()`, `by_uri()`,
and `by_name()` to return wrong results.  There was no safe way to update these
properties without removing and re-adding the whole item.

`reindex(item)` removes all stale index entries for the item using object
identity (scanning `is` rather than reading the current property values, which
are already the post-mutation values), then re-adds the current values.  Safe
update pattern::

    p = gx.persons.by_id("P1")
    p.id = "P1_NEW"
    gx.persons.reindex(p)

### New — `replace(old_item, new_item)` for atomic item swap

Provides a transactional way to swap an item while keeping its list position.
If reindexing the new item fails, the old item's indexes are restored and the
exception is re-raised, leaving the collection unchanged::

    gx.persons.replace(old_person, new_person)

### New — `_rebuild_indexes()` for full recovery

Clears and rebuilds all secondary indexes from `_items` in one O(n) pass.
Useful after bulk out-of-band mutations or as a recovery tool::

    gx.persons._rebuild_indexes()

### Documentation

`TypeCollection` now carries a class-level docstring that explicitly states the
mutation contract and shows all three safe update patterns.

| File | Change |
|------|--------|
| `src/gedcomtools/gedcomx/gedcomx.py` | Rollback fix; `reindex()`; `replace()`; `_rebuild_indexes()`; class docstring |
| `tests/test_gedcomx.py` | 9 new tests covering all four behaviours |

---

## Bug fixes (2026-04-12)

### Fix — `Serialization._coerce_value()` returned `dict` instead of `T`

When generic object instantiation via `T(**kwargs)` raised `TypeError`, the
fallback path logged the error and silently returned the raw `kwargs` dict.
Callers expecting a `T` instance received a `dict`, causing confusing
`AttributeError`s elsewhere.  The fallback now re-raises so the error surfaces
at the actual point of failure.

### Fix — `GedcomXConverter` wrong parent assignment when a parent belongs to multiple families

The single-parent FAM fallback in `_build_relationships()` took the first FAM
any matching parent was found in (`_person_fams[pid][0]`), without checking
whether the other parents also belonged to that FAM.  In blended-family trees
where a parent appears in more than one FAM, children could be silently
assigned to the wrong partnership's family record.

The fallback now scores every candidate FAM by how many of the child's parents
appear in it and picks the highest-scoring match, making the assignment correct
for the common case and best-effort for ambiguous multi-parent structures.

| File | Change |
|------|--------|
| `src/gedcomtools/gedcomx/serialization.py` | `_coerce_value()`: re-raise `TypeError` instead of returning `dict` |
| `src/gedcomtools/gedcom7/gxtog7.py` | Single-parent fallback: score candidates by parent-count match |

---

## Performance optimisations (2026-04-12)

### Opt 1 — Pre-compile GEDCOM 5 line-parse regex

`Gedcom5x.__parse_line()` was assembling five regex fragments into a single
string and calling `re.match()` on every line, causing the pattern to be
compiled on every call.  Three module-level compiled patterns (`_GEDCOM_LINE_RE`,
`_LAST_LINE_RE`, `_CONT_LINE_RE`) now replace the per-call construction.
For a 50 000-line GEDCOM 5 file this eliminates ~50 000 redundant compilations.

### Opt 2 — O(1) xref lookups in `Gedcom7` via `_xref_index`

`_record_by_xref()` previously performed a linear scan of `self.records` with
a `.upper()` call on every element's xref.  A new `_xref_index: Dict[str,
GedcomStructure]` (keyed on uppercase xref) is maintained alongside the
existing `_tag_index` and provides O(1) lookups.  The index is populated
incrementally in `_append_record()` and rebuilt in `_rebuild_tag_index()`, and
is cleared on every `parse_lines()` / `parse_string()` reset.  All relationship
traversal helpers (`get_parents`, `get_children_of`, `get_spouses`) benefit
immediately.

### Opt 3 — `_records_by_tag()` uses `_tag_index`

`_records_by_tag()` was scanning all of `self.records` with `r.tag == tag`
even though `_tag_index` already maps each tag to a list of record positions.
It now reads positions directly from the index, making `individuals()`,
`families()`, `sources()`, etc. O(k) where k is the number of matching records
rather than O(n) over all records.

### Opt 4 — Consolidate payload strip in `parse_gedcom_line()`

`parse_gedcom_line()` called `rstrip("\r\n")` on the raw line and then
`payload.strip()` later.  Changing the initial strip to `rstrip()` (all
trailing whitespace) makes the second strip redundant and removes it.

### Opt 5 — Generator variants for all detail accessors

All `*_details()` methods on `Gedcom7` now delegate to a matching
`*_details_iter()` generator (e.g. `individual_details_iter()`).  Callers that
only need to stream records avoid materialising the full list; existing callers
of `*_details()` are unaffected.

### Opt 6 — O(1) parent-pair lookup in `GedcomXConverter`

The parent-to-family mapping search in `gxtog7._build_relationships()` used
a nested loop over all parent pairs.  The common two-parent case is now a
single `dict.get()` call on the `couple_key_xref` map; the nested loop is
retained only for the rare >2-parent edge case.

| File | Change |
|------|--------|
| `src/gedcomtools/gedcom5/parser.py` | Pre-compile `_GEDCOM_LINE_RE`, `_LAST_LINE_RE`, `_CONT_LINE_RE` at module load |
| `src/gedcomtools/gedcom7/gedcom7.py` | Add `_xref_index`; fix `_records_by_tag` / `_record_by_xref`; consolidate strip; add `*_details_iter()` generators |
| `src/gedcomtools/gedcom7/gxtog7.py` | Replace O(n²) pair search with O(1) direct lookup for common case |

---

## Code quality fixes (2026-04-12)

### Fix — `Gedcom7.from_gedcomx()` uninitialized object state

`from_gedcomx()` was calling `cls.__new__(cls)` to bypass `__init__()`, leaving
`errors`, `_tag_index`, `_rel_cache`, and `filepath` unset on the returned
instance.  Any subsequent call to `validate()`, `__getitem__()`, relationship
helpers, or `write()` would raise `AttributeError`.  Replaced with `cls()` so
all instance attributes are properly initialized before records are populated.
Also added a `GedcomX` type annotation on the `gx` parameter.

### Fix — `download_url_bytes()` backwards `ValueError` re-raise

The `Content-Length` size check caught both `int()` parse failures and the
custom size-limit error in the same `except ValueError` block, then used
`content_length.isdigit()` to decide whether to re-raise — which was inverted.
A non-digit header value would be silently swallowed; the size-limit error
(which always has a digit string) would be correctly re-raised only by
coincidence.  The fix parses the header integer in a dedicated `try/except` and
checks the limit independently, making the two code paths explicit.

### Fix — `gctool_load._load()` broad exception catch

Both `except Exception` blocks in `_load()` were replaced with the specific
exception types each loader can raise: `(GedcomFormatViolationError, OSError,
ValueError)` for GEDCOM 5 and `(GedcomParseError, OSError, ValueError)` for
GEDCOM 7.

### Fix — `Gedcom5.get_shared_note_detail()` redundant suppression

Removed the redundant `# pylint: disable=unused-argument` comment (already
suppressed via `# noqa: ARG002`) and added an underscore prefix to the unused
`xref` parameter for consistency with the adjacent `get_shared_note()` method.

### Test coverage

Added `test_download_url_bytes_ignores_non_numeric_content_length` to
`tests/test_utilities_download.py` to cover the non-digit `Content-Length`
edge case that the previous logic silently mishandled.

| File | Change |
|------|--------|
| `src/gedcomtools/gedcom7/gedcom7.py` | `from_gedcomx()`: `cls.__new__` → `cls()`; `GedcomX` type annotation |
| `src/gedcomtools/utils/Utilities.py` | `download_url_bytes()`: split int-parse and limit-check into separate branches |
| `src/gedcomtools/gctool_load.py` | `_load()`: narrow `except Exception` to specific exception types |
| `src/gedcomtools/gedcom5/gedcom5.py` | `get_shared_note_detail()`: remove redundant suppression; underscore prefix |
| `tests/test_utilities_download.py` | Add non-numeric `Content-Length` test case |

---

## RS 1.0 link-map deserialization for FamilySearch payloads (2026-04-08)

### Fix 17 — make FamilySearch RS `links` accept JSON link maps in inherited GedcomX fields

The FamilySearch RS link support had registered `Conclusion.links` as `_rsLinks`, but
that helper was still a legacy non-pydantic object. As a result, payloads like
FamilySearch `childAndParentsRelationships` could deserialize the typed
`child`, `parent1`, `parent2`, and fact lists, but failed on the inherited
`links` object with a validation error demanding an `_rsLinks` instance.

`rsLink` and `_rsLinks` are now pydantic-compatible extension models. `_rsLinks`
accepts plain JSON maps such as `{"child": {"href": ...}}`, converts each
entry into an `rsLink`, and still exposes backward-compatible accessors like
`.person`, `.portrait`, `.keys()`, and `.get()`.

### Regression coverage

The extension API suite now checks that `_rsLinks.model_validate(...)` accepts
a plain JSON link map, and the FamilySearch relationship tests now verify that
`ChildAndParentsRelationship.model_validate(...)` succeeds with inherited
RS10-style `links` data.

| File | Change |
|------|--------|
| `src/gedcomtools/gedcomx/extensions/fs/fs_types_rs.py` | Convert `RsLink` / `RsLinks` to pydantic-compatible models; accept JSON link maps |
| `tests/extensions/test_extension_api.py` | Added `_rsLinks` JSON-map validation coverage |
| `tests/extensions/test_fs_types.py` | Added `ChildAndParentsRelationship` deserialization coverage with inherited `links` |

---

## FamilySearch RS models moved under `fs` extensions (2026-04-08)

### Fix 18 — move legacy `rs10` FamilySearch models into the `fs` package

The legacy `extensions.rs10` package was housing FamilySearch-specific RS
support types (`rsLink`, `_rsLinks`, `FamilyView`, `DisplayProperties`, and
`FamilyLinks`) even though they are consumed as part of the broader
FamilySearch extension surface. Those models now live in
`gedcomx.extensions.fs.fs_types_rs` with proper class names `RsLink` and
`RsLinks`.

The old `extensions.rs10` package has been removed so FamilySearch extension
code lives in one place. All remaining imports and plugin loading now target
the `fs` package directly.

| File | Change |
|------|--------|
| `src/gedcomtools/gedcomx/extensions/fs/fs_types_rs.py` | New — FamilySearch RS link and display models moved under `fs` |
| `src/gedcomtools/gedcomx/extensions/fs/__init__.py` | Import the new RS support module as part of FS extensions |
| `src/gedcomtools/gedcomx/extensions/__init__.py` | Expose moved FamilySearch RS link types from the new `fs` home |
| `tests/extensions/test_extension_api.py` | Updated to use `fs.fs_types_rs` as the primary import path |
| `tests/extensions/conftest.py` | Stop loading the removed `rs10` plugin package |

---

## FamilySearch docs-name parity for FS extension types (2026-04-08)

### Fix 19 — add exact `FieldInfo` and `RelationshipType` names from the official FS JSON docs

Comparing the current `gedcomx.extensions.fs` package against the official
FamilySearch JSON type list showed that nearly every listed type was already
implemented, but two were only available under internal compatibility names:
`FsFieldInfo` and `FsRelationshipType`.

The FamilySearch extension package now exposes the exact docs names
`FieldInfo` and `RelationshipType` as first-class models/enums, while keeping
the older `FsFieldInfo` and `FsRelationshipType` names as aliases so existing
imports continue to work.

| File | Change |
|------|--------|
| `src/gedcomtools/gedcomx/extensions/fs/fs_types_core.py` | Promote `FieldInfo`; keep `FsFieldInfo` alias |
| `src/gedcomtools/gedcomx/extensions/fs/fs_types_relationship.py` | Promote `RelationshipType`; keep `FsRelationshipType` alias |
| `tests/extensions/test_fs_types.py` | Added coverage for the docs names and alias compatibility |

---

## GedcomX → GEDCOM 7 converter (2026-04-07)

### Feature — `GedcomXConverter`: new reverse conversion path

A new converter completes the format triangle by adding the previously
missing GX → G7 direction.  All three conversion paths now exist:
G5 → G7, G5 → GX, G7 → GX, and now **GX → G7**.

**Converter (`gxtog7.py`) — three phases:**

1. **Xref assignment** — persons → `@I1@`, sources → `@S1@`, repo
   agents → `@R1@`, submitter agents → `@SUBM1@`.
2. **Family reconstruction** — Couple relationships become FAM records;
   ParentChild relationships are grouped by child and matched to an
   existing Couple FAM (by parent-pair lookup), or an implicit FAM is
   created.  Pedigree facts (Adoption, FosterParent, SealingChildToParents)
   are converted back to `FAMC.PEDI` values.
3. **Record building** — canonical G7 order: HEAD → REPO → SUBM →
   SOUR → INDI → FAM → TRLR.

**Coverage:**
- INDI: SEX, NAME (slash notation, GIVN/SURN/NPFX/NSFX, TRAN), all 25
  standard fact/event/attribute tags, FAMS/FAMC with PEDI, notes,
  source citations with PAGE.
- FAM: HUSB/WIFE (assigned by gender), CHIL, all 9 family-event tags,
  notes, source citations.
- SOUR: TITL, AUTH/PUBL/ABBR (recovered from notes encoded by g7togx),
  REPO pointer.
- REPO/SUBM: NAME, ADDR, PHON, EMAIL, WWW.
- DATE: prefers `original` (raw GEDCOM string) over `formal`; converts
  GX formal dates (approximate, before, after, range, ISO) to GEDCOM
  date grammar as fallback.
- Unknown GX fact/event types fall back to `EVEN` with `TYPE`.
- Unconverted constructs are tracked in `conversion_warnings` (same
  pattern as the forward converter).

**Facade methods added:**
- `Gedcom7.from_gedcomx(gx)` — classmethod returning a `Gedcom7` with
  converted records.
- `GedcomX.to_gedcom7()` — instance method mirroring `to_gedcomx()` on
  `Gedcom7`.

| File | Change |
|------|--------|
| `src/gedcomtools/gedcom7/gxtog7.py` | New — `GedcomXConverter` |
| `src/gedcomtools/gedcom7/gedcom7.py` | Added `from_gedcomx()` classmethod |
| `src/gedcomtools/gedcomx/gedcomx.py` | Added `to_gedcom7()` method |
| `tests/test_gxtog7.py` | New — 46 tests covering converter, facade, round-trip |

---

## GEDCOM 5 validator — phases 7-9 and expanded payload checks (2026-04-07)

### Enhancement — nine-phase structural validator for GEDCOM 5.5.1

`Gedcom5Validator` previously had six validation phases.  Three new phases
were added and the existing payload-check phase was extended.

**New phases:**

- **Phase 7 — Xref format**: warns if an xref inner identifier exceeds the
  GEDCOM 5.5.1 maximum of 20 characters (`xref_too_long`); errors if the
  xref contains embedded spaces or `@` characters (`invalid_xref_format`).
- **Phase 8 — Duplicate FAMC links**: warns when the same family is cited
  more than once via `FAMC` on a single individual (`duplicate_famc`).
- **Phase 9 — Self-referential ALIA**: errors when an individual's `ALIA`
  pointer references the individual itself (`self_referential_alia`).

**Extended Phase 1 (file structure):**

- `HEAD.GEDC.VERS` value is now checked; warns if it is not `"5.5"` or
  `"5.5.1"` (`head_gedc_vers_value`).
- `HEAD.CHAR` value is now checked; warns on unrecognised encodings such as
  `LATIN1` (`head_char_unknown`).  Known values: `ANSEL`, `ASCII`, `UTF-8`,
  `UNICODE`, `ANSI`, `IBMPC`, `MACINTOSH`.

**Extended Phase 3 (payload validation):**

- `AGE` values are now validated against the standard age grammar
  (`Ny`, `Nm`, `Nd`, `Nw`, `< Ny Nm Nd`, etc.) — code `invalid_age_format`.
- `STAT` under LDS ordinance parents (`BAPL`, `CONL`, `ENDL`, `SLGC`,
  `SLGS`) is validated against the `LDS_STAT_ORD` enumeration —
  code `invalid_lds_stat_ord`.
- `STAT` under `FAMC` is validated against the `LDS_STAT_CHILD`
  enumeration — code `invalid_lds_stat_child`.

| File | Change |
|------|--------|
| `src/gedcomtools/gedcom5/validator5.py` | Phases 7-9; extended Phase 1 and Phase 3 payload checks |
| `tests/gedcom5/test_gedcom5_validator.py` | New — 45 tests covering all 9 phases |
| `.sample_data/gedcom5/gedcom5_junk.ged` | New — intentionally malformed file exercising every check |

---

## GEDCOM 5 UTF-16 facade/CLI support (2026-04-06)

### Fix 13 — Parse UTF-16 GEDCOM 5 files through the normal loader path

`Gedcom5x.parse()` decoded each binary line as UTF-8, which worked for UTF-8
input but failed on the official UTF-16 GEDCOM 5 sample files.  The parser now
detects a UTF-8/UTF-16 BOM from the raw bytes, decodes the full byte stream
once, and then splits into text lines before feeding `__parse_line()`.  This
fixes the normal `Gedcom5(...)`, `gctool`, and `gedcomtools convert` paths for
UTF-16 GEDCOM 5 input.

### Regression coverage

The GEDCOM 5 official-sample tests now exercise the high-level `Gedcom5`
facade against the UTF-16 LE and BE fixtures instead of skipping them, and the
CLI suite now includes a `g5 -> gx` conversion test using the UTF-16 LE sample.

| File | Change |
|------|--------|
| `src/gedcomtools/gedcom5/parser.py` | BOM-based UTF-8/UTF-16 detection; decode full stream before line splitting |
| `tests/gedcom5/test_gedcom5_official.py` | Expanded `Gedcom5` facade coverage to UTF-16 LE/BE samples |
| `tests/test_cli.py` | Added UTF-16 GEDCOM 5 CLI conversion regression test |

---

## gctool interactive URL sessions use in-memory objects (2026-04-06)

### Fix 14 — `load URL` no longer breaks `info`/`validate`/`list`/`show`/`find`/`tree`/`stats`

`gctool interactive` stored a display-only basename after `load URL` and then
reused the normal file-based command handlers.  Read-only REPL commands like
`info` and `show` would therefore try to reopen a nonexistent local file such
as `family.ged`, even though the remote GEDCOM had already been downloaded and
parsed successfully.

The REPL now renders those read-only commands directly from the in-memory
`Gedcom5`/`Gedcom7` object.  File-based operations (`merge`, `diff`, `export`,
`repair`) remain path-based and now print a clear message when invoked from a
URL-backed session.

### Regression coverage

Added an interactive regression test that simulates `load https://.../family.ged`
followed by `info` and fails if the REPL tries to call `_load()` again.

Follow-up hardening: URL-backed sessions are now tracked explicitly instead of
inferring from `path.exists()`. This prevents `merge`/`diff`/`export`/`repair`
from silently operating on an unrelated same-named local file such as
`family.ged` in the current working directory.

| File | Change |
|------|--------|
| `src/gedcomtools/gctool_interactive.py` | In-memory REPL render helpers for read-only commands; explicit URL-session tracking for path-required operations |
| `tests/test_gctool.py` | Added `load URL` interactive regression tests for `info` and blocked `diff` |

---

## GedcomX polymorphic Group add support (2026-04-06)

### Fix 15 — `GedcomX.add()` now accepts `Group`

`GedcomX` already treated `groups` as a top-level collection for merge,
serialization, deserialization, validation, and ZIP round-trips, but the
generic `GedcomX.add()` dispatcher rejected `Group` objects outright. Added a
dedicated `add_group()` method and wired `Group` into the polymorphic
dispatcher so callers can use the same `gx.add(...)` entry point for groups as
for persons, relationships, agents, events, and other top-level records.

| File | Change |
|------|--------|
| `src/gedcomtools/gedcomx/gedcomx.py` | Added `add_group()` and `Group` support in `GedcomX.add()` |
| `tests/test_gedcomx.py` | Added regression test for `gx.add(Group(...))` |

---

## FamilySearch ChildAndParentsRelationship typing (2026-04-08)

### Fix 16 — make `ChildAndParentsRelationship` a typed Pydantic extension model

The FamilySearch extension model for `ChildAndParentsRelationship` already
existed, but its `parent1Facts` and `parent2Facts` arrays were typed as
`List[Any]`, which weakened validation and made the extension less useful as a
schema-backed Pydantic model.

The model now uses:

- `Resource` for `parent1`, `parent2`, and `child`
- `List[Fact]` for `parent1Facts` and `parent2Facts`
- a small `_validate_self()` method to verify those fields explicitly

This aligns the extension with the rest of the GedcomX model layer and makes
construction, validation, and type-driven serialization more predictable.

| File | Change |
|------|--------|
| `src/gedcomtools/gedcomx/extensions/fs/fs_types_relationship.py` | Typed `ChildAndParentsRelationship` fields as `Resource` / `Fact`; added validation |
| `tests/extensions/test_fs_types.py` | Expanded relationship extension tests for identifier, default fact lists, and typed facts |

---

## Code quality fixes: circular imports, conversion warnings, encoding (2026-04-03d)

### Fix 9 — Remove redundant `model_rebuild()` calls from `gedcomx/__init__.py`

`__init__.py` called `EventRole.model_rebuild()`, `Relationship.model_rebuild()`, and
`Person.model_rebuild()` at the end of its import block as "belt-and-suspenders".  These
were redundant: `event.py` and `relationship.py` each perform their own rebuild (with the
correct `_types_namespace`) at module load time via a deferred import of `person.py`.
Since `person.py` does not import either module, the deferred imports are safe for any
import path.  The three redundant calls are removed and replaced with a comment
documenting where the rebuilds live and why.

| File | Change |
|------|--------|
| `src/gedcomtools/gedcomx/__init__.py` | Removed 3 redundant `model_rebuild()` calls; added explanatory comment |

### Fix 10 — `GedcomX.conversion_warnings` property

Both converters (`GedcomConverter` and `Gedcom7Converter`) already populate
`gx._import_unhandled_tags` — a dict of GEDCOM tags that had no handler during conversion
(i.e. potential data loss).  However, the attribute was private and undocumented, giving
callers no supported way to check whether conversion was clean.

Added a public `conversion_warnings` property to `GedcomX` that returns a copy of that
dict with a docstring explaining the semantics.  Callers can now do:

```python
gx = converter.convert(source)
if gx.conversion_warnings:
    print("Skipped tags:", gx.conversion_warnings)
```

| File | Change |
|------|--------|
| `src/gedcomtools/gedcomx/gedcomx.py` | Added `conversion_warnings` property |

### Fix 12 — `TypeCollection.append()` rollback guard

`_items.append(item)` ran before `_update_indexes(item)` with no cleanup on failure.
If `_update_indexes` raised, the item would be present in `_items` with no index entry,
leaving the collection in an inconsistent state.  A `try/except` now wraps the index
update and pops the item from `_items` before re-raising if anything goes wrong.

| File | Change |
|------|--------|
| `src/gedcomtools/gedcomx/gedcomx.py` | `TypeCollection.append()`: rollback guard on `_update_indexes` |

### Fix 11 — Logged warnings on non-UTF-8 bytes in data reads

`_parse_g5_blocks()` and the G5 merge file read in `gctool_dataops.py` used
`open(..., errors="replace")`, silently substituting U+FFFD for any byte that was not
valid UTF-8.  Users had no indication that their genealogy data was corrupted during a
merge or diff operation.

Both reads are replaced with a binary `read_bytes()` / `decode("utf-8-sig")` pattern.
A `UnicodeDecodeError` falls back to `errors="replace"` **and** emits a `log.warning`
with the file name and count of replaced bytes.

The two sniff-only reads in `cli.py` and `gctool_load.py` retain `errors="replace"` (they
inspect only ASCII VERS/HEAD tags; replacement characters cannot affect the result) but now
carry an explanatory comment.

| File | Change |
|------|--------|
| `src/gedcomtools/gctool_dataops.py` | `_parse_g5_blocks`: binary read + `log.warning` on decode error; G5 merge read: same treatment |
| `src/gedcomtools/cli.py` | Added comment explaining `errors="replace"` is intentional in `_sniff_source_type` |
| `src/gedcomtools/gctool_load.py` | Added comment explaining `errors="replace"` is intentional in `_sniff` |

---

## GedcomFile / GedcomNode protocols (2026-04-03c)

Added `gedcom_protocol.py` with two structural typing protocols.

### `GedcomFile`
Defines the full public API shared by `Gedcom5` and `Gedcom7` — version
detection, validation, raw record accessors, detail model accessors, and
relationship traversal.  Neither class needs to change; structural subtyping
means they satisfy the protocol automatically.

`_load()` and `_load_url()` in `gctool_load.py` now return
`Tuple[str, GedcomFile]` instead of `Tuple[str, Any]`, so pyright/mypy can
flag missing methods on any new format class at analysis time.

### `GedcomNode`
Minimal protocol covering only the `tag: str` attribute — the one field
shared safely by `GedcomStructure` (G7) and `Element` (G5).  Accompanies
a docstring explaining why the extended interfaces differ and how to handle
format-specific behaviour.

| File | Change |
|------|--------|
| `src/gedcomtools/gedcom_protocol.py` | New — `GedcomFile` and `GedcomNode` protocols |
| `src/gedcomtools/gctool_load.py` | Return type `Tuple[str, GedcomFile]` |
| `src/gedcomtools/gctool_commands.py` | Import `GedcomFile` |
| `src/gedcomtools/gctool_dataops.py` | Import `GedcomFile`; type `_alloc_xref_remap` params |

---

## Code quality fixes: xref regex, repair warning, version lookup (2026-04-03b)

### Fix 6 — Xref regex: add `re.IGNORECASE`
`_alloc_xref_remap` used `r"^@([A-Z_]+)(\d+)@$"` without `IGNORECASE`.  Xrefs
are uppercased before matching, but adding the flag makes the intent explicit
and guards against future callers that skip normalisation.

| File | Change |
|------|--------|
| `src/gedcomtools/gctool_dataops.py` | `re.compile(..., re.IGNORECASE)` |

### Fix 7 — Silent data loss in `_repair_walk_g5`
When `el.set_value(new_val)` raised `AttributeError` or `TypeError`, the fix
was silently discarded while its counter had already been incremented — the
repair reported success but made no change.  The bare `pass` is replaced with
a `log.warning` so the user can see which elements could not be repaired.

| File | Change |
|------|--------|
| `src/gedcomtools/gctool_dataops.py` | `except ... pass` → `log.warning(...)` |

### Fix 8 — `NameError` in `_package_version`
`except importlib.metadata.PackageNotFoundError` referenced `importlib.metadata`
which was not in scope after a `from importlib.metadata import version` import —
raising a `NameError` instead of gracefully falling through to the TOML fallback.
Fixed by importing `PackageNotFoundError` explicitly alongside `version`.

| File | Change |
|------|--------|
| `src/gedcomtools/gctool_commands.py` | `from importlib.metadata import version, PackageNotFoundError` |

---

## Code quality fixes: shared URL utils, temp-file safety, narrow excepts (2026-04-03)

### Fix 1 — Deduplicate `_is_url` / `_check_ged_url`
Both helpers were copy-pasted across six files.  Moved to
`utils/Utilities.py` as the single canonical source; all callers now import
from there.  `utils/__init__.py` created to make the package importable.

| File | Change |
|------|--------|
| `src/gedcomtools/utils/Utilities.py` | Added `_is_url`, `_check_ged_url` |
| `src/gedcomtools/utils/__init__.py` | New — package marker |
| `src/gedcomtools/gctool_load.py` | Import from utils; removed local copy |
| `src/gedcomtools/gedcom7/gedcom7.py` | Import from utils; removed local copies |
| `src/gedcomtools/gedcom5/gedcom5.py` | Import from utils; removed local copies |
| `src/gedcomtools/gedcom7/g7cli.py` | Import from utils; removed `Shell._is_url` staticmethod |
| `src/gedcomtools/gedcomx/extensible.py` | Import from utils; removed local copy |
| `src/gedcomtools/gedcomx/gxcli_commands.py` | Import from utils; removed `_LoadMixin._is_url` staticmethod |

### Fix 3 — Temp-file safety in `gctool_load._load_url`
Replaced `mkstemp` + `os.fdopen` with `NamedTemporaryFile(delete=False)`.
The old code could leak the raw file descriptor if `os.fdopen` raised before
taking ownership of `fd`.  The new form is atomic and obviously correct.

| File | Change |
|------|--------|
| `src/gedcomtools/gctool_load.py` | `_load_url`: `mkstemp` → `NamedTemporaryFile(delete=False)` |

### Fix 4 — Narrow bare `except Exception` in `schemas.py`
Three broad `except Exception` clauses replaced with specific types.

| Location | Old | New |
|----------|-----|-----|
| `schemas.py:24` — `Annotated` import guard | `except Exception` | `except ImportError` |
| `schemas.py:292` — `get_type_hints` class fallback | `except Exception` | `except (NameError, AttributeError, TypeError)` |
| `schemas.py:311` — `get_type_hints` init fallback | `except Exception` | `except (NameError, AttributeError, TypeError)` |

---

## RelationshipCacheMixin + gctool.py split (2026-04-01)

### Issue 1 — RelationshipCacheMixin
Extracted the duplicated cache check/store/clear logic from `Gedcom5` and
`Gedcom7` into a shared `RelationshipCacheMixin` in `rel_cache.py`.

Both facade classes now inherit the mixin and use `_cache_get`, `_cache_set`,
and `_cache_clear` instead of direct `_rel_cache` dict access.  Eliminates the
`# type: ignore[return-value]` comments and makes the caching contract explicit.

| File | Change |
|------|--------|
| `src/gedcomtools/rel_cache.py` | New — `RelationshipCacheMixin` |
| `src/gedcomtools/gedcom5/gedcom5.py` | Inherit mixin; use `_cache_*` helpers |
| `src/gedcomtools/gedcom7/gedcom7.py` | Inherit mixin; use `_cache_*` helpers |

### Issue 10 — gctool.py split
`gctool.py` (2,324 lines) split into six focused modules.  `gctool.py` is now a
~120-line thin entry point containing only `main()` and the argparse setup.

| New file | Contents | Lines |
|----------|----------|-------|
| `gctool_output.py` | ANSI colour helpers, `_table`, `_kv`, `_norm_xref` | ~90 |
| `gctool_load.py` | `_sniff`, `_is_url`, `_load_url`, `_load` | ~146 |
| `gctool_commands.py` | `cmd_info/validate/list/show/find/tree/stats/convert/version/spec` | ~598 |
| `gctool_examine.py` | `_Node`, `_FileRoot`, `_run_examine` and helpers | ~455 |
| `gctool_interactive.py` | `cmd_interactive`, `_attribution`, `_print_status` | ~361 |
| `gctool_dataops.py` | `cmd_repair/export/diff/merge` and data helpers | ~608 |

`tests/test_gctool.py` updated to import private helpers from their new home modules.

---

## Sample Data Round-Trip Test Suite (2026-03-31)

### Overview
Added `tests/test_sample_data_roundtrip.py` — a parametrized test module that
exercises the full read → write → read → convert → write → read pipeline for
**every** file in `.sample_data/{gedcom5,gedcom70,gedcomx}`.

### Coverage (294 new tests across 36 files)

| Format | Files | Pipeline |
|--------|-------|---------|
| GEDCOM 5 | 11 `.ged` files | read G5 → to_gedcom7 → write G7 → read G7; G5 → to_gedcomx → JSON → GX |
| GEDCOM 7 | 23 `.ged`/`.gdz` files | read G7 → write G7 → read G7; G7 → to_gedcomx → JSON → GX |
| GedcomX  | 2 `.gedx`/`.gedcomx` files | read GX → JSON → GX → JSON → GX (double round-trip) |

### Notes
* UTF-16 encoded G5 files handled transparently via `io.BytesIO`.
* `.gdz` archives unzipped inline via `zipfile`.
* `gedcom5_all_tags_ascii.ged` → GedcomX conversion is `xfail` (known
  `ConversionErrorDump` on embedded OBJE/FORM tag).
* All record counts (individuals, persons, relationships) are asserted equal
  through every step.

### Files changed

| File | Change |
|------|--------|
| `tests/test_sample_data_roundtrip.py` | New file — 294 tests |

---

## URL Loading Support (2026-03-31)

### Overview
Both `Gedcom5` and `Gedcom7` constructors now accept an HTTP/HTTPS URL in place
of a file path, so callers can load remote GEDCOM files without a separate step.

### Behaviour
* Passing an `http://` or `https://` string to the constructor (or calling
  `load_url()` directly) downloads the file via `urllib.request.urlopen`.
* The URL path **must** end in `.ged`; a `ValueError` is raised otherwise.
* `Gedcom7` decodes the response as UTF-8 (required by the spec) and calls
  `parse_string()`.  `Gedcom5` wraps the raw bytes in `io.BytesIO` and passes
  them directly to the parser's `parse()` method.
* `self.filepath` is set to `None` when loaded from a URL.

### Files changed

| File | Change |
|------|--------|
| `src/gedcomtools/gedcom7/gedcom7.py` | Added `_is_url()`, `_check_ged_url()` module helpers; `__init__` detects URLs; `load_url()` calls `_check_ged_url()`; added `urllib.parse` import |
| `src/gedcomtools/gedcom5/gedcom5.py` | Same module helpers; `__init__` detects URLs; new `load_url()` method; added `io`, `urllib.*` imports |

---

## Relationship Traversal Caching (2026-03-31)

### Overview
`get_parents()`, `get_children_of()`, and `get_spouses()` previously walked the full
element tree on every call (O(n) per query).  For files with thousands of records,
repeated traversal in tree rendering or conversion loops was the main hotspot.

### Fix
Added `_rel_cache: dict[str, list]` to both `Gedcom5` and `Gedcom7`.  Each traversal
method checks the cache before walking the tree and stores its result on first call.
The cache is cleared automatically whenever new data is loaded, so callers that reload
a file (e.g. `loadfile()` / `parse_string()`) always get fresh results.

Cache keys use a short prefix + normalized xref (`p:`, `c:`, `s:`) to avoid collisions
between the three methods for the same individual.

### Files changed

| File | Change |
|------|--------|
| `src/gedcomtools/gedcom5/gedcom5.py` | `__init__`: added `_rel_cache = {}`; `loadfile()`: calls `_rel_cache.clear()`; `get_parents`, `get_children_of`, `get_spouses`: check/populate cache |
| `src/gedcomtools/gedcom7/gedcom7.py` | `__init__`: added `_rel_cache = {}`; `parse_lines()` (called by both `loadfile` and `parse_string`): calls `_rel_cache.clear()`; `get_parents`, `get_children_of`, `get_spouses`: check/populate cache |

---

## Code Quality Refactor (2026-03-31)

### Overview
Structural refactor addressing five code-quality issues identified in a full codebase review:
bare exception handling, a 3 700-line monolithic CLI file, duplicate lookup tables in the
wrong module, absent converter abstraction, and undocumented circular-import workarounds.

### 1 — Bare exception handling

Replaced all `except Exception:` blocks that silently swallowed errors across four files.
Each site now catches only the specific exception types that the underlying call can raise
and logs failures at `DEBUG` level via `loguru` where appropriate.

| File | Change |
|------|--------|
| `src/gedcomtools/gedcom5/g5tog7.py` | Added `get_logger`; 9 bare `except Exception:` → `except (AttributeError, TypeError)` with `log.debug()` |
| `src/gedcomtools/gedcomx/conversion.py` | Uncommented `ConversionErrorDump` re-raise (prevents re-catching dump signals); `str()` fallback narrowed to `(TypeError, AttributeError, RecursionError)` |
| `src/gedcomtools/gctool.py` | Added `get_logger` + `importlib.metadata` import; 20 bare excepts → specific types (`AttributeError`, `KeyError`, `ValueError`, `NotImplementedError`, `PackageNotFoundError`) with `log.debug()` |
| `src/gedcomtools/gedcomx/gxcli.py` | `except Exception:` → `except ImportError:` for colorama guard; JSON helpers narrowed to `orjson.JSONDecodeError`/`ValueError`; display helpers, settings I/O, tab completer, and readline setup all narrowed |

### 2 — Split `gxcli.py` (3 734 LOC → 5 modules)

| New file | Contents |
|----------|----------|
| `gxcli_output.py` | All standalone helpers, constants (`ANSI`, `SHELL_VERSION`), settings I/O, `resolve_path`, `list_fields`, etc. |
| `gxcli_commands.py` | Five `_cmd_*` mixin classes: `_InfoMixin`, `_AhnenMixin`, `_NavMixin`, `_LoadMixin`, `_DataMixin` |
| `gxcli_schema.py` | `_SchemaMixin` — `_cmd_schema`, `_cmd_extras`, `_cmd_type` |
| `gxcli_core.py` | `Shell` class assembled via multiple inheritance + REPL loop |
| `gxcli.py` | Thin entry point — re-exports `Shell`, `main()`, and all public helpers; existing `from gedcomtools.gedcomx.gxcli import Shell, main` imports unchanged |

### 3 — Move EVEN-tag lookup tables out of `schemas.py`

`fact_from_even_tag()` and `event_from_even_tag()` were defined in the schema-registry
module but used only in the converter.  Moved to `conversion.py` alongside their only
call sites; type annotations added.  Backward-compat stubs retained in `schemas.py`.

| File | Change |
|------|--------|
| `src/gedcomtools/gedcomx/conversion.py` | Added `fact_from_even_tag()` and `event_from_even_tag()` as module-level functions; removed `from .schemas import fact_from_even_tag` |
| `src/gedcomtools/gedcomx/schemas.py` | Added comment noting the move; stubs kept for external callers |

### 4 — Converter abstract base class

Both converters previously had no shared interface.  A minimal ABC was added so callers
can type-annotate against `GxConverterBase` regardless of source format.

| File | Change |
|------|--------|
| `src/gedcomtools/gedcomx/converter_base.py` | **New** — `GxConverterBase(ABC)` with single abstract `convert(source) -> GedcomX` method |
| `src/gedcomtools/gedcomx/conversion.py` | `GedcomConverter(GxConverterBase)` + `convert()` alias for `Gedcom5x_GedcomX()` |
| `src/gedcomtools/gedcom7/g7togx.py` | `Gedcom7Converter(GxConverterBase)` (already had `convert()`) |
| `src/gedcomtools/gedcomx/__init__.py` | Exports `GxConverterBase`; adds `G5ToGxConverter = GedcomConverter` preferred alias |

### 5 — Circular import cleanup

The bottom-of-file `from .person import Person` in `event.py` and `relationship.py` was
undocumented and left `Person` in both modules' public namespace unintentionally.

| File | Change |
|------|--------|
| `src/gedcomtools/gedcomx/event.py` | Replaced bare `model_rebuild()` with `model_rebuild(_types_namespace={"Person": _Person_rebuild})`; `del _Person_rebuild` cleans up namespace |
| `src/gedcomtools/gedcomx/relationship.py` | Same treatment |
| `src/gedcomtools/gedcomx/__init__.py` | Added belt-and-suspenders `model_rebuild()` calls at end of `__init__.py` so any import path (direct submodule or via `__init__`) produces a complete model |

Test count: **1 161 passed, 7 xfailed** (unchanged pass rate).

---

## Plugin Security System (2026-03-21)

### Overview
Replaced the unconditional, scan-based `import_plugins()` call in
`gedcomx/__init__.py` with a secure, allowlist-based plugin registry.
Default behaviour is now **nothing loads** — the caller must explicitly
configure trust level and allow each plugin before calling `load()`.

### Files changed

| File | Change |
|------|--------|
| `src/gedcomtools/gedcomx/extensible.py` | Added `TrustLevel`, `PluginStatus`, `PluginEntry`, `PluginBlockedError`, `RegistryLockedError`, `PluginRegistry`, `plugin_registry` singleton, `set_trust_level()`. Updated `import_plugins()` to respect trust level and accept an optional `registry=` parameter. Added `_sha256_of_path()` helper for checksum verification. |
| `src/gedcomtools/gedcomx/__init__.py` | Removed auto-call to `import_plugins()` at import time. Exported new public API: `plugin_registry`, `set_trust_level`, `TrustLevel`, `PluginRegistry`, `PluginEntry`, `PluginStatus`, `PluginBlockedError`, `RegistryLockedError`. |
| `tests/extensions/conftest.py` | Updated session fixture to use `plugin_registry.set_trust_level()` + `plugin_registry.allow()` + `plugin_registry.load()`. |
| `tests/extensions/test_extension_api.py` | Updated `TestImportPlugins` to use local `PluginRegistry` instances (avoids polluting global state). Updated `TestUrlLoading` URL tests to pass `TrustLevel.ALL` via a local registry. |

### New API

```python
from gedcomtools.gedcomx.extensible import plugin_registry, set_trust_level, TrustLevel

# 1. Set coarse trust gate (default: DISABLED — nothing loads)
set_trust_level(TrustLevel.LOCAL)       # builtin + local filesystem
# set_trust_level(TrustLevel.BUILTIN)   # bundled extensions only
# set_trust_level(TrustLevel.ALL)       # + remote URL downloads

# 2. Explicitly allow each plugin
plugin_registry.allow("gedcomtools.gedcomx.extensions.fs")
plugin_registry.allow("./plugins/my_ext.py")
plugin_registry.allow("https://example.com/ext.zip", sha256="abc123…")  # checksum required

# 3. Load — locks the registry (may only be called once)
result = plugin_registry.load()

# Introspection
for entry in plugin_registry.list():
    print(entry.name, entry.status)
```

### Trust levels

| Level | Value | Allows |
|-------|-------|--------|
| `DISABLED` | 0 | Nothing (default) |
| `BUILTIN` | 1 | Bundled `extensions/` subpackage only |
| `LOCAL` | 2 | Builtin + local filesystem paths + env-var local paths |
| `ALL` | 3 | Everything including remote URL downloads |

### Security properties

- **Registry locks after `load()`** — calling `allow()` or `set_trust_level()` after `load()` raises `RegistryLockedError`. No sneaking in new plugins at runtime.
- **URL plugins require SHA-256 checksum** — `allow("https://…")` without `sha256=` raises `ValueError` immediately. The download is rejected if the digest does not match.
- **Trust level is a ceiling** — even explicitly-allowed plugins are blocked if the trust level is below what their source type requires (e.g. a local path is blocked at `BUILTIN` level).
- **`import_plugins()` respects trust level** — the scan-based loader returns empty at `DISABLED`, gates URL sources behind `ALL`, and gates local paths behind `LOCAL`.
- **Test isolation** — `PluginRegistry._reset()` resets global state for tests; `import_plugins(..., registry=reg)` accepts a local registry instance to avoid touching global state.

---

## Code Review Fixes (2026-03-22)

Full static review of the gedcom7 package followed by fixes across seven files.

| File | Fix |
|------|-----|
| `specification.py` | `load_rules()` validates JSON type before clearing `_CORE_RULES` — prevents corrupt module state on bad input |
| `gedcom7.py` | `loadfile()` catches `UnicodeDecodeError` and re-raises as `GedcomParseError` with a clear UTF-8 message |
| `gedcom7.py` | Added `@overload` stubs for `__getitem__` so type checkers infer `g[0]→GedcomStructure`, `g["INDI"]→List[...]` |
| `writer.py` | `write()` is now atomic — serializes to `.tmp` sibling, renames into place, cleans up on failure |
| `writer.py` | `write()` returns the warnings list so callers don't need a separate `get_warnings()` call |
| `writer.py` | `_render_node()` raises `RecursionError` at depth 100, catching circular child references before infinite loop |
| `structure.py` | `add_child()` raises `ValueError` if `child.level != parent.level + 1` — catches incoherent trees early |
| `models.py` | `full_name` falls back to `"Unknown"` when a NAME node exists but has an empty payload |
| `models.py` | `NameDetail` docstring now documents `lang` and `translations` fields |
| `g7interop.py` | `register_tag_uri(overwrite=True)` emits a `UserWarning` when a standard-tag URI is overwritten by another standard tag; extension-tag collisions are silently allowed |
| `validator.py` | Orphaned-record xref regex fallback scoped to known citation tags only — eliminates false positives from free-text `@…@` payloads |
| `tests/test_gedcom7_writer.py` | Added `test_write_returns_warnings`, `test_write_atomic_tmp_cleaned_on_error`, and 25 parametrized `test_official_roundtrip` cases (parse → write → re-parse, assert identical structure) |

Test count: **880 → 905 passing**.

---

## GEDCOM 7 Spec Sync & Updatable Spec (2026-03-22)

### Overview
Two related workstreams completed together:

1. **Spec sync** — compared the module against the live gedcom.io machine-readable YAML
   definitions and the GEDCOM 7 changelog, then fixed all real structural gaps found.
2. **Updatable spec** — the spec rules can now be persisted to / loaded from a JSON file
   (`spec_rules.json`) that ships with the package and can be replaced at runtime.

### Spec fixes (specification.py)

| Area | Change |
|------|--------|
| `PHON / EMAIL / FAX / WWW` cardinality | `(0, 3)` → `(0, None)` — spec permits any number |
| `AGE` under events | Added to `_EVENT_DETAIL_SUBS` / `_EVENT_DETAIL_CARD` so it is permitted under all individual events |
| `ASSO.ROLE` cardinality | `(0, 1)` → `(1, 1)` — ROLE is required under ASSO |
| `NAME` part cardinalities (GIVN/SURN/NPFX/NSFX/SPFX) | `(0, 1)` → `(0, None)` — spec 7.0.9 allows multiples |
| `CHAN` substructures | Added `SNOTE` |
| `HEAD` substructures | Removed `FILE`; added `SNOTE`; fixed `LANG/NOTE/SUBM` cardinality to `(0, 1)` |
| `FILE.FORM` cardinality | `(0, 1)` → `(1, 1)` — FORM is required |
| `SLGC.FAMC` cardinality | `(0, 1)` → `(1, 1)` — FAMC is required |
| `INDI` BIRT/DEAT cardinality | `(0, 1)` → `(0, None)` — multiple birth/death events permitted |
| `SNOTE.LANG` cardinality | `(0, None)` → `(0, 1)` |

### Validator fixes (validator.py)

| Rule | Spec version | Details |
|------|-------------|---------|
| AGE ABNF | 7.0+ | Added support for weeks (`Nw`); now requires at least one time component |
| ADR1/ADR2/ADR3 deprecation warning | 7.0.13 | Warns when deprecated address lines are used |
| EXID without TYPE deprecation warning | 7.0.6 | Warns when EXID has no TYPE child |
| `NO` context validation | 7.0.14 | Warns when `NO XYZ` is used where XYZ is not a permitted sibling |
| Duplicate FAMC/CHIL links | 7.0.14 | Warns on duplicate FAMC per family or CHIL per individual |
| Self-referential ALIA | 7.0.17 | Errors when an individual's ALIA points to itself |
| SOUR→OBJE→SOUR cycle | 7.0.17 | Warns on circular source-object references |

### New tooling

**`check_g7spec.py`** (project root) — standalone script that fetches all 322 GEDCOM 7 term
YAMLs from the FamilySearch/GEDCOM.io GitHub repo, caches them in `.spec_cache/`, and
compares against `_CORE_RULES` and `G7_TAG_TO_URI`, reporting missing URIs, substructure
mismatches, and orphan interop entries.

```
python check_g7spec.py [--cache DIR] [--no-cache] [--verbose]
```

### Updatable spec (Option C)

The structural rules are now serialisable to/from JSON so the bundled spec can be swapped
out at runtime or updated without editing Python source.

#### Files changed

| File | Change |
|------|--------|
| `src/gedcomtools/gedcom7/specification.py` | Added `load_rules()`, `save_rules()`, `reset_rules()`. Loads `spec_rules.json` at import time (falls back silently to inline dict). |
| `src/gedcomtools/gedcom7/spec_rules.json` | New — 140-tag JSON serialisation of the compiled-in rules (~100 KB). Shipped as package data. |
| `src/gedcomtools/gedcom7/spectools.py` | New — `g7spec` CLI (`info`, `export`, `load`, `reset`). |
| `pyproject.toml` | Added `g7spec` entry point; added `package-data` stanza for `spec_rules.json`. |

#### API

```python
from gedcomtools.gedcom7.specification import load_rules, save_rules, reset_rules

load_rules()                        # reload from bundled spec_rules.json
load_rules("/path/to/custom.json")  # load a custom override
save_rules()                        # write active rules back to spec_rules.json
save_rules("/tmp/export.json")      # export to an arbitrary path
reset_rules()                       # restore compiled-in defaults + regenerate JSON
```

#### CLI

```
g7spec info              # show tag list and substructure counts
g7spec export [path]     # dump active rules to JSON (default: spec_rules.json)
g7spec load <path>       # replace bundled spec_rules.json with a custom file
g7spec reset             # restore compiled-in defaults
```

---

## Relationship Cross-Reference Validation Fix (2026-03-29)

### Overview
`GedcomX.validate()` was silently skipping person-reference checks for relationships whose
`person1`/`person2` used the `Resource(resource=URI(fragment="Pn"))` form — the form the
serializer produces during resource-ref deduplication. Only the `resourceId` string form was
checked. Dangling references in the URI-fragment form passed validation without error.

### Root cause

```python
# gedcomx.py — before fix
ref_id = getattr(pfield, "id", None) or getattr(pfield, "resourceId", None)
```

`pfield.id` is the resource object's own identifier (always `None` here, not the target person
id). `pfield.resourceId` covers `Resource(resourceId="P1")` but not
`Resource(resource=URI(fragment="P1"))`. The third branch — `.resource.fragment` — was missing.

### Fix

```python
# gedcomx.py — after fix
ref_id = pfield.resourceId or (pfield.resource.fragment if pfield.resource else None)
```

### Files changed

| File | Change |
|------|--------|
| `src/gedcomtools/gedcomx/gedcomx.py` | Line 526: replaced incorrect `getattr(pfield, "id", …)` fallback with `pfield.resource.fragment` extraction, covering both `resourceId` and `Resource(resource=URI(fragment=…))` forms. |
| `tests/test_gedcomx_validation_rules.py` | Added `TestRelationshipPersonCrossRef` with 4 cases: valid resourceId form, valid resource-fragment form, dangling resourceId (must error), dangling resource-fragment (regression for this bug). |

---

## `from_dict()` Root-Field Loss & `serialize(dict)` Null Leak (2026-03-29)

### Bug #2 — `GedcomX.from_dict()` dropped `attribution` and `groups`

`from_dict()` only passed `id` and `description` to the constructor. `attribution` and `groups`
present in a serialized document were silently ignored, making round-trips lossy without any
error or warning.

**Fix** (`gedcomx.py`): deserialize `attribution` via `Attribution.model_validate()` and append
each `groups` entry via `gx.groups.append()`, using the same guarded pattern as the other
collections.

### Bug #4 — `Serialization.serialize(dict)` leaked `None` placeholders

When serializing a plain `dict`, values were serialized recursively but `None` results were not
filtered. Empty list fields (which `serialize` returns as `None`) produced `"key": null` in the
output instead of being omitted, violating the omit-empty-fields contract.

**Fix** (`serialization.py`): filter `None` values inline during dict comprehension using a
walrus-operator guard, consistent with how `_serialize_dict` already handled this case.

### Files changed

| File | Change |
|------|--------|
| `src/gedcomtools/gedcomx/gedcomx.py` | `from_dict()`: added deserialization of `attribution` and `groups` before the collection loops. |
| `src/gedcomtools/gedcomx/serialization.py` | `serialize(dict)`: replaced unfiltered dict comprehension with one that drops `None` values after recursive serialization. |
| `tests/test_serialization.py` | Added `TestFromDictRootFields` (attribution, groups, id/description round-trips) and `TestSerializeDictNullPruning` (empty list pruned, None pruned, nested None pruned). |

---

## GedcomZip Collision-Safe Naming (2026-03-29)

### Overview
`GedcomZip.add_object_as_resource()` always wrote `GedcomX` objects as `tree.json`,
producing duplicate zip entries (and a `UserWarning`) when more than one was added.
The per-spec entry name is arbitrary; `tree.json` was also non-standard.

### Fix
- Renamed the default entry from `tree.json` to `genealogy.json` (more descriptive,
  consistent with the GedcomX file format spec which has no mandated filename).
- Added `_arcnames: set[str]` on the instance to track all written entry names.
- Added `_unique_arcname(base)` helper: returns `base.json`; on collision returns
  `base2.json`, `base3.json`, … — no silent overwrites.
- Applied the same deduplication to non-GedcomX top-level object entries.
- Updated `read()` to process `genealogy.json` first instead of `tree.json`.

### Files changed

| File | Change |
|------|--------|
| `src/gedcomtools/gedcomx/zip.py` | `__init__`: added `_arcnames` set. Added `_unique_arcname()`. `add_object_as_resource()`: GedcomX path uses `genealogy` base name via `_unique_arcname`; non-GedcomX path also routes through `_unique_arcname`. `read()`: priority entry changed from `tree.json` to `genealogy.json`. |
| `tests/test_zip.py` | Added `test_gedcomx_named_genealogy`; updated `test_multiple_resources` to assert `genealogy.json` / `genealogy2.json` naming and absence of duplicate-name warning. |

---

## TypeCollection URI Fix & Zip Directory Structure (2026-03-29)

### Overview
`TypeCollection.append()` was overwriting every item's `_uri` with a type-path form
(`/persons/#P1`) regardless of whether one was already set. This caused resource references
in serialized output to point at `/persons/#P1` — implying a separate `persons` file in the
zip that doesn't exist — instead of the correct same-document fragment `#P1`.

Additionally, `add_object_as_resource()` was stripping slashes from the URI and flattening
everything to a single directory, so even deliberately path-based URIs lost their structure.

### Fixes

**`gedcomx.py` — `TypeCollection.append()`**
- Only sets `_uri` when the item has none (was: always overwrites)
- Default `_uri` is now `URI(fragment=id)` — no type path — so serialized resource refs
  become `{"resource": "#P1"}` (same-document) not `{"resource": "/persons/#P1"}`
- Explicit path-based URIs set before `append()` are preserved as-is

**`zip.py` — `add_object_as_resource()` and `_unique_arcname()`**
- When `obj._uri` has a path component, the zip entry is placed under that directory:
  `URI(path="/persons/", fragment="P1")` → `persons/P1.json`
- `_unique_arcname()` handles collision suffix correctly for both forms:
  flat: `genealogy2.json`; path-based: `persons/P1_2.json`

### Files changed

| File | Change |
|------|--------|
| `src/gedcomtools/gedcomx/gedcomx.py` | `TypeCollection.append()`: removed type-path stamping; sets `URI(fragment=id)` only when `_uri` is absent. |
| `src/gedcomtools/gedcomx/zip.py` | `add_object_as_resource()`: path-based `_uri` builds directory structure; `_unique_arcname()`: separate collision suffix logic for flat vs path-based names. |
| `tests/test_zip.py` | Added `test_path_uri_builds_directory_structure`: creates a `Person` with explicit `URI(path="/persons/", fragment="P1")`, writes to zip, asserts entry at `persons/P1.json`. |
