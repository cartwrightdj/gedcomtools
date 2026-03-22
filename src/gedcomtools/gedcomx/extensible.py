# extensible.py
"""
Extensibility framework for GedcomX models.

Security model
--------------
By default **nothing loads**.  To load plugins you must:

1. Set a trust level (coarse gate):

   .. code-block:: python

       from gedcomtools.gedcomx.extensible import set_trust_level, TrustLevel
       set_trust_level(TrustLevel.LOCAL)   # builtin + local filesystem

2. Explicitly allow each plugin (fine-grained allowlist):

   .. code-block:: python

       from gedcomtools.gedcomx.extensible import plugin_registry
       plugin_registry.allow("gedcomtools.gedcomx.extensions.fs")
       plugin_registry.allow("./plugins/my_ext.py")
       plugin_registry.allow("https://example.com/ext.zip", sha256="abc123…")

3. Load:

   .. code-block:: python

       result = plugin_registry.load()

After ``load()`` the registry is **locked** — calling ``allow()`` or
``set_trust_level()`` raises ``RegistryLockedError``.

Trust levels
------------
DISABLED  – nothing loads (default).
BUILTIN   – only extensions bundled with gedcomtools.
LOCAL     – builtin + local filesystem paths.
ALL       – everything including remote URL downloads.

URL plugins always require an explicit ``sha256=`` checksum in ``allow()``;
the download is rejected if the digest does not match.
"""
from __future__ import annotations

import atexit
import hashlib
import shutil
from dataclasses import dataclass
from enum import IntEnum, Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import importlib
import importlib.util
import os
import pkgutil
import re
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile

from .gx_base import GedcomXModel


# ---------------------------------------------------------------------------
# Extensible  (kept as a named base for backward compatibility)
# ---------------------------------------------------------------------------

class Extensible(GedcomXModel):
    """Base class for GedcomX entities that support dynamic field extensions.

    Inherits define_ext() / declared_extras() from GedcomXModel.
    """


# ---------------------------------------------------------------------------
# Security types
# ---------------------------------------------------------------------------

class TrustLevel(IntEnum):
    """Coarse gate controlling which plugin sources may be loaded.

    Levels are ordered: DISABLED < BUILTIN < LOCAL < ALL.
    """
    DISABLED = 0  # nothing loads (default)
    BUILTIN  = 1  # only extensions bundled with gedcomtools
    LOCAL    = 2  # builtin + local filesystem paths
    ALL      = 3  # everything including remote URL downloads


class PluginStatus(str, Enum):
    PENDING = "pending"   # registered but not yet allowed
    ALLOWED = "allowed"   # explicitly allowed, not yet loaded
    LOADED  = "loaded"    # successfully imported
    FAILED  = "failed"    # import attempt failed
    BLOCKED = "blocked"   # blocked by trust level


@dataclass
class PluginEntry:
    name: str
    source: str
    status: PluginStatus = PluginStatus.PENDING
    expected_sha256: Optional[str] = None
    actual_sha256: Optional[str] = None
    error: Optional[Exception] = None


class PluginBlockedError(RuntimeError):
    """Raised when a plugin is blocked by the current trust level."""


class RegistryLockedError(RuntimeError):
    """Raised when the registry is modified after load() has been called."""


# ---------------------------------------------------------------------------
# PluginRegistry
# ---------------------------------------------------------------------------

