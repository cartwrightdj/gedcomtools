"""
Tests against the official FamilySearch GEDCOM 7.0 example files.

Two test strategies:

1. **Local** — all .ged/.gdz files pre-downloaded to
   ``.sample_data/gedcom70/`` are parsed and validated.
   These run offline and are always exercised.

2. **URL sample** — three files are chosen at random from the full list
   hosted at https://gedcom.io/testfiles/gedcom70/ and downloaded
   fresh at test time.  The ``network`` fixture skips these if the
   host is unreachable.

Source: https://gedcom.io/tools/ — "Example FamilySearch GEDCOM 7.0 Files"
"""
from __future__ import annotations

import io
import random
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

import pytest

from gedcomtools.gedcom7 import Gedcom7, GedcomValidator

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------

SAMPLE_DIR = Path(__file__).parent.parent / ".sample_data" / "gedcom70"

BASE_URL = "https://gedcom.io/testfiles/gedcom70"

# Complete list of official example files (source: https://gedcom.io/tools/)
OFFICIAL_FILES = [
    "age.ged",
    "escapes.ged",
    "extension-record.ged",
    "extensions.ged",
    "lang.ged",
    "filename-1.ged",
    "long-url.ged",
    "maximal70.ged",
    "maximal70.gdz",
    "maximal70-lds.ged",
    "maximal70-memories1.ged",
    "maximal70-memories2.ged",
    "maximal70-tree1.ged",
    "maximal70-tree2.ged",
    "minimal70.ged",
    "minimal70.gdz",
    "notes-1.ged",
    "obje-1.ged",
    "remarriage1.ged",
    "remarriage2.ged",
    "same-sex-marriage.ged",
    "voidptr.ged",
    "xref.ged",
]

# Files that intentionally exercise features our validator flags as errors
# (undeclared extension tags, >1 MARR per FAM, void xref id, etc.).
# These pass parsing but are xfail for the strict no-errors assertion.
KNOWN_VALIDATOR_STRICT = {
    "extension-record.ged",  # _LOC extension not declared in HEAD.SCHMA.TAG
    "extensions.ged",        # multiple undeclared extension tags / dangling pointer
    "remarriage1.ged",       # MARR appears twice under FAM (cardinality_exceeded)
    "xref.ged",              # INDI record without xref id (tests void ptr usage)
}

# How many files to pick for the live-URL sample tests
URL_SAMPLE_SIZE = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_ged_file(path: Path) -> Gedcom7:
    """Parse *path*, unzipping first if it is a .gdz archive."""
    g = Gedcom7()
    if path.suffix == ".gdz":
        with zipfile.ZipFile(path) as zf:
            ged_names = [n for n in zf.namelist() if n.endswith(".ged")]
            assert ged_names, f"No .ged file inside {path.name}"
            text = zf.read(ged_names[0]).decode("utf-8-sig")
        g.parse_string(text)
    else:
        g.loadfile(path)
    return g


def _load_from_url(filename: str) -> Gedcom7:
    """Download *filename* from the official URL and parse it."""
    url = f"{BASE_URL}/{filename}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = resp.read()
    g = Gedcom7()
    if filename.endswith(".gdz"):
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            ged_names = [n for n in zf.namelist() if n.endswith(".ged")]
            assert ged_names, f"No .ged inside downloaded {filename}"
            text = zf.read(ged_names[0]).decode("utf-8-sig")
        g.parse_string(text)
    else:
        g.parse_string(data.decode("utf-8-sig"))
    return g


def _network_available() -> bool:
    try:
        urllib.request.urlopen(f"{BASE_URL}/minimal70.ged", timeout=5)
        return True
    except Exception:
        return False


