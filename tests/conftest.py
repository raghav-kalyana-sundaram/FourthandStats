"""Shared pytest fixtures."""

import pytest


@pytest.fixture
def sample_plays():
    """Hand-crafted play records for unit testing metric calculations."""
    return [
        {"play_type": "pass", "epa": 0.5, "success": 1, "yards_gained": 8, "down": 1, "ydstogo": 10},
        {"play_type": "pass", "epa": -0.3, "success": 0, "yards_gained": 2, "down": 2, "ydstogo": 8},
        {"play_type": "run", "epa": 0.1, "success": 1, "yards_gained": 5, "down": 2, "ydstogo": 3},
        {"play_type": "run", "epa": -0.8, "success": 0, "yards_gained": -2, "down": 3, "ydstogo": 7},
        {"play_type": "pass", "epa": 1.2, "success": 1, "yards_gained": 20, "down": 3, "ydstogo": 7},
    ]