class PluginRegistry:
    """Secure, allowlist-based plugin registry.

    Usage::

        from gedcomtools.gedcomx.extensible import plugin_registry, TrustLevel

        plugin_registry.set_trust_level(TrustLevel.LOCAL)
        plugin_registry.allow("gedcomtools.gedcomx.extensions.fs")
        plugin_registry.allow("./plugins/my_ext.py")
        plugin_registry.allow("https://example.com/ext.zip", sha256="abc123…")
        result = plugin_registry.load()

    Configuration must happen before ``load()``.  After ``load()`` the registry
    is locked — calling ``allow()`` or ``set_trust_level()`` raises
    ``RegistryLockedError``.
    """

    def __init__(self) -> None:
        self._trust_level: TrustLevel = TrustLevel.DISABLED
        self._entries: Dict[str, PluginEntry] = {}
        self._locked: bool = False

    # ------------------------------------------------------------------
    # Configuration phase
    # ------------------------------------------------------------------

    def set_trust_level(self, level: TrustLevel) -> None:
        """Set the coarse trust gate.  Must be called before ``load()``."""
        if self._locked:
            raise RegistryLockedError("Cannot change trust level after load().")
        self._trust_level = level

    @property
    def trust_level(self) -> TrustLevel:
        return self._trust_level

    @property
    def is_locked(self) -> bool:
        return self._locked

    def allow(
        self,
        source: str,
        *,
        name: Optional[str] = None,
        sha256: Optional[str] = None,
    ) -> None:
        """Explicitly allow a plugin to be loaded.

        Args:
            source:  Module name, local file/directory path, or https:// URL.
            name:    Human-readable label (defaults to *source*).
            sha256:  Required for URL sources — the expected hex SHA-256 digest
                     of the downloaded content.  The load will fail if the
                     digest does not match.

        Raises:
            RegistryLockedError: If called after ``load()``.
            ValueError:          If *source* is a URL and *sha256* is omitted.
        """
        if self._locked:
            raise RegistryLockedError("Cannot allow new plugins after load().")
        if _is_url(source) and sha256 is None:
            raise ValueError(
                f"sha256 checksum is required for URL plugin {source!r}. "
                "Provide sha256=<expected hex digest>."
            )
        key = name or source
        self._entries[key] = PluginEntry(
            name=key,
            source=source,
            status=PluginStatus.ALLOWED,
            expected_sha256=sha256,
        )

    # ------------------------------------------------------------------
    # Load phase
    # ------------------------------------------------------------------

    def load(
        self,
        base_package: str = "gedcomx",
        *,
        recursive: bool = False,
        root_package: str = "gedcomtools",
    ) -> Dict[str, Any]:
        """Import all explicitly-allowed plugins.  May only be called once.

        Returns:
            dict with keys ``"imported"`` (list of module names) and
            ``"errors"`` (dict mapping source → exception).

        Raises:
            RegistryLockedError: If called more than once.
        """
        if self._locked:
            raise RegistryLockedError("load() has already been called.")
        self._locked = True

        imported: List[str] = []
        errors: Dict[str, Exception] = {}

        if base_package.startswith(root_package + "."):
            base_fq = base_package
        else:
            base_fq = f"{root_package}.{base_package}"

        for entry in list(self._entries.values()):
            if entry.status != PluginStatus.ALLOWED:
                continue

            # Trust level gate: URL sources require ALL
            if _is_url(entry.source) and self._trust_level < TrustLevel.ALL:
                entry.status = PluginStatus.BLOCKED
                err = PluginBlockedError(
                    f"{entry.source!r} requires TrustLevel.ALL "
                    f"(current: {self._trust_level.name})."
                )
                entry.error = err
                errors[entry.source] = err
                continue

            # Trust level gate: local paths require LOCAL
            if not _is_url(entry.source) and Path(entry.source).exists():
                if self._trust_level < TrustLevel.LOCAL:
                    entry.status = PluginStatus.BLOCKED
                    err = PluginBlockedError(
                        f"{entry.source!r} requires TrustLevel.LOCAL or higher "
                        f"(current: {self._trust_level.name})."
                    )
                    entry.error = err
                    errors[entry.source] = err
                    continue

            try:
                mods = self._load_entry(entry, base_fq=base_fq, recursive=recursive)
                imported.extend(mods)
                entry.status = PluginStatus.LOADED
            except Exception as exc:
                entry.status = PluginStatus.FAILED
                entry.error = exc
                errors[entry.source] = exc

        return {"imported": imported, "errors": errors}

    def _load_entry(
        self, entry: PluginEntry, *, base_fq: str, recursive: bool
    ) -> List[str]:
        source = entry.source

        if _is_url(source):
            local = _download_to_temp(source)
            actual = _sha256_of_path(local)
            entry.actual_sha256 = actual
            if entry.expected_sha256 is not None and actual != entry.expected_sha256:
                raise ValueError(
                    f"SHA-256 mismatch for {source!r}: "
                    f"expected {entry.expected_sha256!r}, got {actual!r}."
                )
            if local.is_file() and local.suffix == ".py":
                return [_import_file(local, module_prefix=f"{base_fq}.extreg")]
            if local.is_dir():
                return _import_from_directory(
                    local, module_prefix=f"{base_fq}.extreg", recursive=recursive
                )
            return []

        p = Path(source)
        if not p.is_absolute():
            p = (Path(__file__).resolve().parent / p).resolve()
        if p.exists():
            if p.is_file() and p.suffix == ".py":
                return [_import_file(p, module_prefix=f"{base_fq}.extreg")]
            if p.is_dir():
                return _import_from_directory(
                    p, module_prefix=f"{base_fq}.extreg", recursive=recursive
                )
            return []

        # Fall back to treating as a fully-qualified module name
        return [_import_module(source)]

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def list(self) -> List[PluginEntry]:
        """Return a snapshot of all registered plugin entries."""
        return list(self._entries.values())

    # ------------------------------------------------------------------
    # Test support
    # ------------------------------------------------------------------

    def _reset(self) -> None:
        """Reset registry to initial state.  For use in tests only."""
        self._trust_level = TrustLevel.DISABLED
        self._entries.clear()
        self._locked = False


