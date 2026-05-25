# Run common gedcomtools CLI commands from a source checkout.
#
# Usage from the repository root:
#   pwsh examples/cli_examples.ps1
#
# The script uses `python -m gedcomtools.cli` so it works before installing
# the console script. Set $env:PYTHON to choose a different Python executable.

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = if ($env:PYTHON) { $env:PYTHON } else { "python" }
$env:PYTHONPATH = "$Root/src" + [IO.Path]::PathSeparator + $env:PYTHONPATH

$Ged5 = Join-Path $Root ".sample_data/gedcom5/gedcom5_sample.ged"
$Ged7 = Join-Path $Root ".sample_data/gedcom70/minimal70.ged"
$Out = Join-Path $Root "examples/out/cli"

New-Item -ItemType Directory -Force -Path $Out | Out-Null

function Invoke-GedcomTools {
    & $Python -m gedcomtools.cli @args
    if ($LASTEXITCODE -ne 0) {
        throw "gedcomtools command failed: $args"
    }
}

Write-Host "== File summary =="
Invoke-GedcomTools info $Ged5

Write-Host ""
Write-Host "== List individuals as JSON =="
Invoke-GedcomTools --json list $Ged5 indi | Set-Content -Encoding UTF8 (Join-Path $Out "individuals.json")
Write-Host "Wrote $(Join-Path $Out 'individuals.json')"

Write-Host ""
Write-Host "== Export faithful raw GEDCOM tree JSON =="
Invoke-GedcomTools export $Ged5 --to raw-json --out (Join-Path $Out "gedcom5.raw.json") --quiet
Write-Host "Wrote $(Join-Path $Out 'gedcom5.raw.json')"

Write-Host ""
Write-Host "== Convert GEDCOM 5.x to GEDCOM X JSON =="
Invoke-GedcomTools convert $Ged5 --to gx --out (Join-Path $Out "gedcom5.gedcomx.json") --quiet --compact
Write-Host "Wrote $(Join-Path $Out 'gedcom5.gedcomx.json')"

Write-Host ""
Write-Host "== Convert GEDCOM 5.x to GEDCOM 7 =="
Invoke-GedcomTools convert $Ged5 --to g7 --out (Join-Path $Out "gedcom5-as-gedcom7.ged") --quiet
Write-Host "Wrote $(Join-Path $Out 'gedcom5-as-gedcom7.ged')"

Write-Host ""
Write-Host "== Export CSV bundle =="
Invoke-GedcomTools export $Ged5 --to csv --out (Join-Path $Out "gedcom5") --quiet
Write-Host "Wrote $(Join-Path $Out 'gedcom5_*.csv')"

Write-Host ""
Write-Host "== Validate GEDCOM 7 sample =="
Invoke-GedcomTools validate $Ged7
