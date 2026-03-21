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
