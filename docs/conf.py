# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
sys.path.insert(0, os.path.abspath('..'))  # Point to your project root

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'gedcom-x'
copyright = '2025, David J. Cartwright'
author = 'David J. Cartwright'
release = '0.6.2'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",  # For Google/NumPy style docstrings
]
extensions += ["sphinx_togglebutton"]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
#html_static_path = ['_static']

# 1) Hide module prefixes in object names/signatures (headings, autosummaries, etc.)
add_module_names = False

# 2) Shorten how type hints are rendered (pick the one that matches your setup):

# If you're on Sphinx ≥ 7.1 (built-in handling):
autodoc_typehints = "description"      # or "both"/"signature" as you prefer
autodoc_typehints_format = "short"     # show short names instead of fully qualified

# If you use the sphinx-autodoc-typehints extension:
#extensions += ["sphinx_autodoc_typehints"]
typehints_fully_qualified = False      # shorten names like 'pathlib.Path' → 'Path'
# (optional)
simplify_optional_unions = True

# Don’t list inherited members on subclasses (recommended default)
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
    "inherited-members": False,   # <- key: avoid duplicate methods on subclasses
}

