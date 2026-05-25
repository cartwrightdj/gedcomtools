# gedcomtools examples

These examples are intentionally small and heavily commented. Run them from the
repository root so the relative sample-data paths resolve:

```bash
PYTHONPATH=src python3 examples/read_gedcom5_relationships.py
PYTHONPATH=src python3 examples/validate_gedcom7.py
PYTHONPATH=src python3 examples/convert_gedcom5_to_gedcomx.py
PYTHONPATH=src python3 examples/export_gml_graph.py
PYTHONPATH=src python3 examples/mcp_client_quickstart.py
```

If `gedcomtools` is already installed, you can omit `PYTHONPATH=src`.

Shell launchers are also provided for both CLI and Python module/API workflows:

```bash
bash examples/cli_examples.sh
bash examples/module_examples.sh
```

On Windows:

```bat
examples\cli_examples.bat
examples\module_examples.bat
```

PowerShell:

```powershell
pwsh examples/cli_examples.ps1
pwsh examples/module_examples.ps1
```

The CLI launchers use the modern `gedcomtools` command shape through
`python -m gedcomtools.cli`, including `--to`, `--out`, `--quiet`, and
`--compact`. All generated files are written under `examples/out/`.

The MCP example requires the optional MCP dependencies:

```bash
pip install -e ".[mcp]"
```
