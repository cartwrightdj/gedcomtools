# Run Python module/API examples from a source checkout.
#
# Usage from the repository root:
#   pwsh examples/module_examples.ps1
#
# These examples import gedcomtools directly and show the Python API rather
# than the command-line interface.

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = if ($env:PYTHON) { $env:PYTHON } else { "python" }
$env:PYTHONPATH = "$Root/src" + [IO.Path]::PathSeparator + $env:PYTHONPATH

Set-Location $Root
New-Item -ItemType Directory -Force -Path "examples/out" | Out-Null

function Invoke-Example {
    param([string] $Path)
    & $Python $Path
    if ($LASTEXITCODE -ne 0) {
        throw "Example failed: $Path"
    }
}

Write-Host "== GEDCOM 5 relationships via Python API =="
Invoke-Example "examples/read_gedcom5_relationships.py"

Write-Host ""
Write-Host "== GEDCOM 7 validation via Python API =="
Invoke-Example "examples/validate_gedcom7.py"

Write-Host ""
Write-Host "== GEDCOM 5.x to GEDCOM X via Python API =="
Invoke-Example "examples/convert_gedcom5_to_gedcomx.py"

Write-Host ""
Write-Host "== GEDCOM X graph export via Python API =="
Invoke-Example "examples/export_gml_graph.py"
