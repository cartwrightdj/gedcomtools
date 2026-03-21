"""
Shared fixtures for the gedcomtools test suite.
"""
import pytest
from pathlib import Path

SAMPLE_DATA  = Path(__file__).parent.parent / ".sample_data"
GEDCOM5_DATA = SAMPLE_DATA / "gedcom5"

GED_TINY          = GEDCOM5_DATA / "gedcom5_sample.ged"
GED_SMALL         = GEDCOM5_DATA / "gedcom5_sui_dynasty.ged"
GED_MEDIUM        = GEDCOM5_DATA / "gedcom5_all_tags_ascii.ged"
GED_LARGE         = GEDCOM5_DATA / "gedcom5_european_royalty_large.ged"
GED_COMPREHENSIVE = GEDCOM5_DATA / "gedcom5_comprehensive.ged"

GX_TINY = SAMPLE_DATA / "gedcomx" / "full.gedcomx"


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