# Module-level singleton and convenience function
plugin_registry = PluginRegistry()


def set_trust_level(level: TrustLevel) -> None:
    """Convenience wrapper: set trust level on the global plugin_registry."""
    plugin_registry.set_trust_level(level)


# ---------------------------------------------------------------------------
# import_plugins — scan-based loader (respects trust level)
# ---------------------------------------------------------------------------

def import_plugins(
    base_package: str,
    *,
    subpackage: str = "extensions",
    local_dir: str | Path = "./plugins",
    env_var: str = "GEDCOMX_PLUGINS",
    recursive: bool = False,
    root_package: str = "gedcomtools",
    registry: Optional[PluginRegistry] = None,
) -> Dict[str, Any]:
    """Scan-based plugin loader gated by trust level.

    Args:
        base_package: Package to load extensions for (e.g. ``"gedcomx"``).
        subpackage:   Built-in subpackage name or URL.
        local_dir:    Local directory path or URL to scan for plugins.
        env_var:      Environment variable listing additional plugin paths/URLs.
        recursive:    Whether to recurse into sub-packages.
        root_package: Root package prefix.
        registry:     Registry whose trust level to consult.  Defaults to the
                      global ``plugin_registry``.  Pass a fresh
                      ``PluginRegistry()`` in tests to avoid global state.

    Returns:
        ``{"imported": [...], "errors": {...}}``

    Trust level behaviour:
        DISABLED → returns empty immediately.
        BUILTIN  → loads bundled subpackage only.
        LOCAL    → loads subpackage + local_dir + env-var local paths.
        ALL      → loads everything including URL sources.
    """
    reg = registry if registry is not None else plugin_registry
    level = reg.trust_level

    if level == TrustLevel.DISABLED:
        return {"imported": [], "errors": {}}

    imported: List[str] = []
    errors: Dict[str, Exception] = {}

    if base_package.startswith(root_package + "."):
        base_fq = base_package
    else:
        base_fq = f"{root_package}.{base_package}"

    # --- built-in subpackage (BUILTIN+) ---
    if _is_url(subpackage):
        if level < TrustLevel.ALL:
            errors[subpackage] = PluginBlockedError(
                f"URL subpackage {subpackage!r} requires TrustLevel.ALL "
                f"(current: {level.name})."
            )
        else:
            try:
                local_sub = _download_to_temp(subpackage)
                if local_sub.is_file() and local_sub.suffix == ".py":
                    imported.append(_import_file(local_sub, module_prefix=f"{base_fq}.extsub"))
                elif local_sub.is_dir():
                    imported += _import_from_directory(local_sub, module_prefix=f"{base_fq}.extsub", recursive=recursive)
            except Exception as e:
                errors[subpackage] = e
    else:
        subpkg_name = f"gedcomtools.{base_package}.{subpackage}"
        try:
            imported += _import_from_package(subpkg_name, recursive=recursive)
        except ModuleNotFoundError as e:
            if getattr(e, "name", None) != subpkg_name:
                errors[subpkg_name] = e
        except Exception as e:
            errors[subpkg_name] = e

    # --- local_dir (LOCAL+) ---
    if level >= TrustLevel.LOCAL:
        try:
            if _is_url(str(local_dir)):
                if level < TrustLevel.ALL:
                    errors[str(local_dir)] = PluginBlockedError(
                        f"URL local_dir {str(local_dir)!r} requires TrustLevel.ALL "
                        f"(current: {level.name})."
                    )
                else:
                    p = _download_to_temp(str(local_dir))
                    if p.is_file() and p.suffix == ".py":
                        imported.append(_import_file(p, module_prefix=f"{base_fq}.extfs"))
                    else:
                        imported += _import_from_directory(p, module_prefix=f"{base_fq}.extfs", recursive=recursive)
            else:
                p = Path(local_dir)
                if not p.is_absolute():
                    p = (Path(__file__).resolve().parent / p).resolve()
                if p.is_file() and p.suffix == ".py":
                    imported.append(_import_file(p, module_prefix=f"{base_fq}.extfs"))
                else:
                    imported += _import_from_directory(p, module_prefix=f"{base_fq}.extfs", recursive=recursive)
        except FileNotFoundError:
            pass
        except Exception as e:
            errors[str(local_dir)] = e

    # --- env-var entries (LOCAL+ for paths, ALL for URLs) ---
    if level >= TrustLevel.LOCAL:
        for entry in _split_env(os.getenv(env_var, "")):
            try:
                if _is_url(entry):
                    if level < TrustLevel.ALL:
                        errors[entry] = PluginBlockedError(
                            f"URL env entry {entry!r} requires TrustLevel.ALL "
                            f"(current: {level.name})."
                        )
                    else:
                        p = _download_to_temp(entry)
                        if p.is_file() and p.suffix == ".py":
                            imported.append(_import_file(p, module_prefix=f"{base_fq}.extenv"))
                        elif p.is_dir():
                            imported += _import_from_directory(p, module_prefix=f"{base_fq}.extenv", recursive=recursive)
                else:
                    p = Path(entry)
                    if p.exists():
                        if p.is_file() and p.suffix == ".py":
                            imported.append(_import_file(p, module_prefix=f"{base_fq}.extenv"))
                        elif p.is_dir():
                            imported += _import_from_directory(p, module_prefix=f"{base_fq}.extenv", recursive=recursive)
                    else:
                        imported.append(_import_module(entry))
            except Exception as e:
                errors[entry] = e

    return {"imported": imported, "errors": errors}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")


