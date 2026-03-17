# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'gedcom-x'
copyright = '2025, David J. Cartwright'
author = 'David J. Cartwright'
release = '0.5.5'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = []

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    #"sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
    "sphinx_copybutton",
]

# Autosummary generates stub pages
autosummary_generate = True

# Napoleon for Google/NumPy docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_use_param = True
napoleon_use_rtype = False

# Type hints shown in the signature and/or description
autodoc_typehints = "description"  # or "both" / "signature"
typehints_fully_qualified = True

# MyST (Markdown) options
myst_enable_extensions = ["colon_fence", "deflist", "attrs"]

# Intersphinx: link to external docs
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", {}),
}

# Theme
html_theme = "furo"

# If your package is importable only after install, consider:
# autodoc_mock_imports = ["heavy_optional_dependency"]
