"""Integration tests — require a live PostgreSQL with PostGIS.

Run locally (port 5433):
    DATABASE_URL=postgresql+asyncpg://nosh:nosh_dev@localhost:5433/nosh_test \\
        uv run --frozen pytest tests/ -m integration -v

In CI the postgres service container is mapped to 5432 and DATABASE_URL is
set in the workflow environment.
"""

from __future__ import annotations

import asyncio
import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

pytestmark = pytest.mark.integration

# Default to local port 5433 (db_test); CI overrides via DATABASE_URL env var.
_DB_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://nosh:nosh_dev@localhost:5433/nosh_test")
_SYNC_URL = (
    _DB_URL.replace("asyncpg", "psycopg2")
    .replace("+asyncpg", "+psycopg2")
    .replace("postgresql+asyncpg", "postgresql+psycopg2")
)

# ---------------------------------------------------------------------------
# Session-scoped engine + schema setup
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session")
async def engine():
    e = create_async_engine(_DB_URL, echo=False)
    import subprocess

    subprocess.run(
        ["uv", "run", "--frozen", "alembic", "upgrade", "head"],
        check=True,
        env={**os.environ, "DATABASE_URL": _SYNC_URL},
    )
    yield e
    await e.dispose()


@pytest_asyncio.fixture
async def db(engine):
    """Per-test rollback-isolated session."""
    async with engine.connect() as conn:
        await conn.begin()
        factory = async_sessionmaker(
            bind=conn,
            class_=AsyncSession,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        async with factory() as session:
            yield session
        await conn.rollback()


@pytest_asyncio.fixture
async def client(db):
    """HTTP client with auth wired to the rollback-isolated session."""
    os.environ["AUTH_LOCAL_DEV"] = "true"
    os.environ["APP_ENVIRONMENT"] = "test"
    from app.config import get_settings

    get_settings.cache_clear()
    from app.core.database import get_db
    from app.main import create_app

    application = create_app()
    application.dependency_overrides[get_db] = lambda: db

    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as ac:
        yield ac
    application.dependency_overrides.clear()


_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
_USER_2_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
_AUTH = {"Authorization": f"Bearer {_USER_ID}"}
_AUTH2 = {"Authorization": f"Bearer {_USER_2_ID}"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_fixtures(db: AsyncSession) -> None:
    from app.places.service import load_fixture_data

    await load_fixture_data(db)


# Mission District, SF: every fixture place is within walking range.
_HERE = {"latitude": 37.759, "longitude": -122.419}
_HERE_LON_LAT = (_HERE["longitude"], _HERE["latitude"])

_DINNER = {
    "meal_type": "dinner",
    "enabled": True,
    "local_window_start": "18:00",
    "local_window_end": "21:00",
    "active_days": [0, 1, 2, 3, 4, 5, 6],
    "price_ceiling": None,
}
_LUNCH = {
    "meal_type": "lunch",
    "enabled": True,
    "local_window_start": "11:00",
    "local_window_end": "14:00",
    "active_days": [0, 1, 2, 3, 4, 5, 6],
    "price_ceiling": 2,
}


async def _make_schedule(
    client: AsyncClient,
    headers: dict | None = None,
    meals: list[dict] | None = None,
    time_zone: str = "America/Los_Angeles",
) -> dict:
    """PUT a meal schedule (default: dinner 18:00–21:00 every day)."""
    resp = await client.put(
        "/v1/me/meal-schedule",
        json={"time_zone": time_zone, "meals": meals if meals is not None else [_DINNER]},
        headers=headers or _AUTH,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _session_body(window_key: str, **extra: object) -> dict:
    """Session request anchored at the device location unless overridden."""
    return {"meal_window_key": window_key, **(extra or {"location": _HERE})}


async def _create_session_and_go(
    client: AsyncClient,
    window_key: str = "2026-10-12#dinner",
    headers: dict | None = None,
) -> tuple[dict, dict, dict]:
    """Create a suggestion session, record a Go response, and return
    (session, proposal, go_response)."""
    h = headers or _AUTH
    sess_resp = await client.post(
        "/v1/suggestion-sessions",
        json=_session_body(window_key),
        headers=h,
    )
    assert sess_resp.status_code == 201, sess_resp.text
    session = sess_resp.json()
    proposal = session["current_proposal"]
    assert proposal is not None, "Session must have a current proposal"

    go_resp = await client.post(
        f"/v1/proposals/{proposal['id']}/responses",
        json={"response": "go", "client_event_id": f"go-{uuid.uuid4()}"},
        headers=h,
    )
    assert go_resp.status_code == 201, go_resp.text
    assert go_resp.json()["response"] == "go"
    assert go_resp.json()["session_state"] == "accepted"

    return session, proposal, go_resp.json()


# ---------------------------------------------------------------------------
# Migration round-trip
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_migration_round_trip():
    """Migrations apply to an empty DB, downgrade cleanly, and reapply."""
    import subprocess

    result = subprocess.run(
        ["uv", "run", "--frozen", "alembic", "downgrade", "base"],
        capture_output=True,
        text=True,
        env={**os.environ, "DATABASE_URL": _SYNC_URL},
    )
    assert result.returncode == 0, result.stderr

    result = subprocess.run(
        ["uv", "run", "--frozen", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        env={**os.environ, "DATABASE_URL": _SYNC_URL},
    )
    assert result.returncode == 0, result.stderr


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_readiness_with_real_db(client):
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Meal schedule and Home/Work anchors
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_meal_schedule_put_is_idempotent_and_versioned(client):
    _, auth = _fresh_user()
    assert (await client.get("/v1/me/meal-schedule", headers=auth)).json() == {"meals": []}

    first = await _make_schedule(client, headers=auth, meals=[_LUNCH, _DINNER])
    assert [m["meal_type"] for m in first["meals"]] == ["lunch", "dinner"]
    assert all(m["version"] == 1 for m in first["meals"])
    assert first["meals"][0]["price_ceiling"] == 2
    assert first["meals"][0]["time_zone"] == "America/Los_Angeles"

    # An identical PUT changes nothing, not even the version.
    again = await _make_schedule(client, headers=auth, meals=[_LUNCH, _DINNER])
    assert [m["version"] for m in again["meals"]] == [1, 1]

    # Changing lunch bumps only lunch; omitting dinner removes it.
    changed = await _make_schedule(client, headers=auth, meals=[{**_LUNCH, "price_ceiling": 3}])
    assert [(m["meal_type"], m["version"]) for m in changed["meals"]] == [("lunch", 2)]
    assert (await client.get("/v1/me/meal-schedule", headers=auth)).json() == changed


@pytest.mark.integration
async def test_meal_schedule_and_anchors_are_per_user(client):
    _, auth = _fresh_user()
    _, other = _fresh_user()
    await _make_schedule(client, headers=auth)
    put = await client.put("/v1/me/anchors/home", json=_HERE, headers=auth)
    assert put.status_code == 200, put.text

    assert (await client.get("/v1/me/meal-schedule", headers=other)).json() == {"meals": []}
    assert (await client.get("/v1/me/anchors", headers=other)).json() == []
    # Deleting "your" home spot never touches another user's.
    assert (await client.delete("/v1/me/anchors/home", headers=other)).status_code == 204
    assert len((await client.get("/v1/me/anchors", headers=auth)).json()) == 1


@pytest.mark.integration
async def test_anchor_set_replace_delete(client):
    _, auth = _fresh_user()
    r = await client.put("/v1/me/anchors/work", json=_HERE, headers=auth)
    assert r.status_code == 200, r.text
    assert (r.json()["kind"], r.json()["latitude"], r.json()["longitude"]) == (
        "work",
        pytest.approx(_HERE["latitude"]),
        pytest.approx(_HERE["longitude"]),
    )
    moved = {"latitude": 37.76, "longitude": -122.42}
    r = await client.put("/v1/me/anchors/work", json=moved, headers=auth)
    assert r.json()["latitude"] == pytest.approx(37.76)
    assert len((await client.get("/v1/me/anchors", headers=auth)).json()) == 1

    for _ in range(2):  # idempotent
        assert (await client.delete("/v1/me/anchors/work", headers=auth)).status_code == 204
    assert (await client.get("/v1/me/anchors", headers=auth)).json() == []


@pytest.mark.integration
async def test_session_anchored_at_saved_spot(client, db):
    await _seed_fixtures(db)
    _, auth = _fresh_user()
    await _make_schedule(client, headers=auth)

    missing = await client.post(
        "/v1/suggestion-sessions",
        json=_session_body("2026-10-12#dinner", anchor="home"),
        headers=auth,
    )
    assert missing.status_code == 422, missing.text
    assert (missing.json()["code"], missing.json()["field"]) == ("anchor_not_set", "anchor")

    await client.put("/v1/me/anchors/home", json=_HERE, headers=auth)
    r = await client.post(
        "/v1/suggestion-sessions",
        json=_session_body("2026-10-12#dinner", anchor="home"),
        headers=auth,
    )
    assert r.status_code == 201, r.text
    assert r.json()["anchor_source"] == "home"
    assert r.json()["current_proposal"] is not None

    # The window's session already exists: a later device-anchored request returns it.
    again = await client.post(
        "/v1/suggestion-sessions", json=_session_body("2026-10-12#dinner"), headers=auth
    )
    assert again.json()["id"] == r.json()["id"]
    assert again.json()["anchor_source"] == "home"


# ---------------------------------------------------------------------------
# Full suggestion flow
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_suggestion_go_accepted(client, db):
    await _seed_fixtures(db)
    await _make_schedule(client)
    _, _, go = await _create_session_and_go(client)
    assert go["response"] == "go"
    assert go["session_state"] == "accepted"


@pytest.mark.integration
async def test_suggestion_another_next_distinct_proposal(client, db):
    await _seed_fixtures(db)
    await _make_schedule(client)

    resp = await client.post(
        "/v1/suggestion-sessions",
        json=_session_body("2026-10-12#dinner"),
        headers=_AUTH,
    )
    session = resp.json()
    first_place_id = session["current_proposal"]["place_id"]

    event_id = f"test-another-{uuid.uuid4()}"
    resp2 = await client.post(
        f"/v1/proposals/{session['current_proposal']['id']}/responses",
        json={"response": "another", "client_event_id": event_id},
        headers=_AUTH,
    )
    assert resp2.status_code == 201
    result = resp2.json()
    assert result["response"] == "another"
    assert result["next_proposal"] is not None
    assert result["next_proposal"]["place_id"] != first_place_id


@pytest.mark.integration
async def test_suggestion_not_today_skipped_no_preference(client, db):
    await _seed_fixtures(db)
    await _make_schedule(client)

    resp = await client.post(
        "/v1/suggestion-sessions",
        json=_session_body("2026-10-12#dinner"),
        headers=_AUTH,
    )
    session = resp.json()

    resp2 = await client.post(
        f"/v1/proposals/{session['current_proposal']['id']}/responses",
        json={"response": "not_today", "client_event_id": f"test-not-today-{uuid.uuid4()}"},
        headers=_AUTH,
    )
    result = resp2.json()
    assert result["session_state"] == "skipped"
    assert result["no_candidates"] is False


@pytest.mark.integration
async def test_duplicate_response_idempotent(client, db):
    await _seed_fixtures(db)
    await _make_schedule(client)

    resp = await client.post(
        "/v1/suggestion-sessions",
        json=_session_body("2026-10-12#dinner"),
        headers=_AUTH,
    )
    session = resp.json()
    event_id = f"test-dupe-{uuid.uuid4()}"

    r1 = await client.post(
        f"/v1/proposals/{session['current_proposal']['id']}/responses",
        json={"response": "go", "client_event_id": event_id},
        headers=_AUTH,
    )
    r2 = await client.post(
        f"/v1/proposals/{session['current_proposal']['id']}/responses",
        json={"response": "go", "client_event_id": event_id},
        headers=_AUTH,
    )
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["response"] == r2.json()["response"]


@pytest.mark.integration
async def test_duplicate_response_different_user_forbidden(client, db):
    await _seed_fixtures(db)
    await _make_schedule(client)

    resp = await client.post(
        "/v1/suggestion-sessions",
        json=_session_body("2026-10-12#dinner"),
        headers=_AUTH,
    )
    session = resp.json()
    event_id = f"test-crossuser-{uuid.uuid4()}"

    await client.post(
        f"/v1/proposals/{session['current_proposal']['id']}/responses",
        json={"response": "go", "client_event_id": event_id},
        headers=_AUTH,
    )
    # User 2 tries to replay the same client_event_id.
    r2 = await client.post(
        f"/v1/proposals/{session['current_proposal']['id']}/responses",
        json={"response": "go", "client_event_id": event_id},
        headers=_AUTH2,
    )
    assert r2.status_code == 403


@pytest.mark.integration
async def test_cross_user_response_forbidden(client, db):
    await _seed_fixtures(db)
    await _make_schedule(client)

    resp = await client.post(
        "/v1/suggestion-sessions",
        json=_session_body("2026-10-12#dinner"),
        headers=_AUTH,
    )
    session = resp.json()

    r2 = await client.post(
        f"/v1/proposals/{session['current_proposal']['id']}/responses",
        json={"response": "go", "client_event_id": f"other-{uuid.uuid4()}"},
        headers=_AUTH2,
    )
    assert r2.status_code == 403


@pytest.mark.integration
async def test_conflicting_response_after_answer_returns_409(client, db):
    """A different action on an already-answered proposal is a 409 conflict,
    not a 422 invalid-state error, even though the session is now closed."""
    await _seed_fixtures(db)
    await _make_schedule(client)

    resp = await client.post(
        "/v1/suggestion-sessions",
        json=_session_body("2026-10-12#dinner"),
        headers=_AUTH,
    )
    proposal_id = resp.json()["current_proposal"]["id"]

    r1 = await client.post(
        f"/v1/proposals/{proposal_id}/responses",
        json={"response": "go", "client_event_id": f"seq-go-{uuid.uuid4()}"},
        headers=_AUTH,
    )
    assert r1.status_code == 201
    r2 = await client.post(
        f"/v1/proposals/{proposal_id}/responses",
        json={"response": "not_today", "client_event_id": f"seq-nt-{uuid.uuid4()}"},
        headers=_AUTH,
    )
    assert r2.status_code == 409, r2.text
    assert r2.json()["code"] == "conflict"


@pytest.mark.integration
async def test_unrelated_integrity_error_not_converted_to_conflict(client, db, monkeypatch):
    """An IntegrityError from any constraint other than the two response
    idempotency constraints must propagate unchanged, not become a 409."""
    from sqlalchemy.exc import IntegrityError

    from app.core.errors import NoshError
    from app.suggestions.service import record_response

    await _seed_fixtures(db)
    await _make_schedule(client)
    resp = await client.post(
        "/v1/suggestion-sessions",
        json=_session_body("2026-10-12#dinner"),
        headers=_AUTH,
    )
    proposal_id = uuid.UUID(resp.json()["current_proposal"]["id"])

    unrelated = IntegrityError(
        "INSERT INTO proposal_responses ...",
        {},
        Exception(
            'insert or update on table "proposal_responses" violates foreign key '
            'constraint "proposal_responses_proposal_id_fkey"'
        ),
    )

    async def failing_flush(*args: object, **kwargs: object) -> None:
        raise unrelated

    monkeypatch.setattr(db, "flush", failing_flush)
    with pytest.raises(IntegrityError) as excinfo:
        await record_response(db, proposal_id, _USER_ID, "go", f"fk-{uuid.uuid4()}")
    assert excinfo.value is unrelated
    assert not isinstance(excinfo.value, NoshError)


@pytest.mark.integration
async def test_idempotent_session_creation(client, db):
    await _seed_fixtures(db)
    await _make_schedule(client)
    key = "2026-10-12#dinner"

    r1 = await client.post(
        "/v1/suggestion-sessions",
        json=_session_body(key),
        headers=_AUTH,
    )
    r2 = await client.post(
        "/v1/suggestion-sessions",
        json=_session_body(key),
        headers=_AUTH,
    )
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]


@pytest.mark.integration
async def test_exhaustion_state_after_all_another(client, db):
    """Repeated Another ends in exhausted once every nearby place was proposed."""
    await _seed_fixtures(db)
    _, auth = _fresh_user()
    await _make_schedule(client, headers=auth)

    resp2 = await client.post(
        "/v1/suggestion-sessions", json=_session_body("2026-10-12#dinner"), headers=auth
    )
    session = resp2.json()
    assert session["state"] == "active"

    final_state = session["state"]
    proposal = session.get("current_proposal")
    seen: set[str] = set()
    seq = 0
    while proposal and final_state == "active" and seq < 30:
        seq += 1
        assert proposal["place_id"] not in seen, "a place was proposed twice"
        seen.add(proposal["place_id"])
        r = await client.post(
            f"/v1/proposals/{proposal['id']}/responses",
            json={"response": "another", "client_event_id": f"exhaust-{seq}-{uuid.uuid4()}"},
            headers=auth,
        )
        data = r.json()
        final_state = data["session_state"]
        proposal = data.get("next_proposal")

    assert final_state == "exhausted"
    assert len(seen) == 20  # every fixture place, each exactly once


@pytest.mark.integration
async def test_session_far_from_every_place_has_no_candidates(client, db):
    await _seed_fixtures(db)
    _, auth = _fresh_user()
    await _make_schedule(client, headers=auth)
    r = await client.post(
        "/v1/suggestion-sessions",
        json=_session_body("2026-10-12#dinner", location={"latitude": 40.75, "longitude": -73.98}),
        headers=auth,
    )
    assert r.status_code == 201, r.text
    assert (r.json()["state"], r.json()["current_proposal"]) == ("no_candidates", None)


# ---------------------------------------------------------------------------
# Visit confirmation — requires Go on the exact proposal
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_visit_confirmation_and_progress(client, db):
    await _seed_fixtures(db)
    await _make_schedule(client)

    # Must record Go before confirming a visit.
    session, proposal, _ = await _create_session_and_go(client)

    visit_resp = await client.post(
        "/v1/visits",
        json={
            "place_id": proposal["place_id"],
            "proposal_id": proposal["id"],
            "visited_at": "2026-10-12T19:00:00Z",
            "rating": "positive",
        },
        headers=_AUTH,
    )
    assert visit_resp.status_code == 201, visit_resp.text
    visit = visit_resp.json()
    assert visit["rating"] == "positive"
    assert visit["place_id"] == proposal["place_id"]

    prog_resp = await client.get("/v1/progress", headers=_AUTH)
    assert prog_resp.status_code == 200
    total_new = sum(m["confirmed_positive_new_count"] for m in prog_resp.json())
    assert total_new >= 1


@pytest.mark.integration
async def test_visit_requires_go_response_first(client, db):
    """Confirming a proposal-backed visit without recording Go first must return 422
    with error code 'proposal_not_accepted'."""
    await _seed_fixtures(db)
    await _make_schedule(client)

    sess_resp = await client.post(
        "/v1/suggestion-sessions",
        json=_session_body("2026-10-12#dinner"),
        headers=_AUTH,
    )
    assert sess_resp.status_code == 201, sess_resp.text
    session = sess_resp.json()
    proposal = session["current_proposal"]
    assert proposal is not None

    # Attempt visit confirmation WITHOUT recording a Go response first.
    visit_resp = await client.post(
        "/v1/visits",
        json={
            "place_id": proposal["place_id"],
            "proposal_id": proposal["id"],
            "visited_at": "2026-10-12T19:00:00Z",
            "rating": "positive",
        },
        headers=_AUTH,
    )
    assert visit_resp.status_code == 422, visit_resp.text
    assert visit_resp.json().get("code") == "proposal_not_accepted"


@pytest.mark.integration
async def test_visit_idempotent_same_proposal(client, db):
    """Submitting the same visit twice returns the same visit ID (idempotent)."""
    await _seed_fixtures(db)
    await _make_schedule(client)
    session, proposal, _ = await _create_session_and_go(client)

    body = {
        "place_id": proposal["place_id"],
        "proposal_id": proposal["id"],
        "visited_at": "2026-10-12T19:00:00Z",
        "rating": "positive",
    }
    v1 = await client.post("/v1/visits", json=body, headers=_AUTH)
    v2 = await client.post("/v1/visits", json=body, headers=_AUTH)
    assert v1.status_code == 201, v1.text
    assert v2.status_code == 201, v2.text
    assert v1.json()["id"] == v2.json()["id"]


@pytest.mark.integration
async def test_visit_cross_user_forbidden(client, db):
    """Another user cannot confirm a visit on a proposal they don't own."""
    await _seed_fixtures(db)
    await _make_schedule(client)
    # User 1 records Go.
    session, proposal, _ = await _create_session_and_go(client)

    # User 2 tries to confirm the visit for user 1's proposal.
    r = await client.post(
        "/v1/visits",
        json={
            "place_id": proposal["place_id"],
            "proposal_id": proposal["id"],
            "visited_at": "2026-10-12T19:00:00Z",
            "rating": "positive",
        },
        headers=_AUTH2,
    )
    assert r.status_code == 403


@pytest.mark.integration
async def test_visit_correction(client, db):
    """A confirmed visit rating can be corrected; corrected_at is set."""
    await _seed_fixtures(db)
    await _make_schedule(client)
    session, proposal, _ = await _create_session_and_go(client)

    v = await client.post(
        "/v1/visits",
        json={
            "place_id": proposal["place_id"],
            "proposal_id": proposal["id"],
            "visited_at": "2026-10-12T19:00:00Z",
            "rating": "positive",
        },
        headers=_AUTH,
    )
    assert v.status_code == 201, v.text
    visit_id = v.json()["id"]

    patched = await client.patch(
        f"/v1/visits/{visit_id}", json={"rating": "negative"}, headers=_AUTH
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["rating"] == "negative"
    assert patched.json()["corrected_at"] is not None


# ---------------------------------------------------------------------------
# Progress metric integration tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_progress_counts_new_positive_visits(client, db):
    """The /v1/progress endpoint counts confirmed positive first-visits correctly."""
    await _seed_fixtures(db)
    await _make_schedule(client)
    _, proposal1, _ = await _create_session_and_go(client, window_key="2026-10-12#dinner")

    await client.post(
        "/v1/visits",
        json={
            "place_id": proposal1["place_id"],
            "proposal_id": proposal1["id"],
            "visited_at": "2026-10-12T19:00:00Z",
            "rating": "positive",
        },
        headers=_AUTH,
    )

    prog = await client.get("/v1/progress", headers=_AUTH)
    assert prog.status_code == 200
    total_new = sum(m["confirmed_positive_new_count"] for m in prog.json())
    assert total_new == 1


@pytest.mark.integration
async def test_progress_counts_go_after_been_here(client, db):
    """Been here already on the first proposal, then Go on the next: only the
    Go place counts as a new discovery."""
    await _seed_fixtures(db)
    uid, auth = _fresh_user()
    await _make_schedule(client, headers=auth)
    first = (await _new_session(client, "2026-10-12#dinner", auth))["current_proposal"]

    been = await client.post(
        f"/v1/proposals/{first['id']}/responses",
        json={"response": "been_here", "client_event_id": f"been-{uuid.uuid4()}"},
        headers=auth,
    )
    assert been.status_code == 201, been.text
    assert been.json()["session_state"] == "active"
    second = been.json()["next_proposal"]
    assert second["place_id"] != first["place_id"]

    await _go_and_confirm(client, second, "positive", auth)
    progress = (await client.get("/v1/progress", headers=auth)).json()
    assert sum(m["confirmed_positive_new_count"] for m in progress) == 1


# ---------------------------------------------------------------------------
# Exclusion invariants
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_visited_place_excluded_from_next_session(client, db):
    """A confirmed visited place does not appear in a subsequent session."""
    await _seed_fixtures(db)
    await _make_schedule(client)

    # Must record Go before confirming a visit.
    session, proposal, _ = await _create_session_and_go(client)
    place_id = proposal["place_id"]

    await client.post(
        "/v1/visits",
        json={
            "place_id": place_id,
            "proposal_id": proposal["id"],
            "visited_at": "2026-10-12T19:00:00Z",
            "rating": "positive",
        },
        headers=_AUTH,
    )

    resp2 = await client.post(
        "/v1/suggestion-sessions",
        json=_session_body("2026-10-13#dinner"),
        headers=_AUTH,
    )
    session2 = resp2.json()
    if session2.get("current_proposal"):
        assert session2["current_proposal"]["place_id"] != place_id


@pytest.mark.integration
async def test_not_interested_place_excluded(client, db):
    await _seed_fixtures(db)
    await _make_schedule(client)

    from app.places.fixtures import PLACES

    place_id = str(PLACES[0].id)

    await client.put(
        f"/v1/places/{place_id}/state",
        json={"state": "not_interested"},
        headers=_AUTH,
    )

    resp = await client.post(
        "/v1/suggestion-sessions",
        json=_session_body("2026-10-12#dinner"),
        headers=_AUTH,
    )
    session = resp.json()
    proposed = set()
    proposal = session.get("current_proposal")
    seq = 0
    while proposal and session["state"] == "active" and seq < 25:
        seq += 1
        proposed.add(proposal["place_id"])
        r = await client.post(
            f"/v1/proposals/{proposal['id']}/responses",
            json={"response": "another", "client_event_id": f"ni-{seq}-{uuid.uuid4()}"},
            headers=_AUTH,
        )
        data = r.json()
        proposal = data.get("next_proposal")
        session["state"] = data["session_state"]

    assert place_id not in proposed, "Not-interested place appeared as a proposal"


# ---------------------------------------------------------------------------
# Product-data deletion (not full Supabase Auth deletion)
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_product_data_deletion_removes_schedule_anchors_and_sessions(client, db):
    """DELETE /v1/me/product-data removes all owned Nosh data.

    This endpoint removes product data only — the Supabase Auth identity
    is separate and requires a service-role credential (deferred).
    """
    from sqlalchemy import func, select

    from app.suggestions.models import SuggestionSession

    await _seed_fixtures(db)
    uid, auth = _fresh_user()
    await _make_schedule(client, headers=auth)
    await client.put("/v1/me/anchors/home", json=_HERE, headers=auth)

    # Create a session and confirm a visit so there's data to delete.
    _, proposal, _ = await _create_session_and_go(client, headers=auth)
    await client.post(
        "/v1/visits",
        json={
            "place_id": proposal["place_id"],
            "proposal_id": proposal["id"],
            "visited_at": "2026-10-12T19:00:00Z",
            "rating": "positive",
        },
        headers=auth,
    )

    del_resp = await client.delete("/v1/me/product-data", headers=auth)
    assert del_resp.status_code == 204, del_resp.text

    assert (await client.get("/v1/me/meal-schedule", headers=auth)).json() == {"meals": []}
    assert (await client.get("/v1/me/anchors", headers=auth)).json() == []
    assert (await client.get("/v1/visits", headers=auth)).json() == []
    sessions = await db.execute(
        select(func.count()).select_from(SuggestionSession).where(SuggestionSession.user_id == uid)
    )
    assert sessions.scalar_one() == 0


# ---------------------------------------------------------------------------
# Session key format
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_session_key_format_accepted(client, db):
    """Keys for an enabled meal are accepted for any real date on an active day."""
    await _seed_fixtures(db)
    _, auth = _fresh_user()
    await _make_schedule(
        client,
        headers=auth,
        meals=[_LUNCH, {**_DINNER, "local_window_start": "17:30", "local_window_end": "20:30"}],
    )
    for meal in ("lunch", "dinner"):
        for date in ("2026-01-01", "2026-12-31", "2028-02-29"):
            key = f"{date}#{meal}"
            resp = await client.post(
                "/v1/suggestion-sessions", json=_session_body(key), headers=auth
            )
            assert resp.status_code == 201, f"Failed for key={key}: {resp.text}"


# ---------------------------------------------------------------------------
# Concurrent response writes (real PostgreSQL concurrency, separate sessions)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def committing_factory(engine):
    """Session factory that actually commits — used for true concurrency tests."""
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return factory


_CONCURRENT_USER_ID = uuid.UUID("cc000000-0000-0000-0000-000000000001")


async def _purge_concurrent_user(committing_factory) -> None:
    """Delete every committed row owned by the concurrent-test user.

    Includes user_place_states: a confirmed visit marks its place visited, and
    leaking that state would shrink the 20-place candidate pool by one per run.
    """
    from sqlalchemy import delete

    from app.places.models import UserPlaceState
    from app.schedules.models import MealSchedule
    from app.suggestions.models import ProposalResponse, SuggestionSession
    from app.visits.models import Visit

    async with committing_factory() as cleanup_db:
        await cleanup_db.execute(
            delete(ProposalResponse).where(ProposalResponse.user_id == _CONCURRENT_USER_ID)
        )
        await cleanup_db.execute(delete(Visit).where(Visit.user_id == _CONCURRENT_USER_ID))
        await cleanup_db.execute(
            delete(UserPlaceState).where(UserPlaceState.user_id == _CONCURRENT_USER_ID)
        )
        await cleanup_db.execute(
            delete(SuggestionSession).where(SuggestionSession.user_id == _CONCURRENT_USER_ID)
        )
        await cleanup_db.execute(
            delete(MealSchedule).where(MealSchedule.user_id == _CONCURRENT_USER_ID)
        )
        await cleanup_db.commit()


@pytest_asyncio.fixture
async def concurrent_setup(engine, committing_factory):
    """Seed fixtures and create a meal schedule + session once for concurrent tests.

    Returns (user_id, session_id, proposal_id, place_id).
    Rows for the concurrent-test user are purged before setup (recovering from
    any interrupted earlier run) and again after the test, even on failure.
    """
    from app.places.service import load_fixture_data
    from app.schedules.models import MealSchedule
    from app.suggestions.service import get_or_create_session

    setup_user = _CONCURRENT_USER_ID
    await _purge_concurrent_user(committing_factory)

    async with committing_factory() as setup_db:
        await load_fixture_data(setup_db)
        setup_db.add(
            MealSchedule(
                user_id=setup_user,
                meal_type="dinner",
                enabled=True,
                local_window_start="18:00",
                local_window_end="21:00",
                time_zone="America/Los_Angeles",
                active_days=[0, 1, 2, 3, 4, 5, 6],
            )
        )
        await setup_db.commit()

        session = await get_or_create_session(
            setup_db, setup_user, "2026-11-01#dinner", location=_HERE_LON_LAT
        )
        proposal_id = session.proposals[0].id
        place_id = session.proposals[0].place_id
        session_id = session.id

    yield setup_user, session_id, proposal_id, place_id

    # Cleanup: delete all rows created during this test.
    await _purge_concurrent_user(committing_factory)


@pytest.mark.integration
async def test_concurrent_identical_response_idempotent(
    concurrent_setup, committing_factory
) -> None:
    """Two simultaneous identical response (Go, same event_id) attempts:
    - both callers must succeed with the same stored response
    - exactly one ProposalResponse row must exist
    - no unhandled exceptions

    Mechanism: both sessions race to respond to the same proposal.  The
    session-row lock in record_response serialises them: the second caller
    blocks until the first commits, then finds the stored row and returns it —
    so both callers see the same result.
    """
    from sqlalchemy import select

    from app.suggestions.models import ProposalResponse
    from app.suggestions.service import record_response

    setup_user, _, proposal_id, _ = concurrent_setup
    event_id = f"concurrent-go-{uuid.uuid4()}"

    # asyncio.Barrier(2) makes both coroutines reach the same starting line
    # before either proceeds to the INSERT, maximising the overlap window.
    barrier = asyncio.Barrier(2)

    async def attempt() -> uuid.UUID:
        async with committing_factory() as db_session:
            await barrier.wait()  # both reach here before either inserts
            outcome = await record_response(db_session, proposal_id, setup_user, "go", event_id)
            await db_session.commit()
            return outcome.response.id

    # Both must succeed — no exceptions are acceptable here.
    id1, id2 = await asyncio.gather(attempt(), attempt())

    # Both callers received the SAME persisted response.
    assert id1 == id2, f"Expected same response ID; got {id1} vs {id2}"

    # Exactly one row in the database.
    async with committing_factory() as check_db:
        rows = (
            (
                await check_db.execute(
                    select(ProposalResponse).where(ProposalResponse.proposal_id == proposal_id)
                )
            )
            .scalars()
            .all()
        )
    assert len(rows) == 1, f"Expected 1 response row, got {len(rows)}"
    assert rows[0].response == "go"


@pytest.mark.integration
async def test_concurrent_conflicting_responses_one_wins(
    concurrent_setup, committing_factory
) -> None:
    """Two simultaneous conflicting actions (Go vs Not-today):
    - exactly one succeeds and stores a response row
    - the loser must receive ConflictError/409 — never InvalidStateError/422
      and never an arbitrary exception
    - session state must match the winning action
    - exactly one ProposalResponse row
    """
    from sqlalchemy import select

    from app.core.errors import ConflictError
    from app.suggestions.models import ProposalResponse, SuggestionSession
    from app.suggestions.service import record_response

    setup_user, session_id, proposal_id, _ = concurrent_setup

    event_go = f"conflict-go-{uuid.uuid4()}"
    event_nt = f"conflict-nt-{uuid.uuid4()}"

    barrier = asyncio.Barrier(2)

    async def attempt(action: str, eid: str) -> tuple[str, str | BaseException]:
        try:
            async with committing_factory() as db_session:
                await barrier.wait()
                outcome = await record_response(db_session, proposal_id, setup_user, action, eid)
                await db_session.commit()
                return (action, outcome.response.response)
        except Exception as exc:
            # Captured for exact assertions below; any non-ConflictError fails.
            return (action, exc)

    (a1, r1), (a2, r2) = await asyncio.gather(
        attempt("go", event_go),
        attempt("not_today", event_nt),
    )

    outcomes = [(a1, r1), (a2, r2)]
    successes = [(a, r) for a, r in outcomes if isinstance(r, str)]
    failures = [(a, r) for a, r in outcomes if not isinstance(r, str)]

    # Exactly one winner.
    assert len(successes) == 1, f"Expected 1 success; outcomes: {outcomes}"

    # Exactly one loser, and it must be ConflictError (HTTP 409) specifically.
    assert len(failures) == 1, f"Expected 1 loser error; outcomes: {outcomes}"
    loser_exc = failures[0][1]
    assert type(loser_exc) is ConflictError, (
        f"Loser must receive ConflictError; got {type(loser_exc).__name__}: {loser_exc}"
    )
    assert loser_exc.status_code == 409
    assert loser_exc.code == "conflict"

    # Exactly one ProposalResponse row.
    async with committing_factory() as check_db:
        rows = (
            (
                await check_db.execute(
                    select(ProposalResponse).where(ProposalResponse.proposal_id == proposal_id)
                )
            )
            .scalars()
            .all()
        )
    assert len(rows) == 1, f"Expected 1 response row, got {len(rows)}"

    # Session state must match the winning action.
    winning_action = successes[0][0]
    expected_state = "accepted" if winning_action == "go" else "skipped"
    async with committing_factory() as state_db:
        srow = await state_db.get(SuggestionSession, session_id)
    assert srow is not None
    assert srow.state == expected_state, (
        f"Expected session state={expected_state!r}, got {srow.state!r}"
    )


@pytest.mark.integration
async def test_concurrent_visit_confirmation_idempotent(
    concurrent_setup, committing_factory
) -> None:
    """Two simultaneous visit confirmations for the same accepted proposal:
    - both callers must receive the same visit ID
    - exactly one Visit row must exist
    """
    from sqlalchemy import select

    from app.suggestions.service import record_response
    from app.visits.models import Visit
    from app.visits.schemas import VisitCreate
    from app.visits.service import confirm_visit

    setup_user, _, proposal_id, place_id = concurrent_setup

    # Record Go first so confirmation is allowed.
    async with committing_factory() as go_db:
        await record_response(go_db, proposal_id, setup_user, "go", f"go-{uuid.uuid4()}")
        await go_db.commit()

    visit_body = VisitCreate(
        place_id=place_id,
        proposal_id=proposal_id,
        visited_at="2026-11-01T19:00:00Z",  # type: ignore[arg-type]
        rating="positive",
    )

    barrier = asyncio.Barrier(2)

    async def attempt_visit() -> uuid.UUID:
        async with committing_factory() as db_session:
            await barrier.wait()
            v = await confirm_visit(db_session, setup_user, visit_body)
            await db_session.commit()
            return v.id

    # Both must succeed (idempotent: same proposal_id → same visit row).
    vid1, vid2 = await asyncio.gather(attempt_visit(), attempt_visit())

    # Both callers received the SAME visit ID.
    assert vid1 == vid2, f"Expected same visit ID; got {vid1} vs {vid2}"

    # Exactly one visit row.
    async with committing_factory() as check_db:
        rows = (
            (
                await check_db.execute(
                    select(Visit).where(
                        Visit.user_id == setup_user, Visit.proposal_id == proposal_id
                    )
                )
            )
            .scalars()
            .all()
        )
    assert len(rows) == 1, f"Expected 1 visit row, got {len(rows)}"


@pytest.mark.integration
async def test_concurrent_session_creation_idempotent(concurrent_setup, committing_factory) -> None:
    """Two simultaneous session creations for the same (user, window):
    - both callers must receive the same session ID
    - exactly one SuggestionSession row must exist

    The meal_schedules FOR UPDATE lock in get_or_create_session serialises the
    two inserts so one wins and the other re-reads the winner's session.
    """
    from sqlalchemy import select

    from app.suggestions.models import SuggestionSession
    from app.suggestions.service import get_or_create_session

    setup_user, _, _, _ = concurrent_setup
    window_key = "2026-11-02#dinner"  # distinct from the one created in setup

    barrier = asyncio.Barrier(2)

    async def attempt_session() -> str:
        async with committing_factory() as db_session:
            await barrier.wait()
            s = await get_or_create_session(
                db_session, setup_user, window_key, location=_HERE_LON_LAT
            )
            await db_session.commit()
            return str(s.id)

    # Both must succeed and return the same session ID.
    sid1, sid2 = await asyncio.gather(attempt_session(), attempt_session())

    assert sid1 == sid2, f"Expected same session ID; got {sid1} vs {sid2}"

    # Exactly one session row for this window key.
    async with committing_factory() as check_db:
        rows = (
            (
                await check_db.execute(
                    select(SuggestionSession).where(
                        SuggestionSession.user_id == setup_user,
                        SuggestionSession.meal_window_key == window_key,
                    )
                )
            )
            .scalars()
            .all()
        )
    assert len(rows) == 1, f"Expected 1 session row, got {len(rows)}"


# ===========================================================================
# Correctness hardening (2026-10-16)
# ===========================================================================


def _fresh_user() -> tuple[uuid.UUID, dict[str, str]]:
    """A user with no prior rows, so exact-value assertions cannot see leftovers."""
    uid = uuid.uuid4()
    return uid, {"Authorization": f"Bearer {uid}"}


async def _new_session(client: AsyncClient, key: str, headers: dict) -> dict:
    resp = await client.post("/v1/suggestion-sessions", json=_session_body(key), headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _go_and_confirm(client: AsyncClient, proposal: dict, rating: str, headers: dict) -> dict:
    go = await client.post(
        f"/v1/proposals/{proposal['id']}/responses",
        json={"response": "go", "client_event_id": f"go-{proposal['id']}"},
        headers=headers,
    )
    assert go.status_code == 201, go.text
    visit = await client.post(
        "/v1/visits",
        json={
            "place_id": proposal["place_id"],
            "proposal_id": proposal["id"],
            "visited_at": "2026-10-12T19:00:00Z",
            "rating": rating,
        },
        headers=headers,
    )
    assert visit.status_code == 201, visit.text
    return visit.json()


async def _place_state(db: AsyncSession, user_id: uuid.UUID, place_id: str):
    from sqlalchemy import select

    from app.places.models import UserPlaceState

    result = await db.execute(
        select(UserPlaceState)
        .where(
            UserPlaceState.user_id == user_id,
            UserPlaceState.place_id == uuid.UUID(place_id),
        )
        .execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()


async def _primary_cuisine(db: AsyncSession, place_id: str) -> uuid.UUID:
    from sqlalchemy import select

    from app.places.models import PlaceCuisine

    result = await db.execute(
        select(PlaceCuisine.cuisine_id).where(
            PlaceCuisine.place_id == uuid.UUID(place_id), PlaceCuisine.is_primary.is_(True)
        )
    )
    return result.scalar_one()


# ---------------------------------------------------------------------------
# Been here already provenance (D025, D018)
# ---------------------------------------------------------------------------


async def _been_here(client: AsyncClient, proposal: dict, headers: dict) -> dict:
    r = await client.post(
        f"/v1/proposals/{proposal['id']}/responses",
        json={"response": "been_here", "client_event_id": f"been-{proposal['id']}"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.integration
async def test_been_here_place_never_counts_toward_north_star(client, db):
    """Been here already marks the place visited before Nosh.  A later positive
    visit to the same place keeps that provenance and never counts as new."""
    await _seed_fixtures(db)
    uid, auth = _fresh_user()
    await _make_schedule(client, headers=auth)

    proposal = (await _new_session(client, "2026-10-12#dinner", auth))["current_proposal"]
    place_id = proposal["place_id"]
    result = await _been_here(client, proposal, auth)
    assert result["response"] == "been_here"
    assert result["next_proposal"]["place_id"] != place_id

    row = await _place_state(db, uid, place_id)
    assert (row.state, row.source, row.was_visited_before_nosh) == ("visited", "been_here", True)

    visit = await client.post(
        "/v1/visits",
        json={
            "place_id": place_id,
            "visited_at": "2026-10-14T19:00:00Z",
            "rating": "positive",
            "confirmation_source": "manual",
        },
        headers=auth,
    )
    assert visit.status_code == 201, visit.text
    row = await _place_state(db, uid, place_id)
    assert row.source == "confirmation"
    assert row.was_visited_before_nosh is True, "confirmation must not erase provenance"

    progress = (await client.get("/v1/progress", headers=auth)).json()
    assert progress == [
        {"month": "2026-10", "confirmed_positive_new_count": 0, "total_confirmed_count": 1}
    ]


@pytest.mark.integration
async def test_been_here_provenance_survives_manual_edits(client, db):
    await _seed_fixtures(db)
    _, auth = _fresh_user()
    await _make_schedule(client, headers=auth)
    proposal = (await _new_session(client, "2026-10-12#dinner", auth))["current_proposal"]
    place_id = proposal["place_id"]
    await _been_here(client, proposal, auth)

    for state in ("unknown", "not_interested", "visited"):
        manual = await client.put(
            f"/v1/places/{place_id}/state", json={"state": state}, headers=auth
        )
        assert manual.status_code == 200, manual.text
        assert manual.json()["source"] == "manual"
        assert manual.json()["was_visited_before_nosh"] is True


@pytest.mark.integration
async def test_manual_place_state_never_marks_pre_nosh(client, db):
    await _seed_fixtures(db)
    uid, auth = _fresh_user()
    await _make_schedule(client, headers=auth)
    proposal = (await _new_session(client, "2026-10-12#dinner", auth))["current_proposal"]

    manual = await client.put(
        f"/v1/places/{proposal['place_id']}/state", json={"state": "visited"}, headers=auth
    )
    assert manual.status_code == 200, manual.text
    assert manual.json()["source"] == "manual"
    assert manual.json()["was_visited_before_nosh"] is False


@pytest.mark.integration
async def test_been_here_negative_paths_and_replay(client, db):
    await _seed_fixtures(db)
    uid, auth = _fresh_user()
    _, other = _fresh_user()
    await _make_schedule(client, headers=auth)
    first = (await _new_session(client, "2026-10-12#dinner", auth))["current_proposal"]
    url = f"/v1/proposals/{first['id']}/responses"
    body = {"response": "been_here", "client_event_id": f"been-{uuid.uuid4()}"}

    # Another user cannot mark someone else's proposal.
    r = await client.post(url, json=body, headers=other)
    assert r.status_code == 403 and r.json()["code"] == "forbidden", r.text
    assert await _place_state(db, uid, first["place_id"]) is None

    original = await client.post(url, json=body, headers=auth)
    assert original.status_code == 201, original.text
    # Replays (same or new event id) return the original result.
    assert (await client.post(url, json=body, headers=auth)).json() == original.json()
    retry = {"response": "been_here", "client_event_id": f"been-{uuid.uuid4()}"}
    assert (await client.post(url, json=retry, headers=auth)).json() == original.json()
    # A different action on the same proposal conflicts.
    go = {"response": "go", "client_event_id": f"go-{uuid.uuid4()}"}
    r = await client.post(url, json=go, headers=auth)
    assert r.status_code == 409 and r.json()["code"] == "conflict", r.text

    # Excluded from the next session too.
    nxt = await _new_session(client, "2026-10-13#dinner", auth)
    assert nxt["current_proposal"]["place_id"] != first["place_id"]


@pytest.mark.integration
async def test_nonexistent_place_returns_stable_404(client, db):
    _, auth = _fresh_user()
    missing = uuid.uuid4()
    r = await client.put(f"/v1/places/{missing}/state", json={"state": "visited"}, headers=auth)
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "not_found"

    r = await client.post(
        "/v1/visits",
        json={
            "place_id": str(missing),
            "visited_at": "2026-10-12T19:00:00Z",
            "rating": "positive",
            "confirmation_source": "manual",
        },
        headers=auth,
    )
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "not_found"


# ---------------------------------------------------------------------------
# Recommendation priors and history provenance (service level)
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_cuisine_stats_without_pre_nosh_history_are_neutral(client, db):
    from app.recommendations.engine import _beta_params
    from app.suggestions.service import _load_cuisine_stats

    await _seed_fixtures(db)
    uid, _ = _fresh_user()
    stats = await _load_cuisine_stats(db, uid)
    assert stats, "every catalog cuisine must be represented"
    for s in stats.values():
        assert s.history_frequency is None
        assert _beta_params(s) == (1.0, 1.0)


@pytest.mark.integration
async def test_cuisine_stats_history_only_from_been_here_and_outcomes_only_from_proposals(
    client, db
):
    from app.places.fixtures import PLACES
    from app.suggestions.service import _load_cuisine_stats

    await _seed_fixtures(db)
    uid, auth = _fresh_user()
    await _make_schedule(client, headers=auth)

    # 1. Pre-Nosh history: one Been here already.
    first = (await _new_session(client, "2026-10-12#dinner", auth))["current_proposal"]
    been_id = first["place_id"]
    p1 = (await _been_here(client, first, auth))["next_proposal"]
    been_cuisine = await _primary_cuisine(db, been_id)

    stats = await _load_cuisine_stats(db, uid)
    assert stats[been_cuisine].history_frequency == 1.0
    assert all(s.history_frequency == 0.0 for c, s in stats.items() if c != been_cuisine)
    assert all(
        s.confirmed_positive_visits == 0 and s.confirmed_negative_visits == 0
        for s in stats.values()
    )

    # 2. Later Nosh visits: one positive, one negative.
    await _go_and_confirm(client, p1, "positive", auth)
    p2 = (await _new_session(client, "2026-10-13#dinner", auth))["current_proposal"]
    await _go_and_confirm(client, p2, "negative", auth)
    assert len({been_id, p1["place_id"], p2["place_id"]}) == 3

    # 3. A manual visit (no proposal) must not update cuisine preference (D015).
    manual_place = next(
        str(p.id) for p in PLACES if str(p.id) not in {been_id, p1["place_id"], p2["place_id"]}
    )
    r = await client.post(
        "/v1/visits",
        json={
            "place_id": manual_place,
            "visited_at": "2026-10-14T19:00:00Z",
            "rating": "positive",
            "confirmation_source": "manual",
        },
        headers=auth,
    )
    assert r.status_code == 201, r.text

    after = await _load_cuisine_stats(db, uid)
    # History is unchanged: post-Nosh visits are never pre-Nosh history.
    for cid, s in after.items():
        assert s.history_frequency == stats[cid].history_frequency

    c1 = await _primary_cuisine(db, p1["place_id"])
    c2 = await _primary_cuisine(db, p2["place_id"])
    expected_pos = {c1: 1}
    expected_neg = {c2: 1}
    for cid, s in after.items():
        assert s.confirmed_positive_visits == expected_pos.get(cid, 0), cid
        assert s.confirmed_negative_visits == expected_neg.get(cid, 0), cid


# ---------------------------------------------------------------------------
# Meal-schedule and meal-window validation (stored-schedule paths)
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_overlapping_meals_rejected_and_schedule_unchanged(client, db):
    _, auth = _fresh_user()
    stored = await _make_schedule(client, headers=auth, meals=[_LUNCH])

    for dinner in (
        {**_DINNER, "local_window_start": "13:00"},  # overlaps lunch 11:00–14:00
        {**_DINNER, "local_window_start": "10:00", "local_window_end": "11:30"},
    ):
        r = await client.put(
            "/v1/me/meal-schedule",
            json={"time_zone": "America/Los_Angeles", "meals": [_LUNCH, dinner]},
            headers=auth,
        )
        assert r.status_code == 422, r.text
        assert (r.json()["code"], r.json()["field"]) == ("validation_error", "meals")
    assert (await client.get("/v1/me/meal-schedule", headers=auth)).json() == stored

    # Overlap is allowed when the meals share no day, or one is disabled.
    weekend_dinner = {**_DINNER, "local_window_start": "13:00", "active_days": [5, 6]}
    weekday_lunch = {**_LUNCH, "active_days": [0, 1, 2, 3, 4]}
    for meals in (
        [weekday_lunch, weekend_dinner],
        [_LUNCH, {**_DINNER, "enabled": False, "local_window_start": "13:00"}],
    ):
        r = await client.put(
            "/v1/me/meal-schedule",
            json={"time_zone": "America/Los_Angeles", "meals": meals},
            headers=auth,
        )
        assert r.status_code == 200, r.text


@pytest.mark.integration
async def test_session_key_must_match_schedule(client, db):
    await _seed_fixtures(db)
    _, auth = _fresh_user()

    # No schedule yet.
    r = await client.post(
        "/v1/suggestion-sessions", json=_session_body("2026-10-12#dinner"), headers=auth
    )
    assert r.status_code == 422 and r.json()["field"] == "meal_window_key", r.text

    await _make_schedule(
        client,
        headers=auth,
        meals=[{**_DINNER, "active_days": [0, 1, 2, 3, 4]}, {**_LUNCH, "enabled": False}],
    )
    for key in (
        "2026-10-12#lunch",  # lunch is disabled
        "2026-10-11#dinner",  # Sunday: inactive day
        "2026-10-17#dinner",  # Saturday: inactive day
        "2026-02-30#dinner",  # impossible date
        "2026-00-10#dinner",  # impossible month
    ):
        r = await client.post("/v1/suggestion-sessions", json=_session_body(key), headers=auth)
        assert r.status_code == 422, (key, r.text)
        assert r.json()["code"] == "validation_error"
        assert r.json()["field"] == "meal_window_key"

    ok = await client.post(
        "/v1/suggestion-sessions", json=_session_body("2026-10-12#dinner"), headers=auth
    )
    assert ok.status_code == 201, ok.text


@pytest.mark.integration
async def test_session_rejected_for_stored_schedule_with_invalid_values(client, db):
    """Rows written before strict validation (or by migration) cannot open a session."""
    from sqlalchemy import delete

    from app.schedules.models import MealSchedule

    uid, auth = _fresh_user()
    for tz, start, end in (
        ("Not/AZone", "18:00", "21:00"),
        ("America/Los_Angeles", "22:00", "02:00"),
        ("America/Los_Angeles", "25:99", "26:00"),
    ):
        await db.execute(delete(MealSchedule).where(MealSchedule.user_id == uid))
        db.add(
            MealSchedule(
                user_id=uid,
                meal_type="dinner",
                enabled=True,
                local_window_start=start,
                local_window_end=end,
                time_zone=tz,
                active_days=[0, 1, 2, 3, 4, 5, 6],
            )
        )
        await db.flush()
        r = await client.post(
            "/v1/suggestion-sessions", json=_session_body("2026-10-12#dinner"), headers=auth
        )
        assert r.status_code == 422, (tz, start, end, r.text)
        assert r.json()["code"] == "validation_error"


# ---------------------------------------------------------------------------
# Candidate queue (D022): ranked once, no stored coordinate, emptied on close
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_candidate_queue_drains_and_clears(client, db):
    from sqlalchemy import select

    from app.suggestions.models import SuggestionSession

    await _seed_fixtures(db)
    uid, auth = _fresh_user()
    await _make_schedule(client, headers=auth)

    async def queue_len(session_id: str) -> int:
        row = (
            await db.execute(
                select(SuggestionSession)
                .where(SuggestionSession.id == uuid.UUID(session_id))
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        return len(row.candidate_queue)

    s1 = await _new_session(client, "2026-10-12#dinner", auth)
    assert s1["anchor_source"] == "device"
    assert await queue_len(s1["id"]) == 19  # 20 places, first one proposed

    r = await client.post(
        f"/v1/proposals/{s1['current_proposal']['id']}/responses",
        json={"response": "another", "client_event_id": f"a-{uuid.uuid4()}"},
        headers=auth,
    )
    assert await queue_len(s1["id"]) == 18

    # A newer meal window drops the older session's remaining queue.
    s2 = await _new_session(client, "2026-10-13#dinner", auth)
    assert await queue_len(s1["id"]) == 0
    assert await queue_len(s2["id"]) == 19

    # Closing a session (Go) empties its queue.
    await _go_and_confirm(client, s2["current_proposal"], "positive", auth)
    assert await queue_len(s2["id"]) == 0
    # The open session's Another still works after its queue was dropped: exhausted.
    nxt = r.json()["next_proposal"]
    r = await client.post(
        f"/v1/proposals/{nxt['id']}/responses",
        json={"response": "another", "client_event_id": f"a-{uuid.uuid4()}"},
        headers=auth,
    )
    assert r.json()["session_state"] == "exhausted"


@pytest.mark.integration
async def test_queue_order_matches_one_at_a_time_generation(client, db):
    """Ranking once at creation proposes exactly what policy_v0 would propose
    one Another at a time."""
    from app.places.service import build_candidates
    from app.recommendations.engine import recommend
    from app.suggestions.service import WALKING_RADIUS_METERS, _load_cuisine_stats

    await _seed_fixtures(db)
    uid, auth = _fresh_user()
    await _make_schedule(client, headers=auth)
    session = await _new_session(client, "2026-10-12#dinner", auth)

    proposed: list[str] = []
    proposal = session["current_proposal"]
    while proposal:
        proposed.append(proposal["place_id"])
        r = await client.post(
            f"/v1/proposals/{proposal['id']}/responses",
            json={"response": "another", "client_event_id": f"o-{uuid.uuid4()}"},
            headers=auth,
        )
        proposal = r.json()["next_proposal"]

    stats = await _load_cuisine_stats(db, uid)
    expected: list[str] = []
    for seq in range(1, len(proposed) + 1):
        already = {uuid.UUID(p) for p in expected}
        candidates = await build_candidates(db, uid, *_HERE_LON_LAT, WALKING_RADIUS_METERS, already)
        outcome = recommend(
            session_id=uuid.UUID(session["id"]),
            candidates=candidates,
            stats_by_cuisine=stats,
            already_proposed=already,
            radius_meters=WALKING_RADIUS_METERS,
            sequence_number=seq,
            meal_type="dinner",
        )
        expected.append(str(outcome.proposal.candidate.place_id))  # type: ignore[union-attr]
    assert proposed == expected


# ---------------------------------------------------------------------------
# Visit-history pagination
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_visit_history_pagination_is_deterministic_with_timestamp_ties(client, db):
    from app.places.fixtures import PLACES

    await _seed_fixtures(db)
    _, auth = _fresh_user()
    created: list[dict] = []
    # Five visits sharing one timestamp plus one earlier and one later.
    stamps = ["2026-10-12T19:00:00Z"] * 5 + ["2026-10-11T19:00:00Z", "2026-10-13T19:00:00Z"]
    for place, stamp in zip(PLACES, stamps, strict=False):
        r = await client.post(
            "/v1/visits",
            json={
                "place_id": str(place.id),
                "visited_at": stamp,
                "rating": "positive",
                "confirmation_source": "manual",
            },
            headers=auth,
        )
        assert r.status_code == 201, r.text
        created.append(r.json())

    seen: list[str] = []
    cursor: str | None = None
    for _ in range(10):
        params = {"limit": 2, **({"cursor": cursor} if cursor else {})}
        page = (await client.get("/v1/visits", params=params, headers=auth)).json()
        if not page:
            break
        seen += [v["id"] for v in page]
        cursor = page[-1]["id"]

    assert len(seen) == len(set(seen)) == len(created), "no visit skipped or repeated"
    expected = sorted(created, key=lambda v: (v["visited_at"], uuid.UUID(v["id"])), reverse=True)
    assert seen == [v["id"] for v in expected]


@pytest.mark.integration
async def test_visit_history_cursor_owned_by_other_user_rejected(client, db):
    from app.places.fixtures import PLACES

    await _seed_fixtures(db)
    _, auth = _fresh_user()
    _, other = _fresh_user()
    r = await client.post(
        "/v1/visits",
        json={
            "place_id": str(PLACES[0].id),
            "visited_at": "2026-10-12T19:00:00Z",
            "rating": "positive",
            "confirmation_source": "manual",
        },
        headers=auth,
    )
    page = await client.get("/v1/visits", params={"cursor": r.json()["id"]}, headers=other)
    assert page.status_code == 404, page.text
    assert page.json()["code"] == "not_found"


# ---------------------------------------------------------------------------
# Idempotent replay of Another
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_another_replay_returns_original_next_proposal(client, db):
    await _seed_fixtures(db)
    _, auth = _fresh_user()
    await _make_schedule(client, headers=auth)
    created = await _new_session(client, "2026-10-12#dinner", auth)
    original_session_id = created["id"]
    first = created["current_proposal"]
    url = f"/v1/proposals/{first['id']}/responses"
    body = {"response": "another", "client_event_id": f"another-{uuid.uuid4()}"}

    original = await client.post(url, json=body, headers=auth)
    assert original.status_code == 201, original.text
    assert original.json()["next_proposal"] is not None
    assert original.json()["session_state"] == "active"

    replay = await client.post(url, json=body, headers=auth)
    assert replay.status_code == 201, replay.text
    assert replay.json() == original.json()

    # Same action under a different event id is also equivalent.
    other_event = await client.post(
        url,
        json={"response": "another", "client_event_id": f"another-{uuid.uuid4()}"},
        headers=auth,
    )
    assert other_event.status_code == 201, other_event.text
    assert other_event.json() == original.json()

    # Even after the session moves on (Go on the next proposal), a late retry of
    # the Another still returns what the original request returned.
    await _go_and_confirm(client, original.json()["next_proposal"], "positive", auth)
    late = await client.post(url, json=body, headers=auth)
    assert late.status_code == 201, late.text
    assert late.json() == original.json()

    # Replays generated no extra proposal: the session holds exactly two.
    from sqlalchemy import func, select

    from app.suggestions.models import Proposal

    count = await db.execute(
        select(func.count())
        .select_from(Proposal)
        .where(Proposal.suggestion_session_id == uuid.UUID(original_session_id))
    )
    assert count.scalar_one() == 2


@pytest.mark.integration
async def test_another_replay_after_exhaustion_is_equivalent(client, db):
    await _seed_fixtures(db)
    _, auth = _fresh_user()
    await _make_schedule(client, headers=auth)
    proposal = (await _new_session(client, "2026-10-12#dinner", auth))["current_proposal"]

    last: tuple[str, dict, dict] | None = None
    for i in range(40):
        body = {"response": "another", "client_event_id": f"exhaust-{i}-{uuid.uuid4()}"}
        url = f"/v1/proposals/{proposal['id']}/responses"
        r = await client.post(url, json=body, headers=auth)
        assert r.status_code == 201, r.text
        last = (url, body, r.json())
        if r.json()["no_candidates"]:
            break
        proposal = r.json()["next_proposal"]
    assert last is not None
    url, body, original = last
    assert original == {
        "response": "another",
        "session_state": "exhausted",
        "next_proposal": None,
        "no_candidates": True,
    }
    replay = await client.post(url, json=body, headers=auth)
    assert replay.status_code == 201, replay.text
    assert replay.json() == original


@pytest.mark.integration
async def test_another_replay_by_other_user_forbidden(client, db):
    await _seed_fixtures(db)
    _, auth = _fresh_user()
    _, other = _fresh_user()
    await _make_schedule(client, headers=auth)
    first = (await _new_session(client, "2026-10-12#dinner", auth))["current_proposal"]
    url = f"/v1/proposals/{first['id']}/responses"
    body = {"response": "another", "client_event_id": f"another-{uuid.uuid4()}"}
    assert (await client.post(url, json=body, headers=auth)).status_code == 201
    r = await client.post(url, json=body, headers=other)
    assert r.status_code == 403 and r.json()["code"] == "forbidden", r.text


# ---------------------------------------------------------------------------
# Concurrent first-time user_place_states writes
# ---------------------------------------------------------------------------


_RACE_ROUNDS = 10


async def _clear_place_states(committing_factory, user_id: uuid.UUID) -> None:
    from sqlalchemy import delete

    from app.places.models import UserPlaceState

    async with committing_factory() as session:
        await session.execute(delete(UserPlaceState).where(UserPlaceState.user_id == user_id))
        await session.commit()


async def _place_state_rows(committing_factory, user_id: uuid.UUID, place_id: uuid.UUID) -> list:
    from sqlalchemy import select

    from app.places.models import UserPlaceState

    async with committing_factory() as check_db:
        result = await check_db.execute(
            select(UserPlaceState).where(
                UserPlaceState.user_id == user_id, UserPlaceState.place_id == place_id
            )
        )
        return list(result.scalars().all())


@pytest.mark.integration
async def test_concurrent_first_pre_nosh_writes_atomic(
    concurrent_setup, committing_factory
) -> None:
    """Two simultaneous first-time pre-Nosh writes (Been here already) for one
    (user, place) both succeed and leave exactly one row.

    Repeated because the first round on cold connections rarely overlaps; the
    pre-fix SELECT-then-INSERT failed with a primary-key IntegrityError in
    nearly every later round.
    """
    from app.places.service import upsert_user_place_state

    setup_user, _, _, place_id = concurrent_setup

    for _ in range(_RACE_ROUNDS):
        await _clear_place_states(committing_factory, setup_user)
        barrier = asyncio.Barrier(2)

        async def attempt(barrier: asyncio.Barrier) -> bool:
            async with committing_factory() as session:
                await barrier.wait()
                row = await upsert_user_place_state(
                    session, setup_user, place_id, "visited", "been_here", visited_before_nosh=True
                )
                await session.commit()
                return row.was_visited_before_nosh

        flags = await asyncio.gather(attempt(barrier), attempt(barrier))
        assert flags == [True, True]

        rows = await _place_state_rows(committing_factory, setup_user, place_id)
        assert len(rows) == 1
        assert rows[0].was_visited_before_nosh is True


@pytest.mark.integration
async def test_concurrent_been_here_and_confirmation_keep_provenance(
    concurrent_setup, committing_factory
) -> None:
    """A pre-Nosh write racing a confirmation write for the same new
    (user, place): both succeed and pre-Nosh provenance survives either order."""
    from app.places.service import upsert_user_place_state

    setup_user, _, _, place_id = concurrent_setup

    for _ in range(_RACE_ROUNDS):
        await _clear_place_states(committing_factory, setup_user)
        barrier = asyncio.Barrier(2)

        async def been_here(barrier: asyncio.Barrier) -> None:
            async with committing_factory() as session:
                await barrier.wait()
                await upsert_user_place_state(
                    session, setup_user, place_id, "visited", "been_here", visited_before_nosh=True
                )
                await session.commit()

        async def confirmation(barrier: asyncio.Barrier) -> None:
            async with committing_factory() as session:
                await barrier.wait()
                await upsert_user_place_state(
                    session, setup_user, place_id, "visited", "confirmation"
                )
                await session.commit()

        await asyncio.gather(been_here(barrier), confirmation(barrier))

        rows = await _place_state_rows(committing_factory, setup_user, place_id)
        assert len(rows) == 1
        assert rows[0].state == "visited"
        assert rows[0].was_visited_before_nosh is True
