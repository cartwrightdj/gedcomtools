@echo off
rem Run Python module/API examples from a source checkout.
rem
rem Usage from the repository root:
rem   examples\module_examples.bat
rem
rem These examples import gedcomtools directly and show the Python API rather
rem than the command-line interface.

setlocal

for %%I in ("%~dp0..") do set "ROOT=%%~fI"
if not defined PYTHON set "PYTHON=python"
set "PYTHONPATH=%ROOT%\src;%PYTHONPATH%"

cd /d "%ROOT%" || exit /b 1
if not exist "examples\out" mkdir "examples\out"

echo == GEDCOM 5 relationships via Python API ==
"%PYTHON%" examples\read_gedcom5_relationships.py || exit /b 1

echo.
echo == GEDCOM 7 validation via Python API ==
"%PYTHON%" examples\validate_gedcom7.py || exit /b 1

echo.
echo == GEDCOM 5.x to GEDCOM X via Python API ==
"%PYTHON%" examples\convert_gedcom5_to_gedcomx.py || exit /b 1

echo.
echo == GEDCOM X graph export via Python API ==
"%PYTHON%" examples\export_gml_graph.py || exit /b 1

endlocal
