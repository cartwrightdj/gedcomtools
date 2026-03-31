# UPDATES

Track of changes made to gedcomtools after v0.7.0.

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
