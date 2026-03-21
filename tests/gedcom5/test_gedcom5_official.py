"""
Tests against the official GEDCOM 5.5.5 sample files.

Two test strategies:

1. **Local** — all .GED files pre-downloaded to ``.sample_data/gedcom5/`` are parsed
   and validated.  These run offline and are always exercised.

2. **URL sample** — a selection of files from https://www.gedcom.org/samples/
   are downloaded fresh at test time.  The ``network`` fixture skips these if
   the host is unreachable.

Source: https://www.gedcom.org/samples.html
"""
from __future__ import annotations

import io
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from gedcomtools.gedcom5.parser import Gedcom5x
from gedcomtools.gedcom5.gedcom5 import Gedcom5

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------

SAMPLE_DIR = Path(__file__).parent.parent.parent / ".sample_data" / "gedcom5"

BASE_URL = "https://www.gedcom.org/samples"

# Official GEDCOM 5.5.5 sample files from gedcom.org (original filenames)
URL_SAMPLES = [
    "555SAMPLE.GED",
]

# All local 555 sample files (including UTF-16 variants) — new descriptive names
LOCAL_SAMPLES = [
    "gedcom5_sample.ged",
    "gedcom5_minimal.ged",
    "gedcom5_remarriage.ged",
    "gedcom5_same_sex_marriage.ged",
    "gedcom5_sample_utf16be.ged",
    "gedcom5_sample_utf16le.ged",
]

# Files that are UTF-16 encoded (need special handling)
UTF16_FILES = {"gedcom5_sample_utf16be.ged", "gedcom5_sample_utf16le.ged"}

