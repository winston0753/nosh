"""Strict meal-schedule and meal-window-key validation (no database required).

Schema validation runs before any database access, so the API negative tests
use the unit-test client.  Checks that depend on a stored schedule (session
keys, overlapping meals) live in test_integration.py.
"""

from __future__ import annotations

import pytest

from app.schedules import validation

_LUNCH = {
    "meal_type": "lunch",
    "enabled": True,
    "local_window_start": "11:30",
    "local_window_end": "13:30",
    "active_days": [0, 1, 2, 3, 4],
    "price_ceiling": 2,
}

# --------------------------------------------------------------------------- #
# Pure rules
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(("value", "minutes"), [("00:00", 0), ("09:05", 545), ("23:59", 1439)])
def test_parse_local_time_accepts_valid(value: str, minutes: int) -> None:
    assert validation.parse_local_time(value) == minutes


@pytest.mark.parametrize(
    "value", ["24:00", "25:99", "12:60", "9:00", "09:5", "0900", "ab:cd", "", " 09:00", "09:00\n"]
)
def test_parse_local_time_rejects_impossible(value: str) -> None:
    with pytest.raises(ValueError):
        validation.parse_local_time(value)


@pytest.mark.parametrize("zone", ["America/Los_Angeles", "Europe/London", "Asia/Kolkata", "UTC"])
def test_validate_time_zone_accepts_iana(zone: str) -> None:
    assert validation.validate_time_zone(zone) == zone


@pytest.mark.parametrize(
    "zone", ["Not/AZone", "", " UTC", "UTC ", "../etc/passwd", "/etc/localtime", "PST8PDT/x"]
)
def test_validate_time_zone_rejects_unknown(zone: str) -> None:
    with pytest.raises(ValueError):
        validation.validate_time_zone(zone)


@pytest.mark.parametrize("days", [[], [0, 0], [7], [-1], [True], [0, 1, 1]])
def test_validate_active_days_rejects_invalid(days: list[int]) -> None:
    with pytest.raises(ValueError):
        validation.validate_active_days(days)


def test_validate_active_days_accepts_unique_weekdays() -> None:
    assert validation.validate_active_days([6, 0, 3]) == [6, 0, 3]


@pytest.mark.parametrize(("start", "end"), [("22:00", "02:00"), ("18:00", "18:00")])
def test_validate_window_rejects_overnight_and_empty(start: str, end: str) -> None:
    with pytest.raises(ValueError):
        validation.validate_window(start, end)


@pytest.mark.parametrize(
    ("a", "b", "overlap"),
    [
        (("11:30", "13:30"), ("17:30", "20:30"), False),
        (("11:30", "13:30"), ("13:30", "15:00"), False),  # touching is not overlapping
        (("11:30", "14:00"), ("13:30", "15:00"), True),
        (("12:00", "13:00"), ("11:00", "14:00"), True),  # nested
    ],
)
def test_windows_overlap(a: tuple[str, str], b: tuple[str, str], overlap: bool) -> None:
    assert validation.windows_overlap(*a, *b) is overlap
    assert validation.windows_overlap(*b, *a) is overlap


def _check(key: str, **overrides: object) -> None:
    ctx: dict[str, object] = {
        "meal_type": "dinner",
        "active_days": [0, 1, 2, 3, 4],  # Mon–Fri
        "time_zone": "America/Los_Angeles",
        "local_window_start": "18:00",
        "local_window_end": "21:00",
    }
    ctx.update(overrides)
    validation.check_meal_window_key(key, **ctx)  # type: ignore[arg-type]


def test_meal_window_key_consistent_passes() -> None:
    _check("2026-10-12#dinner")  # a Monday


