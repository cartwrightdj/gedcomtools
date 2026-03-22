# UPDATES

Track of changes made to gedcomtools after v0.7.0.

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
