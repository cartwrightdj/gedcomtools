# extensible.py
"""
Extensibility framework for GedcomX models.

After the pydantic migration:
- Extensible is now a GedcomXModel subclass (no custom metaclass needed).
- define_ext() is inherited from GedcomXModel.
- import_plugins() is unchanged — it is pure import machinery.

The old SCHEMA registry, ExtrasAwareMeta, and accept_extras() are gone;
their roles are now fulfilled by pydantic's model_fields + extra='allow'.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import importlib
import importlib.util
import os
import pkgutil
import re
import sys

from .gx_base import GedcomXModel


# ---------------------------------------------------------------------------
# Extensible  (kept as a named base for backward compatibility)
# ---------------------------------------------------------------------------

class Extensible(GedcomXModel):
    """Base class for GedcomX entities that support dynamic field extensions.

    Inherits define_ext() / declared_extras() from GedcomXModel.
    Classes that previously used ``class Person(Extensible, Subject)`` should
    now simply use ``class Person(Subject)`` — Subject already inherits from
    GedcomXModel which provides all the same extension capabilities.
    """
    pass


# ---------------------------------------------------------------------------
# import_plugins — unchanged from original
# ---------------------------------------------------------------------------

def import_plugins(
    base_package: str,
    *,
    subpackage: str = "extensions",
    local_dir: str | Path = "./plugins",
    env_var: str = "GEDCOMX_PLUGINS",
    recursive: bool = False,
    root_package: str = "gedcomtools",
) -> dict:
    imported: List[str] = []
    errors: Dict[str, Exception] = {}

    if base_package.startswith(root_package + "."):
        base_fq = base_package
    else:
        base_fq = f"{root_package}.{base_package}"

    subpkg_name = f"gedcomtools.{base_package}.{subpackage}"
    try:
        imported += _import_from_package(subpkg_name, recursive=recursive)
    except ModuleNotFoundError as e:
        if getattr(e, "name", None) == subpkg_name:
            pass
        else:
            errors[subpkg_name] = e
    except Exception as e:
        errors[subpkg_name] = e

    try:
        p = Path(local_dir)
        if not p.is_absolute():
            p = (Path(__file__).resolve().parent / p).resolve()
        imported += _import_from_directory(p, module_prefix=f"{base_fq}.extfs", recursive=recursive)
    except FileNotFoundError:
        pass
    except Exception as e:
        errors[str(local_dir)] = e

    for entry in _split_env(os.getenv(env_var, "")):
        try:
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
    spec.loader.exec_module(module)
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
    spec.loader.exec_module(module)
    return modname


def _import_module(modname: str) -> str:
    importlib.import_module(modname)
    return modname


def _safe_name(s: str) -> str:
    return re.sub(r"[^0-9a-zA-Z_]", "_", s)


def _short_hash(s: str) -> str:
    import hashlib
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:8]


def _split_env(value: str) -> List[str]:
    if not value:
        return []
    parts = []
    for chunk in value.split(os.pathsep):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts.extend([p.strip() for p in chunk.split(",") if p.strip()])
    return parts
