"""
Tests for gedcomtools.cli — exit codes, source sniffing, convert command
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from gedcomtools.cli import (
    _sniff_source_type,
    OK, ERR_FILE_NOT_FOUND, ERR_UNKNOWN_SOURCE_TYPE,
    ERR_UNSUPPORTED_CONV, ERR_CONVERSION_FAILED, ERR_IO,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_cli(*args) -> subprocess.CompletedProcess:
    """Run the CLI as a subprocess and return the result."""
    import os
    src = str(Path(__file__).parent.parent / "src")
    env = {**os.environ, "PYTHONPATH": src}
    return subprocess.run(
        [sys.executable, "-m", "gedcomtools.cli", *args],
        capture_output=True,
        text=True,
        env=env,
    )


# ---------------------------------------------------------------------------
# Source type sniffing
# ---------------------------------------------------------------------------

class TestSniffSourceType:
    def test_g5_ged_file(self, ged_tiny):
        assert _sniff_source_type(ged_tiny) == "g5"

    def test_g5_small_ged(self, ged_small):
        assert _sniff_source_type(ged_small) == "g5"

    def test_g5_medium_ged(self, ged_medium):
        assert _sniff_source_type(ged_medium) == "g5"

    def test_unreadable_raises(self):
        with pytest.raises((ValueError, Exception)):
            _sniff_source_type(Path("/nonexistent/file.ged"))

    def test_unknown_type_raises(self, tmp_path):
        f = tmp_path / "mystery.xyz"
        f.write_text("not a gedcom file")
        with pytest.raises(ValueError):
            _sniff_source_type(f)

    def test_json_object_detected_as_gx(self, tmp_path):
        f = tmp_path / "test.json"
        f.write_text('{"persons": []}')
        assert _sniff_source_type(f) == "gx"

    def test_g5_synthetic_file(self, tmp_path):
        f = tmp_path / "test.ged"
        f.write_text("0 HEAD\n1 GEDC\n2 VERS 5.5.1\n0 TRLR\n")
        assert _sniff_source_type(f) == "g5"

    def test_g7_synthetic_file(self, tmp_path):
        f = tmp_path / "test.ged"
        f.write_text("0 HEAD\n1 GEDC\n2 VERS 7.0\n0 TRLR\n")
        assert _sniff_source_type(f) == "g7"


# ---------------------------------------------------------------------------
# Exit codes via subprocess
# ---------------------------------------------------------------------------

class TestExitCodes:
    def test_file_not_found(self):
        result = run_cli("convert", "/nonexistent/file.ged", "/tmp/out.json", "-gx")
        assert result.returncode == ERR_FILE_NOT_FOUND

    def test_unsupported_conversion_g5_to_g7(self, ged_tiny):
        with tempfile.NamedTemporaryFile(suffix=".ged") as tmp:
            result = run_cli("convert", str(ged_tiny), tmp.name, "-g7")
            assert result.returncode == ERR_UNSUPPORTED_CONV

    def test_unsupported_conversion_g5_to_g5(self, ged_tiny):
        # same type → OK (nothing to do)
        with tempfile.NamedTemporaryFile(suffix=".ged") as tmp:
            result = run_cli("convert", str(ged_tiny), tmp.name, "-g5")
            assert result.returncode == OK

    def test_successful_g5_to_gx(self, ged_tiny, tmp_path):
        out = tmp_path / "out.json"
        result = run_cli("convert", str(ged_tiny), str(out), "-gx")
        assert result.returncode == OK

    def test_output_file_created(self, ged_tiny, tmp_path):
        out = tmp_path / "out.json"
        run_cli("convert", str(ged_tiny), str(out), "-gx")
        assert out.exists()

    def test_output_is_valid_json(self, ged_tiny, tmp_path):
        out = tmp_path / "out.json"
        run_cli("convert", str(ged_tiny), str(out), "-gx")
        with open(out) as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_output_has_persons(self, ged_tiny, tmp_path):
        out = tmp_path / "out.json"
        run_cli("convert", str(ged_tiny), str(out), "-gx")
        with open(out) as f:
            data = json.load(f)
        assert "persons" in data
        assert len(data["persons"]) > 0

    def test_io_error_unwritable_dest(self, ged_tiny):
        result = run_cli("convert", str(ged_tiny), "/root/cant_write_here.json", "-gx")
        assert result.returncode in (ERR_IO, ERR_CONVERSION_FAILED)

    def test_stderr_message_on_file_not_found(self):
        result = run_cli("convert", "/nonexistent.ged", "/tmp/out.json", "-gx")
        assert "Error" in result.stderr or "error" in result.stderr.lower()

    def test_stderr_message_on_unsupported(self, ged_tiny):
        with tempfile.NamedTemporaryFile(suffix=".ged") as tmp:
            result = run_cli("convert", str(ged_tiny), tmp.name, "-g7")
            assert "not yet supported" in result.stderr


# ---------------------------------------------------------------------------
# Help output
# ---------------------------------------------------------------------------

class TestHelp:
    def test_top_level_help(self):
        result = run_cli("--help")
        assert result.returncode == 0
        assert "convert" in result.stdout

    def test_convert_help(self):
        result = run_cli("convert", "--help")
        assert result.returncode == 0
        assert "-gx" in result.stdout
        assert "-g5" in result.stdout
        assert "-g7" in result.stdout

    def test_no_args_exits_nonzero(self):
        result = run_cli()
        assert result.returncode != 0


# ---------------------------------------------------------------------------
# Larger file conversion via CLI
# ---------------------------------------------------------------------------

class TestLargeFileConversion:
    def test_royal92_converts(self, ged_large, tmp_path):
        out = tmp_path / "royal.json"
        result = run_cli("convert", str(ged_large), str(out), "-gx")
        assert result.returncode == OK
        assert out.exists()
        with open(out) as f:
            data = json.load(f)
        assert len(data.get("persons", [])) > 100