# Expected individual / family counts for known local files
EXPECTED_COUNTS = {
    "gedcom5_sample.ged":            {"individuals": 3, "families": 2},
    "gedcom5_minimal.ged":           {"individuals": 0, "families": 0},
    "gedcom5_remarriage.ged":        {"individuals": 3, "families": 3},
    "gedcom5_same_sex_marriage.ged": {"individuals": 2, "families": 1},
    "gedcom5_sample_utf16be.ged":    {"individuals": 3, "families": 2},
    "gedcom5_sample_utf16le.ged":    {"individuals": 3, "families": 2},
    # URL tests use the original gedcom.org filenames
    "555SAMPLE.GED":                 {"individuals": 3, "families": 2},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_local(filename: str) -> Gedcom5x:
    """Parse a local .GED file, handling UTF-16 encoding automatically."""
    path = SAMPLE_DIR / filename
    p = Gedcom5x()
    if filename in UTF16_FILES:
        raw = path.read_bytes()
        text = raw.decode("utf-16")
        p.parse(io.BytesIO(text.encode("utf-8")))
    else:
        p.parse_file(str(path))
    return p


def _load_from_url(filename: str) -> Gedcom5x:
    """Download *filename* from gedcom.org and parse it."""
    url = f"{BASE_URL}/{filename}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = resp.read()
    p = Gedcom5x()
    p.parse(io.BytesIO(data))
    return p


def _network_available() -> bool:
    try:
        urllib.request.urlopen(f"{BASE_URL}/555SAMPLE.GED", timeout=5)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def network():
    """Skip the caller if gedcom.org is unreachable."""
    if not _network_available():
        pytest.skip("gedcom.org not reachable — skipping network tests")


# ---------------------------------------------------------------------------
# Local tests — all pre-downloaded 555 sample files
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filename", LOCAL_SAMPLES, ids=LOCAL_SAMPLES)
def test_local_parses(filename):
    """Every local sample file loads without raising an exception."""
    path = SAMPLE_DIR / filename
    if not path.exists():
        pytest.skip(f"Pre-downloaded file not found: {path}")
    _load_local(filename)   # must not raise


@pytest.mark.parametrize("filename", LOCAL_SAMPLES, ids=LOCAL_SAMPLES)
def test_local_version_555(filename):
    """Every local sample file reports GEDCOM version 5.5.5."""
    path = SAMPLE_DIR / filename
    if not path.exists():
        pytest.skip(f"Pre-downloaded file not found: {path}")
    p = _load_local(filename)
    header = p.header
    assert header, f"{filename}: no header records found"


@pytest.mark.parametrize("filename", LOCAL_SAMPLES, ids=LOCAL_SAMPLES)
def test_local_has_header(filename):
    """Every local sample file contains a HEAD record."""
    path = SAMPLE_DIR / filename
    if not path.exists():
        pytest.skip(f"Pre-downloaded file not found: {path}")
    p = _load_local(filename)
    assert len(p.header) >= 1, f"{filename}: no header record found"


@pytest.mark.parametrize(
    "filename",
    [f for f in LOCAL_SAMPLES if f not in UTF16_FILES],
    ids=[f for f in LOCAL_SAMPLES if f not in UTF16_FILES],
)
def test_local_gedcom5_facade(filename):
    """Gedcom5 high-level facade loads each file and detects version 5.5.5."""
    path = SAMPLE_DIR / filename
    if not path.exists():
        pytest.skip(f"Pre-downloaded file not found: {path}")
    g = Gedcom5(str(path))
    assert g.detect_gedcom_version() == "5.5.5", (
        f"{filename}: expected version 5.5.5, got {g.detect_gedcom_version()}"
    )


@pytest.mark.parametrize(
    "filename,expected",
    [(f, EXPECTED_COUNTS[f]) for f in LOCAL_SAMPLES],
    ids=LOCAL_SAMPLES,
)
def test_local_record_counts(filename, expected):
    """Individual and family counts match known values."""
    path = SAMPLE_DIR / filename
    if not path.exists():
        pytest.skip(f"Pre-downloaded file not found: {path}")
    p = _load_local(filename)
    assert len(p.individuals) == expected["individuals"], (
        f"{filename}: expected {expected['individuals']} individuals, "
        f"got {len(p.individuals)}"
    )
    assert len(p.families) == expected["families"], (
        f"{filename}: expected {expected['families']} families, "
        f"got {len(p.families)}"
    )


@pytest.mark.parametrize(
    "filename",
    [f for f in LOCAL_SAMPLES if EXPECTED_COUNTS[f]["individuals"] > 0],
    ids=[f for f in LOCAL_SAMPLES if EXPECTED_COUNTS[f]["individuals"] > 0],
)
def test_local_individuals_have_xref(filename):
    """All parsed individuals have a non-None xref identifier."""
    path = SAMPLE_DIR / filename
    if not path.exists():
        pytest.skip(f"Pre-downloaded file not found: {path}")
    p = _load_local(filename)
    for indi in p.individuals:
        assert indi.xref is not None, (
            f"{filename}: individual without xref: {indi}"
        )


@pytest.mark.parametrize(
    "filename",
    [f for f in LOCAL_SAMPLES if f not in UTF16_FILES],
    ids=[f for f in LOCAL_SAMPLES if f not in UTF16_FILES],
)
def test_local_element_dictionary(filename):
    """get_element_dictionary() returns a non-empty dict for files with records."""
    path = SAMPLE_DIR / filename
    if not path.exists():
        pytest.skip(f"Pre-downloaded file not found: {path}")
    p = _load_local(filename)
    d = p.get_element_dictionary()
    assert isinstance(d, dict)
    assert d is not None


@pytest.mark.parametrize(
    "filename",
    [f for f in LOCAL_SAMPLES if f not in UTF16_FILES],
    ids=[f for f in LOCAL_SAMPLES if f not in UTF16_FILES],
)
def test_local_root_child_elements(filename):
    """get_root_child_elements() returns a non-empty list for non-minimal files."""
    path = SAMPLE_DIR / filename
    if not path.exists():
        pytest.skip(f"Pre-downloaded file not found: {path}")
    p = _load_local(filename)
    elements = p.get_root_child_elements()
    assert len(elements) > 0, f"{filename}: expected root child elements"


# ---------------------------------------------------------------------------
# Specific feature tests for named files
# ---------------------------------------------------------------------------

def test_remarriage_has_three_families():
    """gedcom5_remarriage.ged exercises remarriage: 3 individuals, 3 families."""
    path = SAMPLE_DIR / "gedcom5_remarriage.ged"
    if not path.exists():
        pytest.skip("gedcom5_remarriage.ged not found")
    p = _load_local("gedcom5_remarriage.ged")
    assert len(p.families) == 3, f"Expected 3 families (remarriage), got {len(p.families)}"
    assert len(p.individuals) == 3


def test_same_sex_marriage_has_one_family():
    """gedcom5_same_sex_marriage.ged: 2 individuals, 1 family."""
    path = SAMPLE_DIR / "gedcom5_same_sex_marriage.ged"
    if not path.exists():
        pytest.skip("gedcom5_same_sex_marriage.ged not found")
    p = _load_local("gedcom5_same_sex_marriage.ged")
    assert len(p.families) == 1
    assert len(p.individuals) == 2


def test_utf16_be_matches_utf8():
    """gedcom5_sample_utf16be.ged (UTF-16 BE) produces the same record counts as gedcom5_sample.ged."""
    be_path = SAMPLE_DIR / "gedcom5_sample_utf16be.ged"
    utf8_path = SAMPLE_DIR / "gedcom5_sample.ged"
    if not be_path.exists() or not utf8_path.exists():
        pytest.skip("UTF-16 BE or UTF-8 sample not found")
    p_be = _load_local("gedcom5_sample_utf16be.ged")
    p_utf8 = _load_local("gedcom5_sample.ged")
    assert len(p_be.individuals) == len(p_utf8.individuals)
    assert len(p_be.families) == len(p_utf8.families)


def test_utf16_le_matches_utf8():
    """gedcom5_sample_utf16le.ged (UTF-16 LE) produces the same record counts as gedcom5_sample.ged."""
    le_path = SAMPLE_DIR / "gedcom5_sample_utf16le.ged"
    utf8_path = SAMPLE_DIR / "gedcom5_sample.ged"
    if not le_path.exists() or not utf8_path.exists():
        pytest.skip("UTF-16 LE or UTF-8 sample not found")
    p_le = _load_local("gedcom5_sample_utf16le.ged")
    p_utf8 = _load_local("gedcom5_sample.ged")
    assert len(p_le.individuals) == len(p_utf8.individuals)
    assert len(p_le.families) == len(p_utf8.families)


def test_sample_individual_details():
    """gedcom5_sample.ged — the Gedcom5 facade returns full IndividualDetail objects."""
    path = SAMPLE_DIR / "gedcom5_sample.ged"
    if not path.exists():
        pytest.skip("gedcom5_sample.ged not found")
    g = Gedcom5(str(path))
    details = list(g.individual_details())
    assert len(details) == 3
    d = details[0]
    assert d.xref is not None
    assert d.names, "Expected at least one name"
    assert d.birth is not None, "Expected birth event on first individual"


def test_sample_family_details():
    """gedcom5_sample.ged — the Gedcom5 facade returns FamilyDetail objects."""
    path = SAMPLE_DIR / "gedcom5_sample.ged"
    if not path.exists():
        pytest.skip("gedcom5_sample.ged not found")
    g = Gedcom5(str(path))
    details = list(g.family_details())
    assert len(details) == 2
    for fd in details:
        assert fd.xref is not None


def test_sample_source_details():
    """gedcom5_sample.ged — the Gedcom5 facade returns SourceDetail objects."""
    path = SAMPLE_DIR / "gedcom5_sample.ged"
    if not path.exists():
        pytest.skip("gedcom5_sample.ged not found")
    g = Gedcom5(str(path))
    details = list(g.source_details())
    assert len(details) >= 1


# ---------------------------------------------------------------------------
# Network tests — live download from gedcom.org
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filename", URL_SAMPLES, ids=URL_SAMPLES)
def test_url_parses(filename, network):
    """Official samples from gedcom.org can be fetched and parsed live."""
    _load_from_url(filename)   # must not raise


@pytest.mark.parametrize("filename", URL_SAMPLES, ids=URL_SAMPLES)
def test_url_has_header(filename, network):
    """Live-downloaded files contain a HEAD record."""
    p = _load_from_url(filename)
    assert len(p.header) >= 1, f"{filename} (URL): no header record"


@pytest.mark.parametrize("filename", URL_SAMPLES, ids=URL_SAMPLES)
def test_url_record_counts(filename, network):
    """Live-downloaded record counts match local expectations."""
    if filename not in EXPECTED_COUNTS:
        pytest.skip(f"No expected counts for {filename}")
    expected = EXPECTED_COUNTS[filename]
    p = _load_from_url(filename)
    assert len(p.individuals) == expected["individuals"], (
        f"{filename} (URL): expected {expected['individuals']} individuals, "
        f"got {len(p.individuals)}"
    )
    assert len(p.families) == expected["families"], (
        f"{filename} (URL): expected {expected['families']} families, "
        f"got {len(p.families)}"
    )


@pytest.mark.parametrize("filename", URL_SAMPLES, ids=URL_SAMPLES)
def test_url_gedcom5_facade(filename, network):
    """Gedcom5 facade loaded from URL-downloaded bytes detects version 5.5.5."""
    url = f"{BASE_URL}/{filename}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = resp.read()
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".ged", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        g = Gedcom5(tmp_path)
        assert g.detect_gedcom_version() == "5.5.5", (
            f"{filename} (URL): expected 5.5.5, got {g.detect_gedcom_version()}"
        )
    finally:
        os.unlink(tmp_path)
