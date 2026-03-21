"""
Shared fixtures for the gedcomtools test suite.
"""
import pytest
from pathlib import Path

SAMPLE_DATA = Path(__file__).parent.parent / ".sample_data"

# Small / fast files
GED_TINY    = SAMPLE_DATA / "555SAMPLE.GED"
GED_SMALL   = SAMPLE_DATA / "Sui_Dynasty.ged"
GED_MEDIUM  = SAMPLE_DATA / "allged.ged"
GED_LARGE   = SAMPLE_DATA / "Royal92-Famous+European+Royalty+Gedcom.ged"
GED_DJC     = SAMPLE_DATA / "_DJC_ Nunda Cartwright Family.ged"
GED_COMPREHENSIVE = SAMPLE_DATA / "comprehensive_test.ged"

GX_TINY     = SAMPLE_DATA / "full.gedcomx"
GX_SMALL    = SAMPLE_DATA / "blakesley_gedcomx_sample.json"
GX_MEDIUM   = SAMPLE_DATA / "blakesley_gedcomx_fullish.json"


@pytest.fixture(scope="session")
def sample_data_dir():
    return SAMPLE_DATA


@pytest.fixture(scope="session")
def ged_tiny():
    return GED_TINY


@pytest.fixture(scope="session")
def ged_small():
    return GED_SMALL


@pytest.fixture(scope="session")
def ged_medium():
    return GED_MEDIUM


@pytest.fixture(scope="session")
def ged_large():
    return GED_LARGE


@pytest.fixture(scope="session")
def ged_comprehensive():
    return GED_COMPREHENSIVE


@pytest.fixture(scope="session")
def gx_small():
    return GX_SMALL


@pytest.fixture(scope="session")
def gx_medium():
    return GX_MEDIUM
