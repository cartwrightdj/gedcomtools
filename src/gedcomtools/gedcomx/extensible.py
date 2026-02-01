# extensible.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import importlib
import importlib.util
import os
import pkgutil
import re
import sys
"""
======================================================================
 Project: Gedcom-X
 File:    extensible.py
 Author:  David J. Cartwright
 Purpose: provide extensibility functionality

 Created: 2025-09-12
 Updated:
   
   
======================================================================
"""

"""
======================================================================
GEDCOM Module Types
======================================================================
"""
from .schemas import SCHEMA, schema_class, ExtrasAwareMeta



@schema_class()
class Extensible(metaclass=ExtrasAwareMeta):
    # class-level registry of declared extras
    _declared_extras: Dict[str, Any] = {}

    def __init_subclass__(cls, **kw):
        super().__init_subclass__(**kw)
        # each subclass gets its own dict (copy, not shared)
        cls._declared_extras = dict(getattr(cls, "_declared_extras", {}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # cooperative
        self.extras: Dict[str, Any] = {}
        # seed declared defaults
        for k, default in type(self)._declared_extras.items():
            self.extras[k] = _copy_default(default)

    @classmethod
    def define_ext(
        cls,
        name: str,
        *,
        typ: type | None = None,
        default: Any = None,
        overwrite: bool = False,
    ) -> None:
        """
        Declare an extra field on the CLASS.

        Args:
            name: field name
            typ: Python type (used to update schema registry)
            default: default value for new instances
            overwrite: if True, replaces existing definition
        """
        if name in getattr(cls, "__dataclass_fields__", {}):
            raise AttributeError(f"{name!r} already exists on {cls.__name__}")

        already = hasattr(cls, name)
        if already and not overwrite:
            return

        # Attach descriptor
        setattr(cls, name, _ExtraField(name, default))
        cls._declared_extras[name] = default

        # Register with schema
        if typ is None and default is not None:
            typ = type(default)
        SCHEMA.register_extra(cls, name, typ or type(None))

    @classmethod
    def declared_extras(cls) -> Dict[str, Any]:
        return dict(getattr(cls, "_declared_extras", {}))

class _ExtraField:
    def __init__(self, name: str, default: Any):
        self.name = name
        self.default = default
    def __get__(self, obj, owner):
        if obj is None:
            return self
        return obj.extras.get(self.name, self.default)
    def __set__(self, obj, value):
        obj.extras[self.name] = value

def _copy_default(v: Any) -> Any:
    if isinstance(v, (list, dict, set)):
        return v.copy()
    return v
    # avoid shared mutable defaults
    if isinstance(v, (list, dict, set)):
        return v.copy()
    return v

def import_plugins(
    base_package: str,                    # e.g., "gedcomx"  (or "gedcomtools.gedcomx")
    *,
    subpackage: str = "extensions",
    local_dir: str | Path = "./plugins",
    env_var: str = "GEDCOMX_PLUGINS",
    recursive: bool = False,
    root_package: str = "gedcomtools",    # NEW
) -> dict:
    imported: List[str] = []
    errors: Dict[str, Exception] = {}

    # Normalize base_package to a fully qualified package
    # Accept either "gedcomx" or "gedcomtools.gedcomx"
    if base_package.startswith(root_package + "."):
        base_fq = base_package
        base_short = base_package[len(root_package) + 1 :]
    else:
        base_fq = f"{root_package}.{base_package}"
        base_short = base_package

    # 1) Subpackage: <base_fq>.<subpackage>
    subpkg_name = f"gedcomtools.{base_package}.{subpackage}"
    try:
        imported += _import_from_package(subpkg_name, recursive=recursive)
    except ModuleNotFoundError as e:
        # Only ignore if the missing thing IS the subpackage itself
        if getattr(e, "name", None) == subpkg_name:
            pass
        else:
            errors[subpkg_name] = e
    except Exception as e:
        errors[subpkg_name] = e

    # 2) Local directory (resolve relative to *this file* if relative)
    try:
        p = Path(local_dir)
        if not p.is_absolute():
            p = (Path(__file__).resolve().parent / p).resolve()
        imported += _import_from_directory(
            p,
            module_prefix=f"{base_fq}.extfs",   # FIXED prefix
            recursive=recursive,
        )
    except FileNotFoundError:
        pass
    except Exception as e:
        errors[str(local_dir)] = e

    # 3) Env var entries
    for entry in _split_env(os.getenv(env_var, "")):
        try:
            p = Path(entry)
            if p.exists():
                if p.is_file() and p.suffix == ".py":
                    imported.append(_import_file(p, module_prefix=f"{base_fq}.extenv"))
                elif p.is_dir():
                    imported += _import_from_directory(p, module_prefix=f"{base_fq}.extenv", recursive=recursive)
                else:
                    continue
            else:
                imported.append(_import_module(entry))
        except Exception as e:
            errors[entry] = e

    return {"imported": imported, "errors": errors}

# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _import_from_package(pkg_name: str, *, recursive: bool) -> List[str]:
    mods: List[str] = []
    pkg = importlib.import_module(pkg_name)
    if not hasattr(pkg, "__path__"):
        return mods

    walker = pkgutil.walk_packages if recursive else pkgutil.iter_modules
    for mi in walker(pkg.__path__, pkg.__name__ + "."):
        modname = mi.name
        tail = modname.rsplit(".", 1)[-1]
        if tail.startswith("_"):
            continue
        importlib.import_module(modname)
        mods.append(modname)

    return mods

def _import_package_dir(pkg_dir: Path, modname: str, *, recursive: bool) -> str:
    init_py = pkg_dir / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        modname, init_py, submodule_search_locations=[str(pkg_dir)]
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create spec for package {pkg_dir}")

    module = importlib.util.module_from_spec(spec)

    # IMPORTANT: register before exec for relative imports / recursion
    sys.modules[modname] = module

    # Ensure package attrs for child imports
    module.__file__ = str(init_py)
    module.__package__ = modname
    module.__path__ = [str(pkg_dir)]  # type: ignore[attr-defined]

    spec.loader.exec_module(module)  # type: ignore[arg-type]

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
    """
    Import top-level .py files and packages under a filesystem directory.
    - Uses stable, unique module names under `module_prefix`.
    - For packages (dir with __init__.py), import that package; optionally recurse.
    """
    root = Path(dirpath)
    if not root.exists():
        raise FileNotFoundError(root)

    imported: List[str] = []

    # First: import packages (directories with __init__.py)
    for pkg_dir in sorted([p for p in root.iterdir() if p.is_dir() and (p / "__init__.py").exists()]):
        if pkg_dir.name.startswith("_"):
            continue
        modname = f"{module_prefix}.{_safe_name(pkg_dir.name)}"
        imported.append(_import_package_dir(pkg_dir, modname, recursive=recursive))

    # Then: import top-level .py modules
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

    # IMPORTANT: register before exec
    sys.modules[modname] = module

    spec.loader.exec_module(module)  # type: ignore[arg-type]
    return modname

def _import_module(modname: str) -> str:
    importlib.import_module(modname)
    return modname

def _safe_name(s: str) -> str:
    return re.sub(r"[^0-9a-zA-Z_]", "_", s)

def _short_hash(s: str) -> str:
    # short, stable, no external deps
    import hashlib
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:8]

def _split_env(value: str) -> List[str]:
    if not value:
        return []
    parts = []
    # primary split by os.pathsep (';' on Windows, ':' on Unix)
    for chunk in value.split(os.pathsep):
        chunk = chunk.strip()
        if not chunk:
            continue
        # allow comma as alternative delimiter inside each chunk
        parts.extend([p.strip() for p in chunk.split(",") if p.strip()])
    return parts



