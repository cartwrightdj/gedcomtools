#!/usr/bin/env bash
# Run common gedcomtools CLI commands from a source checkout.
#
# Usage from the repository root:
#   bash examples/cli_examples.sh
#
# If gedcomtools is installed, this still works; the PYTHONPATH line simply
# makes the local src/ tree win while you are developing.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

GED5="${ROOT}/.sample_data/gedcom5/gedcom5_sample.ged"
GED7="${ROOT}/.sample_data/gedcom70/minimal70.ged"
OUT="${ROOT}/examples/out/cli"

mkdir -p "${OUT}"

# Use the modern CLI form. This is equivalent to the installed `gedcomtools`
# command, but `python -m` works directly from a checkout.
GCT=("${PYTHON}" -m gedcomtools.cli)

echo "== File summary =="
"${GCT[@]}" info "${GED5}"

echo
echo "== List individuals as JSON =="
"${GCT[@]}" --json list "${GED5}" indi > "${OUT}/individuals.json"
echo "Wrote ${OUT}/individuals.json"

echo
echo "== Export faithful raw GEDCOM tree JSON =="
"${GCT[@]}" export "${GED5}" --to raw-json --out "${OUT}/gedcom5.raw.json" --quiet
echo "Wrote ${OUT}/gedcom5.raw.json"

echo
echo "== Convert GEDCOM 5.x to GEDCOM X JSON =="
"${GCT[@]}" convert "${GED5}" --to gx --out "${OUT}/gedcom5.gedcomx.json" --quiet --compact
echo "Wrote ${OUT}/gedcom5.gedcomx.json"

echo
echo "== Convert GEDCOM 5.x to GEDCOM 7 =="
"${GCT[@]}" convert "${GED5}" --to g7 --out "${OUT}/gedcom5-as-gedcom7.ged" --quiet
echo "Wrote ${OUT}/gedcom5-as-gedcom7.ged"

echo
echo "== Export CSV bundle =="
"${GCT[@]}" export "${GED5}" --to csv --out "${OUT}/gedcom5" --quiet
echo "Wrote ${OUT}/gedcom5_*.csv"

echo
echo "== Validate GEDCOM 7 sample =="
"${GCT[@]}" validate "${GED7}"
