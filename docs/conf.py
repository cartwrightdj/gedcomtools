import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath("../src"))


def _strip_file_header(app, what, name, obj, options, lines):
    """Strip ====== file-header banners from module docstrings."""
    if what != "module":
        return
    clean = []
    in_banner = False
    for line in lines:
        if re.match(r"^={60,}\s*$", line):
            in_banner = not in_banner
            continue
        if in_banner:
            continue
        clean.append(line)
    lines[:] = clean


_SKIP_IMPORTED_HELPERS = {
    "BaseModel",
    "ConfigDict",
    "Field",
    "PrivateAttr",
    "computed_field",
    "field_validator",
    "model_validator",
    "validator",
}


def _skip_imported_helpers(_app, _what, name, obj, skip, _options):
    """Skip imported Pydantic helper symbols that are not part of the public API docs."""
    if name in _SKIP_IMPORTED_HELPERS:
        return True
    return skip


def setup(app):
    app.connect("autodoc-process-docstring", _strip_file_header)
    app.connect("autodoc-skip-member", _skip_imported_helpers)

project   = "gedcomtools"
copyright = "2025, David J. Cartwright"
author    = "David J. Cartwright"
release   = "0.6.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
    "myst_parser",
]

autosummary_generate = False

autodoc_default_options = {
    "members":          True,
    "undoc-members":    False,
    "private-members":  False,
    "show-inheritance": True,
    "member-order":     "bysource",
    "exclude-members":  ",".join(sorted(_SKIP_IMPORTED_HELPERS)),
}

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

html_theme = "furo"
html_static_path = ["_static"] if Path(__file__).with_name("_static").exists() else []
html_title = "gedcomtools"

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

suppress_warnings = [
    "ref.duplicate",
    "sphinx_autodoc_typehints.forward_reference",
    "sphinx_autodoc_typehints.guarded_import",
]