@pytest.mark.parametrize(
    ("key", "overrides"),
    [
        ("2026-10-12#lunch", {}),  # meal type mismatch
        ("2026-10-11#dinner", {}),  # Sunday, not an active day
        ("2026-02-30#dinner", {}),  # impossible date
        ("2026-13-01#dinner", {}),  # impossible month
        ("2026-10-12#supper", {}),  # unsupported meal type
        ("20261012#dinner", {}),  # malformed
        ("2026-10-12#dinner", {"time_zone": "Not/AZone"}),  # stored zone invalid
        ("2026-10-12#dinner", {"local_window_end": "17:00"}),  # stored window inverted
        ("2026-10-12#dinner", {"local_window_start": "25:00"}),  # stored time impossible
    ],
)
def test_meal_window_key_inconsistent_rejected(key: str, overrides: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        _check(key, **overrides)


# --------------------------------------------------------------------------- #
# API negative tests: every invalid case returns 422 validation_error
# --------------------------------------------------------------------------- #


def _put_schedule(client, auth_headers, meal_override=None, **body_override):
    body = {
        "time_zone": "America/Los_Angeles",
        "meals": [{**_LUNCH, **(meal_override or {})}],
        **body_override,
    }
    return client.put("/v1/me/meal-schedule", json=body, headers=auth_headers)


@pytest.mark.parametrize(
    ("override", "field"),
    [
        ({"local_window_start": "25:99"}, "meals.0.local_window_start"),
        ({"local_window_start": "24:00"}, "meals.0.local_window_start"),
        ({"local_window_end": "13:60"}, "meals.0.local_window_end"),
        ({"local_window_end": "1:30"}, "meals.0.local_window_end"),
        ({"active_days": []}, "meals.0.active_days"),
        ({"active_days": [0, 0]}, "meals.0.active_days"),
        ({"active_days": [7]}, "meals.0.active_days"),
        ({"active_days": [-1]}, "meals.0.active_days"),
        ({"active_days": ["1"]}, "meals.0.active_days.0"),
        ({"active_days": [1.0]}, "meals.0.active_days.0"),
        ({"active_days": [True]}, "meals.0.active_days.0"),
        ({"active_days": [0, 1, 2, 3, 4, 5, 6, 0]}, "meals.0.active_days"),
        ({"local_window_start": "22:00", "local_window_end": "02:00"}, "meals.0.local_window_end"),
        ({"local_window_start": "12:00", "local_window_end": "12:00"}, "meals.0.local_window_end"),
        ({"local_window_start": "13:00", "local_window_end": "12:00"}, "meals.0.local_window_end"),
        ({"meal_type": "brunch"}, "meals.0.meal_type"),
        ({"price_ceiling": 0}, "meals.0.price_ceiling"),
        ({"price_ceiling": 5}, "meals.0.price_ceiling"),
    ],
)
def test_meal_schedule_rejects_invalid_meal(client, auth_headers, override, field) -> None:
    resp = _put_schedule(client, auth_headers, override)
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert body["code"] == "validation_error"
    assert isinstance(body["message"], str) and body["message"]
    assert isinstance(body["detail"], list) and body["detail"]
    assert body["field"] == field


@pytest.mark.parametrize(
    ("override", "field"),
    [
        ({"time_zone": "Not/AZone"}, "time_zone"),
        ({"time_zone": ""}, "time_zone"),
        ({"time_zone": "../../etc/passwd"}, "time_zone"),
        ({"meals": []}, "meals"),
        ({"meals": [_LUNCH, _LUNCH]}, "meals"),
    ],
)
def test_meal_schedule_rejects_invalid_body(client, auth_headers, override, field) -> None:
    resp = _put_schedule(client, auth_headers, **override)
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "validation_error"
    assert resp.json()["field"] == field


@pytest.mark.parametrize("kind", ["office", "HOME", ""])
def test_anchor_kind_rejected(client, auth_headers, kind: str) -> None:
    resp = client.put(
        f"/v1/me/anchors/{kind}", json={"latitude": 37.7, "longitude": -122.4}, headers=auth_headers
    )
    assert resp.status_code in (404, 405, 422), resp.text


@pytest.mark.parametrize(
    "coords", [{"latitude": 91, "longitude": 0}, {"latitude": 0, "longitude": -181}, {}]
)
def test_anchor_coordinates_rejected(client, auth_headers, coords) -> None:
    resp = client.put("/v1/me/anchors/home", json=coords, headers=auth_headers)
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "validation_error"


_HERE = {"latitude": 37.759, "longitude": -122.419}


@pytest.mark.parametrize(
    "key", ["2026-10-12", "2026-10-12#supper", "2026-10-12#brunch", "x#lunch", ""]
)
def test_session_key_shape_rejected(client, auth_headers, key: str) -> None:
    resp = client.post(
        "/v1/suggestion-sessions",
        json={"meal_window_key": key, "location": _HERE},
        headers=auth_headers,
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "validation_error"
    assert resp.json()["field"] == "meal_window_key"


@pytest.mark.parametrize(
    "extra",
    [
        {},  # neither
        {"location": _HERE, "anchor": "home"},  # both
        {"anchor": "office"},
        {"location": {"latitude": 95, "longitude": 0}},
    ],
)
def test_session_anchor_shape_rejected(client, auth_headers, extra) -> None:
    resp = client.post(
        "/v1/suggestion-sessions",
        json={"meal_window_key": "2026-10-12#lunch", **extra},
        headers=auth_headers,
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "validation_error"