_DOWNLOAD_TIMEOUT = 30  # seconds

# Tracks temp directories created by _download_to_temp for atexit cleanup.
_plugin_tmp_dirs: List[Path] = []


def _cleanup_plugin_tmp_dirs() -> None:
    """Remove all plugin temp directories created during this process."""
    for d in _plugin_tmp_dirs:
        try:
            shutil.rmtree(d, ignore_errors=True)
        except Exception:
            pass
    _plugin_tmp_dirs.clear()


atexit.register(_cleanup_plugin_tmp_dirs)


def _download_to_temp(url: str) -> Path:
    """Download *url* into a fresh temp directory and return the local path.

    * A ``.py`` URL → returns the downloaded ``.py`` file path.
    * A ``.zip`` URL → extracts into a sub-directory and returns that directory.
    * Any other URL → treated as a raw file download (returned as-is).

    The temp directory is *not* deleted automatically; it persists for the
    lifetime of the process so that imported modules can reference their
    source files.

    Raises ``urllib.error.URLError`` if the download exceeds ``_DOWNLOAD_TIMEOUT``
    seconds or the host is unreachable.
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="gedcomx_plugins_"))
    _plugin_tmp_dirs.append(tmp_dir)
    filename = Path(urllib.parse.urlparse(url).path).name or "plugin_download"
    dest = tmp_dir / filename

    with urllib.request.urlopen(url, timeout=_DOWNLOAD_TIMEOUT) as resp:
        dest.write_bytes(resp.read())

    if dest.suffix == ".zip":
        extract_dir = tmp_dir / dest.stem
        extract_dir.mkdir(exist_ok=True)
        resolved_extract = extract_dir.resolve()
        with zipfile.ZipFile(dest, "r") as zf:
            for member in zf.infolist():
                member_path = (extract_dir / member.filename).resolve()
                try:
                    member_path.relative_to(resolved_extract)
                except ValueError as exc:
                    raise ValueError(
                        f"Zip slip detected in plugin archive: {member.filename!r}"
                    ) from exc
                zf.extract(member, extract_dir)
        dest.unlink()
        return extract_dir
    return dest


def _sha256_of_path(p: Path) -> str:
    """Compute hex SHA-256 of a file, or of a directory's contents (sorted)."""
    h = hashlib.sha256()
    if p.is_file():
        h.update(p.read_bytes())
    else:
        for child in sorted(p.rglob("*")):
            if child.is_file():
                h.update(child.read_bytes())
    return h.hexdigest()


