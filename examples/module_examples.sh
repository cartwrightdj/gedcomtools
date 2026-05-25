#!/usr/bin/env bash
# Run Python module/API examples from a source checkout.
#
# Usage from the repository root:
#   bash examples/module_examples.sh
#
# These examples import gedcomtools directly and show the Python API rather
# than the command-line interface.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

cd "${ROOT}"
mkdir -p examples/out

echo "== GEDCOM 5 relationships via Python API =="
"${PYTHON}" examples/read_gedcom5_relationships.py

echo
echo "== GEDCOM 7 validation via Python API =="
"${PYTHON}" examples/validate_gedcom7.py

echo
echo "== GEDCOM 5.x to GEDCOM X via Python API =="
"${PYTHON}" examples/convert_gedcom5_to_gedcomx.py

echo
echo "== GEDCOM X graph export via Python API =="
"${PYTHON}" examples/export_gml_graph.py
