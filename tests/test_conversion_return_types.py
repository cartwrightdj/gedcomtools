"""
======================================================================
 Project: gedcomtools
 File:    tests/test_conversion_return_types.py
 Purpose: Verify that every conversion facade method returns the
          correct type.  These are the most basic correctness checks
          for the conversion layer and should catch any regression
          where a method returns a raw list, a dict, or None instead
          of the expected high-level object.

 Created: 2026-03-24
======================================================================
"""
from pathlib import Path

import pytest

SAMPLE_DATA  = Path(__file__).parent.parent / ".sample_data"
GED5_TINY    = SAMPLE_DATA / "gedcom5" / "gedcom5_sample.ged"
GED7_MAXIMAL = SAMPLE_DATA / "gedcom70" / "maximal70.ged"


def _require(path: Path):
    if not path.exists():
        pytest.skip(f"Sample file not found: {path}")


# ---------------------------------------------------------------------------
# Gedcom5 conversion return types
# ---------------------------------------------------------------------------

class TestGedcom5ConversionReturnTypes:
    """Gedcom5.to_gedcom7() and Gedcom5.to_gedcomx() must return the right types."""

    @pytest.fixture(autouse=True)
    def g5(self):
        _require(GED5_TINY)
        from gedcomtools.gedcom5.gedcom5 import Gedcom5
        self.g5 = Gedcom5(GED5_TINY)

    def test_to_gedcom7_returns_gedcom7(self):
        from gedcomtools.gedcom7.gedcom7 import Gedcom7
        result = self.g5.to_gedcom7()
        assert isinstance(result, Gedcom7), (
            f"Gedcom5.to_gedcom7() returned {type(result).__name__}, expected Gedcom7"
        )

    def test_to_gedcom7_not_list(self):
        result = self.g5.to_gedcom7()
        assert not isinstance(result, list), (
            "Gedcom5.to_gedcom7() returned a raw list — should return Gedcom7"
        )

    def test_to_gedcom7_has_individuals(self):
        from gedcomtools.gedcom7.gedcom7 import Gedcom7
        result = self.g5.to_gedcom7()
        assert isinstance(result, Gedcom7)
        assert len(result.individuals()) > 0

    def test_to_gedcom7_unknown_tags_drop_returns_gedcom7(self):
        from gedcomtools.gedcom7.gedcom7 import Gedcom7
        result = self.g5.to_gedcom7(unknown_tags="drop")
        assert isinstance(result, Gedcom7)

    def test_to_gedcom7_unknown_tags_convert_returns_gedcom7(self):
        from gedcomtools.gedcom7.gedcom7 import Gedcom7
        result = self.g5.to_gedcom7(unknown_tags="convert")
        assert isinstance(result, Gedcom7)

    def test_to_gedcomx_returns_gedcomx(self):
        from gedcomtools.gedcomx.gedcomx import GedcomX
        result = self.g5.to_gedcomx()
        assert isinstance(result, GedcomX), (
            f"Gedcom5.to_gedcomx() returned {type(result).__name__}, expected GedcomX"
        )

    def test_to_gedcomx_not_dict(self):
        result = self.g5.to_gedcomx()
        assert not isinstance(result, dict), (
            "Gedcom5.to_gedcomx() returned a dict — should return GedcomX"
        )

    def test_to_gedcomx_has_persons(self):
        from gedcomtools.gedcomx.gedcomx import GedcomX
        result = self.g5.to_gedcomx()
        assert isinstance(result, GedcomX)
        assert len(result.persons) > 0


# ---------------------------------------------------------------------------
# Gedcom7 conversion return types
# ---------------------------------------------------------------------------

class TestGedcom7ConversionReturnTypes:
    """Gedcom7.to_gedcomx() must return the right type."""

    @pytest.fixture(autouse=True)
    def g7(self):
        _require(GED7_MAXIMAL)
        from gedcomtools.gedcom7.gedcom7 import Gedcom7
        self.g7 = Gedcom7(GED7_MAXIMAL)

    def test_to_gedcomx_returns_gedcomx(self):
        from gedcomtools.gedcomx.gedcomx import GedcomX
        result = self.g7.to_gedcomx()
        assert isinstance(result, GedcomX), (
            f"Gedcom7.to_gedcomx() returned {type(result).__name__}, expected GedcomX"
        )

    def test_to_gedcomx_not_list(self):
        result = self.g7.to_gedcomx()
        assert not isinstance(result, list), (
            "Gedcom7.to_gedcomx() returned a raw list — should return GedcomX"
        )

    def test_to_gedcomx_not_dict(self):
        result = self.g7.to_gedcomx()
        assert not isinstance(result, dict), (
            "Gedcom7.to_gedcomx() returned a dict — should return GedcomX"
        )

    def test_to_gedcomx_has_persons(self):
        from gedcomtools.gedcomx.gedcomx import GedcomX
        result = self.g7.to_gedcomx()
        assert isinstance(result, GedcomX)
        assert len(result.persons) > 0


# ---------------------------------------------------------------------------
# Cross-format chaining return types
# ---------------------------------------------------------------------------

class TestConversionChaining:
    """g5 → g7 → gx chain must produce correct types at each step."""

    @pytest.fixture(autouse=True)
    def g5(self):
        _require(GED5_TINY)
        from gedcomtools.gedcom5.gedcom5 import Gedcom5
        self.g5 = Gedcom5(GED5_TINY)

    def test_g5_to_g7_to_gedcomx_chain(self):
        from gedcomtools.gedcom7.gedcom7 import Gedcom7
        from gedcomtools.gedcomx.gedcomx import GedcomX
        g7 = self.g5.to_gedcom7()
        assert isinstance(g7, Gedcom7)
        gx = g7.to_gedcomx()
        assert isinstance(gx, GedcomX)

    def test_g5_to_gedcomx_direct(self):
        from gedcomtools.gedcomx.gedcomx import GedcomX
        gx = self.g5.to_gedcomx()
        assert isinstance(gx, GedcomX)

    def test_g5_to_g7_person_count_preserved(self):
        """Person count should survive the g5→g7→gx chain."""
        g7 = self.g5.to_gedcom7()
        n_g7_indi = len(g7.individuals())
        gx = g7.to_gedcomx()
        assert len(gx.persons) == n_g7_indi
