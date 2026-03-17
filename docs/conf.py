import os
import re
import sys

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


def setup(app):
    app.connect("autodoc-process-docstring", _strip_file_header)

project   = "gedcomtools"
copyright = "2025, David J. Cartwright"
author    = "David J. Cartwright"
release   = "0.6.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
]

autosummary_generate = False

autodoc_default_options = {
    "members":          True,
    "undoc-members":    False,
    "private-members":  False,
    "show-inheritance": True,
    "member-order":     "bysource",
}

napoleon_google_docstring   = True
napoleon_numpy_docstring    = False
napoleon_include_init_with_doc = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

html_theme = "furo"
html_static_path = ["_static"]
html_title = "gedcomtools"

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

suppress_warnings = ["ref.duplicate"]
