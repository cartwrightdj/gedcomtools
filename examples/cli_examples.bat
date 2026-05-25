@echo off
rem Run common gedcomtools CLI commands from a source checkout.
rem
rem Usage from the repository root:
rem   examples\cli_examples.bat
rem
rem The script uses `python -m gedcomtools.cli` so it works before installing
rem the console script. Set PYTHON=py or PYTHON=python3 if needed.

setlocal

for %%I in ("%~dp0..") do set "ROOT=%%~fI"
if not defined PYTHON set "PYTHON=python"
set "PYTHONPATH=%ROOT%\src;%PYTHONPATH%"

set "GED5=%ROOT%\.sample_data\gedcom5\gedcom5_sample.ged"
set "GED7=%ROOT%\.sample_data\gedcom70\minimal70.ged"
set "OUT=%ROOT%\examples\out\cli"

if not exist "%OUT%" mkdir "%OUT%"

echo == File summary ==
"%PYTHON%" -m gedcomtools.cli info "%GED5%" || exit /b 1

echo.
echo == List individuals as JSON ==
"%PYTHON%" -m gedcomtools.cli --json list "%GED5%" indi > "%OUT%\individuals.json" || exit /b 1
echo Wrote %OUT%\individuals.json

echo.
echo == Export faithful raw GEDCOM tree JSON ==
"%PYTHON%" -m gedcomtools.cli export "%GED5%" --to raw-json --out "%OUT%\gedcom5.raw.json" --quiet || exit /b 1
echo Wrote %OUT%\gedcom5.raw.json

echo.
echo == Convert GEDCOM 5.x to GEDCOM X JSON ==
"%PYTHON%" -m gedcomtools.cli convert "%GED5%" --to gx --out "%OUT%\gedcom5.gedcomx.json" --quiet --compact || exit /b 1
echo Wrote %OUT%\gedcom5.gedcomx.json

echo.
echo == Convert GEDCOM 5.x to GEDCOM 7 ==
"%PYTHON%" -m gedcomtools.cli convert "%GED5%" --to g7 --out "%OUT%\gedcom5-as-gedcom7.ged" --quiet || exit /b 1
echo Wrote %OUT%\gedcom5-as-gedcom7.ged

echo.
echo == Export CSV bundle ==
"%PYTHON%" -m gedcomtools.cli export "%GED5%" --to csv --out "%OUT%\gedcom5" --quiet || exit /b 1
echo Wrote %OUT%\gedcom5_*.csv

echo.
echo == Validate GEDCOM 7 sample ==
"%PYTHON%" -m gedcomtools.cli validate "%GED7%" || exit /b 1

endlocal
