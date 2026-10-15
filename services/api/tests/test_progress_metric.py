"""Unit tests for the monthly progress metric.

These tests call the real production function `compute_progress_months` which
is extracted from `get_progress()` in `app/visits/service.py`.  They do not
duplicate the algorithm — they exercise the actual production code path.

Integration tests in `test_integration.py` verify the full end-to-end behavior
including the database queries that feed data into this function.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

from app.visits.service import compute_progress_months

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _visit(
    place_id: uuid.UUID,
    rating: str,
    visited_at: datetime,
) -> MagicMock:
    """Create a minimal Visit-like object for testing compute_progress_months."""
    v = MagicMock()
    v.place_id = place_id
    v.rating = rating
    v.visited_at = visited_at
    return v


# ---------------------------------------------------------------------------
# Tests of the real production compute_progress_months()
# ---------------------------------------------------------------------------


def test_first_positive_visit_counts_as_new() -> None:
    """A restaurant the user first visits via Nosh counts toward positive-new."""
    place_id = uuid.uuid4()
    visits = [_visit(place_id, "positive", datetime(2026, 10, 12, 19, 0, tzinfo=UTC))]
    result = compute_progress_months(visits, pre_nosh_places=set())
    assert len(result) == 1
    assert result[0].month == "2026-10"
    assert result[0].confirmed_positive_new_count == 1
    assert result[0].total_confirmed_count == 1


def test_pre_nosh_place_does_not_count_as_new() -> None:
    """A place that was visited before Nosh (was_visited_before_nosh=True) must not
    count as a new discovery even if the user later confirms a positive visit."""
    place_id = uuid.uuid4()
    visits = [_visit(place_id, "positive", datetime(2026, 10, 12, 19, 0, tzinfo=UTC))]
    # Simulate was_visited_before_nosh=True for this place.
    result = compute_progress_months(visits, pre_nosh_places={place_id})
    assert result[0].confirmed_positive_new_count == 0
    assert result[0].total_confirmed_count == 1


def test_second_visit_same_place_does_not_increment_new() -> None:
    """Revisiting a Nosh-discovered restaurant in a later month does not count again."""
    place_id = uuid.uuid4()
    oct_dt = datetime(2026, 10, 15, 19, 0, tzinfo=UTC)
    nov_dt = datetime(2026, 11, 5, 19, 0, tzinfo=UTC)
    visits = [_visit(place_id, "positive", oct_dt), _visit(place_id, "positive", nov_dt)]
    result = compute_progress_months(visits, pre_nosh_places=set())
    oct_row = next(r for r in result if r.month == "2026-10")
    nov_row = next(r for r in result if r.month == "2026-11")
    assert oct_row.confirmed_positive_new_count == 1
    assert nov_row.confirmed_positive_new_count == 0  # already counted in Oct


def test_negative_rating_does_not_count_as_positive_new() -> None:
    """A confirmed visit with a negative rating does not increment positive_new."""
    place_id = uuid.uuid4()
    visits = [_visit(place_id, "negative", datetime(2026, 10, 12, 19, 0, tzinfo=UTC))]
    result = compute_progress_months(visits, pre_nosh_places=set())
    assert result[0].confirmed_positive_new_count == 0
    assert result[0].total_confirmed_count == 1


def test_multiple_new_places_same_month() -> None:
    """Two distinct positive first-visits in the same month both count."""
    p1, p2 = uuid.uuid4(), uuid.uuid4()
    t = datetime(2026, 10, 12, 19, 0, tzinfo=UTC)
    visits = [_visit(p1, "positive", t), _visit(p2, "positive", t)]
    result = compute_progress_months(visits, pre_nosh_places=set())
    assert result[0].confirmed_positive_new_count == 2


def test_months_sorted_ascending() -> None:
    """Results are sorted by month in ascending order."""
    p = uuid.uuid4()
    visits = [
        _visit(p, "positive", datetime(2026, 11, 1, 12, 0, tzinfo=UTC)),
        _visit(uuid.uuid4(), "positive", datetime(2026, 9, 1, 12, 0, tzinfo=UTC)),
    ]
    result = compute_progress_months(visits, pre_nosh_places=set())
    assert [r.month for r in result] == ["2026-09", "2026-11"]


def test_empty_visits_returns_empty() -> None:
    result = compute_progress_months([], pre_nosh_places=set())
    assert result == []


def test_provenance_flag_preserves_pre_nosh_evidence() -> None:
    """Even if the same place has both a pre-Nosh entry and a later confirmation,
    it must not count as new — the provenance flag wins."""
    place_id = uuid.uuid4()
    visits = [
        _visit(place_id, "positive", datetime(2026, 10, 1, 12, 0, tzinfo=UTC)),
        _visit(place_id, "positive", datetime(2026, 11, 1, 12, 0, tzinfo=UTC)),
    ]
    result = compute_progress_months(visits, pre_nosh_places={place_id})
    for row in result:
        assert row.confirmed_positive_new_count == 0
