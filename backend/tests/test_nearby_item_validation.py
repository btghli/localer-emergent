"""Validation coverage for client-submitted nearby items."""
from pathlib import Path
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models import NearbyItem


def valid_item(**overrides):
    values = {
        "id": "item-1",
        "externalId": "wikipedia:1",
        "provider": "wikipedia",
        "sourceName": "Wikipedia",
        "sourceUrl": "https://en.wikipedia.org/wiki/Chicago",
        "category": "landmark",
        "title": "Chicago",
        "latitude": 41.88,
        "longitude": -87.63,
        "fetchedAt": "2026-10-09T12:00:00+00:00",
    }
    values.update(overrides)
    return NearbyItem(**values)


@pytest.mark.parametrize(
    "field,value",
    [
        ("sourceUrl", "javascript:alert(1)"),
        ("canonicalUrl", "data:text/html,unsafe"),
        ("imageUrl", "file:///tmp/image.jpg"),
    ],
)
def test_rejects_non_web_urls(field, value):
    with pytest.raises(ValidationError):
        valid_item(**{field: value})


def test_rejects_out_of_range_coordinates_and_confidence():
    with pytest.raises(ValidationError):
        valid_item(latitude=91)
    with pytest.raises(ValidationError):
        valid_item(confidenceScore=1.1)


def test_rejects_unbounded_content():
    with pytest.raises(ValidationError):
        valid_item(title="x" * 501)


def test_accepts_normal_verified_item():
    item = valid_item(confidenceScore=0.9)
    assert item.sourceUrl.startswith("https://")
