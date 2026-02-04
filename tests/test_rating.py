"""Basic tests for product_picker."""

import pytest
from pathlib import Path

from product_picker.rating import conservative_score


def test_conservative_score():
    """Test conservative score calculation."""
    mu = 25.0
    sigma = 8.333
    score = conservative_score(mu, sigma)
    assert score == pytest.approx(mu - 3 * sigma)


def test_conservative_score_lowers_uncertainty():
    """Items with higher uncertainty should have lower conservative scores."""
    mu = 25.0
    low_uncertainty = conservative_score(mu, 5.0)
    high_uncertainty = conservative_score(mu, 10.0)
    assert low_uncertainty > high_uncertainty