def _import_from_package(pkg_name: str, *, recursive: bool) -> List[str]:
    mods: List[str] = []
    pkg = importlib.import_module(pkg_name)
    if not hasattr(pkg, "__path__"):
        return mods
    walker = pkgutil.walk_packages if recursive else pkgutil.iter_modules
    for mi in walker(pkg.__path__, pkg.__name__ + "."):
        tail = mi.name.rsplit(".", 1)[-1]
        if tail.startswith("_"):
            continue
        importlib.import_module(mi.name)
        mods.append(mi.name)
    return mods


def _import_package_dir(pkg_dir: Path, modname: str, *, recursive: bool) -> str:
    init_py = pkg_dir / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        modname, init_py, submodule_search_locations=[str(pkg_dir)]
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create spec for package {pkg_dir}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[modname] = module
    module.__file__ = str(init_py)
    module.__package__ = modname
    module.__path__ = [str(pkg_dir)]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    if recursive:
        for child in sorted(pkg_dir.iterdir()):
            if child.name.startswith("_"):
                continue
            if child.is_dir() and (child / "__init__.py").exists():
                _import_package_dir(child, f"{modname}.{_safe_name(child.name)}", recursive=True)
            elif child.suffix == ".py" and child.name != "__init__.py":
                _import_file(child, module_prefix=modname)
    return modname


def _import_from_directory(dirpath: str | Path, *, module_prefix: str, recursive: bool) -> List[str]:
    root = Path(dirpath)
    if not root.exists():
        raise FileNotFoundError(root)
    imported: List[str] = []
    for pkg_dir in sorted([p for p in root.iterdir() if p.is_dir() and (p / "__init__.py").exists()]):
        if pkg_dir.name.startswith("_"):
            continue
        modname = f"{module_prefix}.{_safe_name(pkg_dir.name)}"
        imported.append(_import_package_dir(pkg_dir, modname, recursive=recursive))
    for py in sorted(root.glob("*.py")):
        if py.name in ("__init__.py",) or py.stem.startswith("_"):
            continue
        imported.append(_import_file(py, module_prefix))
    return imported


def _import_file(py_file: Path, module_prefix: str) -> str:
    name = _safe_name(py_file.stem)
    ident = _short_hash(str(py_file.resolve()))
    modname = f"{module_prefix}.{name}_{ident}"
    spec = importlib.util.spec_from_file_location(modname, py_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create spec for file {py_file}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[modname] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return modname


def _import_module(modname: str) -> str:
    importlib.import_module(modname)
    return modname


def _safe_name(s: str) -> str:
    return re.sub(r"[^0-9a-zA-Z_]", "_", s)


def _short_hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:8]


def _split_env(value: str) -> List[str]:
    """Split a plugin env-var string into individual entries.

    Entries may be separated by commas or ``os.pathsep`` (``:`` on POSIX,
    ``;`` on Windows).  URLs (``http://…`` / ``https://…``) are matched as
    whole tokens so their embedded colons and ports are never split.
    """
    if not value:
        return []
    non_url_sep = re.escape("," + os.pathsep)
    pattern = re.compile(
        rf"https?://[^\s,]+"        # full URL — stop only at space or comma
        rf"|[^{non_url_sep}\s]+"    # regular path / module name
    )
    return [m.group() for m in pattern.finditer(value)]