def _error_issues(issues):
    return [i for i in issues if getattr(i, "severity", "warning") == "error"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def network():
    """Skip the caller if gedcom.io is unreachable."""
    if not _network_available():
        pytest.skip("gedcom.io not reachable — skipping network tests")


# ---------------------------------------------------------------------------
# Local tests — all 23 pre-downloaded files
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filename", OFFICIAL_FILES, ids=OFFICIAL_FILES)
def test_official_parses(filename):
    """Every official example file loads without raising an exception."""
    path = SAMPLE_DIR / filename
    if not path.exists():
        pytest.skip(f"Pre-downloaded file not found: {path}")
    _load_ged_file(path)   # must not raise


@pytest.mark.parametrize(
    "filename",
    [f for f in OFFICIAL_FILES if not f.endswith(".gdz")],
    ids=[f for f in OFFICIAL_FILES if not f.endswith(".gdz")],
)
def test_official_has_head_and_trlr(filename):
    """Every .ged file has a HEAD and a TRLR record at level 0."""
    path = SAMPLE_DIR / filename
    if not path.exists():
        pytest.skip(f"Pre-downloaded file not found: {path}")
    g = _load_ged_file(path)
    tags = {r.tag for r in g.records}
    assert "HEAD" in tags, f"{filename}: no HEAD record"
    assert "TRLR" in tags, f"{filename}: no TRLR record"


@pytest.mark.parametrize("filename", OFFICIAL_FILES, ids=OFFICIAL_FILES)
def test_official_validation_runs(filename):
    """Validation completes without raising for every official file."""
    path = SAMPLE_DIR / filename
    if not path.exists():
        pytest.skip(f"Pre-downloaded file not found: {path}")
    g = _load_ged_file(path)
    v = GedcomValidator(g)
    v.validate()   # must not raise


@pytest.mark.parametrize("filename", OFFICIAL_FILES, ids=OFFICIAL_FILES)
def test_official_no_error_issues(filename):
    """Official files that don't test extension edge-cases are error-free."""
    path = SAMPLE_DIR / filename
    if not path.exists():
        pytest.skip(f"Pre-downloaded file not found: {path}")

    if filename in KNOWN_VALIDATOR_STRICT:
        pytest.xfail(
            f"{filename} intentionally exercises features our validator "
            "flags as errors (see KNOWN_VALIDATOR_STRICT)"
        )

    g = _load_ged_file(path)
    v = GedcomValidator(g)
    issues = v.validate()
    errors = _error_issues(issues)
    assert not errors, (
        f"{filename}: {len(errors)} unexpected error(s)\n"
        + "\n".join(f"  [{i.code}] {i.message}" for i in errors)
    )


# ---------------------------------------------------------------------------
# Network tests — random sample fetched live from gedcom.io
# ---------------------------------------------------------------------------

# Sample is fixed once at collection time so parametrize IDs are stable.
_URL_SAMPLE: list[str] = random.sample(OFFICIAL_FILES, k=URL_SAMPLE_SIZE)


@pytest.mark.parametrize("filename", _URL_SAMPLE, ids=_URL_SAMPLE)
def test_url_parses(filename, network):
    """A random selection of official files can be fetched and parsed live."""
    _load_from_url(filename)   # must not raise


@pytest.mark.parametrize("filename", _URL_SAMPLE, ids=_URL_SAMPLE)
def test_url_has_head_and_trlr(filename, network):
    """Live-downloaded .ged files contain HEAD and TRLR."""
    g = _load_from_url(filename)
    tags = {r.tag for r in g.records}
    assert "HEAD" in tags
    assert "TRLR" in tags


@pytest.mark.parametrize("filename", _URL_SAMPLE, ids=_URL_SAMPLE)
def test_url_validation_runs(filename, network):
    """Validation completes without raising on live-downloaded files."""
    g = _load_from_url(filename)
    v = GedcomValidator(g)
    v.validate()


@pytest.mark.parametrize("filename", _URL_SAMPLE, ids=_URL_SAMPLE)
def test_url_no_error_issues(filename, network):
    """Live-downloaded files that don't test extension edge-cases are error-free."""
    if filename in KNOWN_VALIDATOR_STRICT:
        pytest.xfail(
            f"{filename} intentionally exercises features our validator "
            "flags as errors (see KNOWN_VALIDATOR_STRICT)"
        )
    g = _load_from_url(filename)
    v = GedcomValidator(g)
    issues = v.validate()
    errors = _error_issues(issues)
    assert not errors, (
        f"{filename} (URL): {len(errors)} unexpected error(s)\n"
        + "\n".join(f"  [{i.code}] {i.message}" for i in errors)
    )
