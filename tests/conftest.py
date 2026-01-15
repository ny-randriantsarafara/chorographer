"""Pytest fixtures and configuration."""

import pytest


@pytest.fixture
def sample_osm_node() -> dict:
    """Sample OSM node data for testing."""
    return {
        "id": 1,
        "lat": -18.8792,
        "lon": 47.5079,
        "tags": {"name": "Antananarivo"},
    }
