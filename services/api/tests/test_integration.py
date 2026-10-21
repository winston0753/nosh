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


async def _make_context(client: AsyncClient, headers: dict | None = None) -> dict:
    resp = await client.post(
        "/v1/contexts",
        json={
            "name": "Test Dinner",
            "meal_type": "dinner",
            "longitude": -122.419,
            "latitude": 37.759,
            "radius_meters": 5000,
            "local_window_start": "18:00",
            "local_window_end": "21:00",
            "time_zone": "America/Los_Angeles",
            "active_days": [0, 1, 2, 3, 4, 5, 6],
        },
        headers=headers or _AUTH,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_session_and_go(
    client: AsyncClient,
    ctx: dict,
    window_key: str = "2026-10-12#dinner",
    headers: dict | None = None,
) -> tuple[dict, dict, dict]:
    """Create a suggestion session, record a Go response, and return
    (session, proposal, go_response)."""
    h = headers or _AUTH
    sess_resp = await client.post(
        "/v1/suggestion-sessions",
        json={"dining_context_id": ctx["id"], "meal_window_key": window_key},
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
# Context CRUD and authorization
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_create_and_list_contexts(client):
    ctx = await _make_context(client)
    assert ctx["meal_type"] == "dinner"
    assert ctx["radius_meters"] == 5000

    resp = await client.get("/v1/contexts", headers=_AUTH)
    assert resp.status_code == 200
    assert ctx["id"] in [c["id"] for c in resp.json()]


@pytest.mark.integration
async def test_cross_user_context_forbidden(client):
    ctx = await _make_context(client)
    resp = await client.patch(
        f"/v1/contexts/{ctx['id']}",
        json={"name": "Hacked"},
        headers=_AUTH2,
    )
    assert resp.status_code in (403, 404)


# ---------------------------------------------------------------------------
# Full suggestion flow
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_suggestion_go_accepted(client, db):
    await _seed_fixtures(db)
    ctx = await _make_context(client)
    _, _, go = await _create_session_and_go(client, ctx)
    assert go["response"] == "go"
    assert go["session_state"] == "accepted"


@pytest.mark.integration
async def test_suggestion_another_next_distinct_proposal(client, db):
    await _seed_fixtures(db)
    ctx = await _make_context(client)

    resp = await client.post(
        "/v1/suggestion-sessions",
        json={"dining_context_id": ctx["id"], "meal_window_key": "2026-10-12#dinner"},
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
    ctx = await _make_context(client)

    resp = await client.post(
        "/v1/suggestion-sessions",
        json={"dining_context_id": ctx["id"], "meal_window_key": "2026-10-12#dinner"},
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
    ctx = await _make_context(client)

    resp = await client.post(
        "/v1/suggestion-sessions",
        json={"dining_context_id": ctx["id"], "meal_window_key": "2026-10-12#dinner"},
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
    ctx = await _make_context(client)

    resp = await client.post(
        "/v1/suggestion-sessions",
        json={"dining_context_id": ctx["id"], "meal_window_key": "2026-10-12#dinner"},
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
    ctx = await _make_context(client)

    resp = await client.post(
        "/v1/suggestion-sessions",
        json={"dining_context_id": ctx["id"], "meal_window_key": "2026-10-12#dinner"},
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
    ctx = await _make_context(client)

    resp = await client.post(
        "/v1/suggestion-sessions",
        json={"dining_context_id": ctx["id"], "meal_window_key": "2026-10-12#dinner"},
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
    ctx = await _make_context(client)
    resp = await client.post(
        "/v1/suggestion-sessions",
        json={"dining_context_id": ctx["id"], "meal_window_key": "2026-10-12#dinner"},
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
    ctx = await _make_context(client)
    key = "2026-10-12#dinner"

    r1 = await client.post(
        "/v1/suggestion-sessions",
        json={"dining_context_id": ctx["id"], "meal_window_key": key},
        headers=_AUTH,
    )
    r2 = await client.post(
        "/v1/suggestion-sessions",
        json={"dining_context_id": ctx["id"], "meal_window_key": key},
        headers=_AUTH,
    )
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]


@pytest.mark.integration
async def test_exhaustion_state_after_all_another(client, db):
    """Repeated Another returns no_candidates when all places exhausted."""
    await _seed_fixtures(db)
    resp = await client.post(
        "/v1/contexts",
        json={
            "name": "Tiny radius",
            "meal_type": "dinner",
            "longitude": -122.419,
            "latitude": 37.759,
            "radius_meters": 100,
            "local_window_start": "18:00",
            "local_window_end": "21:00",
            "time_zone": "America/Los_Angeles",
            "active_days": [0, 1, 2, 3, 4, 5, 6],
        },
        headers=_AUTH,
    )
    assert resp.status_code == 201, resp.text
    ctx = resp.json()

    resp2 = await client.post(
        "/v1/suggestion-sessions",
        json={"dining_context_id": ctx["id"], "meal_window_key": "2026-10-12#dinner"},
        headers=_AUTH,
    )
    session = resp2.json()
    if session["state"] == "no_candidates":
        return

    final_state = session["state"]
    proposal = session.get("current_proposal")
    seq = 0
    while proposal and final_state == "active" and seq < 30:
        seq += 1
        r = await client.post(
            f"/v1/proposals/{proposal['id']}/responses",
            json={"response": "another", "client_event_id": f"exhaust-{seq}-{uuid.uuid4()}"},
            headers=_AUTH,
        )
        data = r.json()
        final_state = data["session_state"]
        proposal = data.get("next_proposal")
        if data.get("no_candidates"):
            break

    assert final_state in ("exhausted", "no_candidates")


# ---------------------------------------------------------------------------
# Visit confirmation — requires Go on the exact proposal
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_visit_confirmation_and_progress(client, db):
    await _seed_fixtures(db)
    ctx = await _make_context(client)

    # Must record Go before confirming a visit.
    session, proposal, _ = await _create_session_and_go(client, ctx)

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
    ctx = await _make_context(client)

    sess_resp = await client.post(
        "/v1/suggestion-sessions",
        json={"dining_context_id": ctx["id"], "meal_window_key": "2026-10-12#dinner"},
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
    ctx = await _make_context(client)
    session, proposal, _ = await _create_session_and_go(client, ctx)

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
    ctx = await _make_context(client)
    # User 1 records Go.
    session, proposal, _ = await _create_session_and_go(client, ctx)

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
    ctx = await _make_context(client)
    session, proposal, _ = await _create_session_and_go(client, ctx)

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
    ctx = await _make_context(client)
    _, proposal1, _ = await _create_session_and_go(client, ctx, window_key="2026-10-12#dinner")

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
async def test_progress_excludes_pre_nosh_onboarding_place(client, db):
    """A place marked 'Been' during onboarding does not count as a new Nosh discovery."""
    await _seed_fixtures(db)
    ctx = await _make_context(client)

    # Mark the first onboarding place as 'Been'.
    ob = await client.get(f"/v1/contexts/{ctx['id']}/onboarding-places", headers=_AUTH)
    assert ob.status_code == 200, ob.text
    pre_nosh_place_id = ob.json()[0]["place"]["id"]
    classified = await client.put(
        f"/v1/contexts/{ctx['id']}/onboarding-places/{pre_nosh_place_id}/state",
        json={"state": "visited"},
        headers=_AUTH,
    )
    assert classified.status_code == 200, classified.text

    # Get a session that proposes a different restaurant (not the pre-Nosh one).
    sess_resp = await client.post(
        "/v1/suggestion-sessions",
        json={"dining_context_id": ctx["id"], "meal_window_key": "2026-10-12#dinner"},
        headers=_AUTH,
    )
    assert sess_resp.status_code == 201, sess_resp.text
    session = sess_resp.json()
    assert session["current_proposal"] is not None
    proposal = session["current_proposal"]

    # If the proposed place happens to be the pre-Nosh place (unlikely given 20
    # fixtures but possible), skip this test variant gracefully.
    if proposal["place_id"] == pre_nosh_place_id:
        pytest.skip("Proposed place is the pre-Nosh place; need a different proposal")

    # Record Go and confirm the visit.
    go_resp = await client.post(
        f"/v1/proposals/{proposal['id']}/responses",
        json={"response": "go", "client_event_id": f"go-{uuid.uuid4()}"},
        headers=_AUTH,
    )
    assert go_resp.status_code == 201

    await client.post(
        "/v1/visits",
        json={
            "place_id": proposal["place_id"],
            "proposal_id": proposal["id"],
            "visited_at": "2026-10-12T19:00:00Z",
            "rating": "positive",
        },
        headers=_AUTH,
    )

    prog = await client.get("/v1/progress", headers=_AUTH)
    assert prog.status_code == 200
    # This visit IS a new Nosh discovery (not the pre-Nosh place).
    total_new = sum(m["confirmed_positive_new_count"] for m in prog.json())
    assert total_new == 1


# ---------------------------------------------------------------------------
# Exclusion invariants
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_visited_place_excluded_from_next_session(client, db):
    """A confirmed visited place does not appear in a subsequent session."""
    await _seed_fixtures(db)
    ctx = await _make_context(client)

    # Must record Go before confirming a visit.
    session, proposal, _ = await _create_session_and_go(client, ctx)
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
        json={"dining_context_id": ctx["id"], "meal_window_key": "2026-10-13#dinner"},
        headers=_AUTH,
    )
    session2 = resp2.json()
    if session2.get("current_proposal"):
        assert session2["current_proposal"]["place_id"] != place_id


@pytest.mark.integration
async def test_not_interested_place_excluded(client, db):
    await _seed_fixtures(db)
    ctx = await _make_context(client)

    ob = await client.get(f"/v1/contexts/{ctx['id']}/onboarding-places", headers=_AUTH)
    assert ob.status_code == 200
    places = ob.json()
    assert len(places) > 0
    place_id = places[0]["place"]["id"]

    await client.put(
        f"/v1/places/{place_id}/state",
        json={"state": "not_interested"},
        headers=_AUTH,
    )

    resp = await client.post(
        "/v1/suggestion-sessions",
        json={"dining_context_id": ctx["id"], "meal_window_key": "2026-10-12#dinner"},
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
async def test_product_data_deletion_removes_contexts(client, db):
    """DELETE /v1/me/product-data removes all owned Nosh data.

    This endpoint removes product data only — the Supabase Auth identity
    is separate and requires a service-role credential (deferred).
    """
    await _seed_fixtures(db)
    ctx = await _make_context(client)

    # Create a session and confirm a visit so there's data to delete.
    _, proposal, _ = await _create_session_and_go(client, ctx)
    await client.post(
        "/v1/visits",
        json={
            "place_id": proposal["place_id"],
            "proposal_id": proposal["id"],
            "visited_at": "2026-10-12T19:00:00Z",
            "rating": "positive",
        },
        headers=_AUTH,
    )

    del_resp = await client.delete("/v1/me/product-data", headers=_AUTH)
    assert del_resp.status_code == 204, del_resp.text

    # Contexts must be gone.
    ctx_resp = await client.get("/v1/contexts", headers=_AUTH)
    assert ctx_resp.status_code == 200, ctx_resp.text
    assert ctx_resp.json() == []

    # Visit history must be gone.
    visits_resp = await client.get("/v1/visits", headers=_AUTH)
    assert visits_resp.status_code == 200, visits_resp.text
    assert visits_resp.json() == []


# ---------------------------------------------------------------------------
# Session key format
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_session_key_format_accepted(client, db):
    """Keys whose meal type matches the context are accepted for any real date."""
    await _seed_fixtures(db)
    for meal in ("lunch", "dinner", "brunch"):
        resp = await client.post(
            "/v1/contexts",
            json={
                "name": f"Test {meal}",
                "meal_type": meal,
                "longitude": -122.419,
                "latitude": 37.759,
                "radius_meters": 5000,
                "local_window_start": "11:00",
                "local_window_end": "14:00",
                "time_zone": "America/Los_Angeles",
                "active_days": [0, 1, 2, 3, 4, 5, 6],
            },
            headers=_AUTH,
        )
        assert resp.status_code == 201, resp.text
        ctx = resp.json()
        for date in ("2026-01-01", "2026-12-31", "2028-02-29"):
            key = f"{date}#{meal}"
            resp = await client.post(
                "/v1/suggestion-sessions",
                json={"dining_context_id": ctx["id"], "meal_window_key": key},
                headers=_AUTH,
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

    from app.contexts.models import DiningContext
    from app.places.models import UserPlaceState
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
            delete(DiningContext).where(DiningContext.user_id == _CONCURRENT_USER_ID)
        )
        await cleanup_db.commit()


@pytest_asyncio.fixture
async def concurrent_setup(engine, committing_factory):
    """Seed fixtures and create a context+session once for concurrent tests.

    Returns (context_id, session_id, proposal_id, place_id).
    Rows for the concurrent-test user are purged before setup (recovering from
    any interrupted earlier run) and again after the test, even on failure.
    """
    from app.contexts.models import DiningContext
    from app.places.service import load_fixture_data

    setup_user = _CONCURRENT_USER_ID
    await _purge_concurrent_user(committing_factory)

    async with committing_factory() as setup_db:
        await load_fixture_data(setup_db)

        ctx = DiningContext(
            user_id=setup_user,
            name="Concurrent Test",
            meal_type="dinner",
            location="SRID=4326;POINT(-122.419 37.759)",
            radius_meters=5000,
            local_window_start="18:00",
            local_window_end="21:00",
            time_zone="America/Los_Angeles",
            active_days=[0, 1, 2, 3, 4, 5, 6],
        )
        setup_db.add(ctx)
        await setup_db.flush()

        from app.suggestions.service import get_or_create_session

        session = await get_or_create_session(setup_db, setup_user, ctx.id, "2026-11-01#dinner")
        await setup_db.commit()

        proposal_id = session.proposals[0].id
        place_id = session.proposals[0].place_id
        session_id = session.id
        context_id = ctx.id

    yield setup_user, context_id, session_id, proposal_id, place_id

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

    setup_user, _, _, proposal_id, _ = concurrent_setup
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

    setup_user, _, session_id, proposal_id, _ = concurrent_setup

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

    setup_user, _, _, proposal_id, place_id = concurrent_setup

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
    """Two simultaneous session creations for the same (context, window):
    - both callers must receive the same session ID
    - exactly one SuggestionSession row must exist

    The DiningContext FOR UPDATE lock in get_or_create_session serialises the
    two inserts so one wins and the other re-reads the winner's session.
    """
    from sqlalchemy import select

    from app.suggestions.models import SuggestionSession
    from app.suggestions.service import get_or_create_session

    setup_user, context_id, _, _, _ = concurrent_setup
    window_key = "2026-11-02#dinner"  # distinct from the one created in setup

    barrier = asyncio.Barrier(2)

    async def attempt_session() -> str:
        async with committing_factory() as db_session:
            await barrier.wait()
            s = await get_or_create_session(db_session, setup_user, context_id, window_key)
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
                        SuggestionSession.dining_context_id == context_id,
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


async def _new_session(client: AsyncClient, ctx: dict, key: str, headers: dict) -> dict:
    resp = await client.post(
        "/v1/suggestion-sessions",
        json={"dining_context_id": ctx["id"], "meal_window_key": key},
        headers=headers,
    )
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
# Onboarding provenance
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_onboarding_been_then_nosh_visit_same_place_excluded_from_north_star(client, db):
    """The SAME restaurant: proposed by Nosh, classified Been during (resumed)
    onboarding, then accepted with Go and confirmed positive.  It must stay
    pre-Nosh and never count toward confirmed positive NEW restaurants."""
    await _seed_fixtures(db)
    uid, auth = _fresh_user()
    ctx = await _make_context(client, headers=auth)

    proposal = (await _new_session(client, ctx, "2026-10-12#dinner", auth))["current_proposal"]
    place_id = proposal["place_id"]

    classified = await client.put(
        f"/v1/contexts/{ctx['id']}/onboarding-places/{place_id}/state",
        json={"state": "visited"},
        headers=auth,
    )
    assert classified.status_code == 200, classified.text
    assert classified.json() == {
        "place_id": place_id,
        "state": "visited",
        "source": "onboarding",
        "was_visited_before_nosh": True,
    }

    await _go_and_confirm(client, proposal, "positive", auth)

    row = await _place_state(db, uid, place_id)
    assert row is not None
    assert row.state == "visited"
    assert row.source == "confirmation"
    assert row.was_visited_before_nosh is True, "confirmation must not erase provenance"

    progress = (await client.get("/v1/progress", headers=auth)).json()
    assert progress == [
        {"month": "2026-10", "confirmed_positive_new_count": 0, "total_confirmed_count": 1}
    ]


@pytest.mark.integration
async def test_onboarding_provenance_survives_reclassification_and_manual_edits(client, db):
    await _seed_fixtures(db)
    uid, auth = _fresh_user()
    ctx = await _make_context(client, headers=auth)
    place_id = (
        await client.get(f"/v1/contexts/{ctx['id']}/onboarding-places", headers=auth)
    ).json()[0]["place"]["id"]
    url = f"/v1/contexts/{ctx['id']}/onboarding-places/{place_id}/state"

    assert (await client.put(url, json={"state": "visited"}, headers=auth)).status_code == 200
    for state in ("unknown", "not_interested"):
        r = await client.put(url, json={"state": state}, headers=auth)
        assert r.status_code == 200, r.text
        assert r.json()["was_visited_before_nosh"] is True
    manual = await client.put(
        f"/v1/places/{place_id}/state", json={"state": "unknown"}, headers=auth
    )
    assert manual.status_code == 200, manual.text
    assert manual.json()["source"] == "manual"
    assert manual.json()["was_visited_before_nosh"] is True

    # A later manual-logged positive visit to that place is still not "new".
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
    progress = (await client.get("/v1/progress", headers=auth)).json()
    assert sum(m["confirmed_positive_new_count"] for m in progress) == 0


@pytest.mark.integration
async def test_manual_place_state_never_marks_pre_nosh(client, db):
    await _seed_fixtures(db)
    uid, auth = _fresh_user()
    ctx = await _make_context(client, headers=auth)
    proposal = (await _new_session(client, ctx, "2026-10-12#dinner", auth))["current_proposal"]

    manual = await client.put(
        f"/v1/places/{proposal['place_id']}/state", json={"state": "visited"}, headers=auth
    )
    assert manual.status_code == 200, manual.text
    assert manual.json()["source"] == "manual"
    assert manual.json()["was_visited_before_nosh"] is False


@pytest.mark.integration
async def test_onboarding_classification_negative_paths(client, db):
    await _seed_fixtures(db)
    uid, auth = _fresh_user()
    _, other_auth = _fresh_user()
    ctx = await _make_context(client, headers=auth)
    place_id = (
        await client.get(f"/v1/contexts/{ctx['id']}/onboarding-places", headers=auth)
    ).json()[0]["place"]["id"]

    # Nonexistent place → stable 404.
    r = await client.put(
        f"/v1/contexts/{ctx['id']}/onboarding-places/{uuid.uuid4()}/state",
        json={"state": "visited"},
        headers=auth,
    )
    assert r.status_code == 404 and r.json()["code"] == "not_found", r.text

    # Nonexistent context → 404; another user's context → 403.
    r = await client.put(
        f"/v1/contexts/{uuid.uuid4()}/onboarding-places/{place_id}/state",
        json={"state": "visited"},
        headers=auth,
    )
    assert r.status_code == 404 and r.json()["code"] == "not_found", r.text
    r = await client.put(
        f"/v1/contexts/{ctx['id']}/onboarding-places/{place_id}/state",
        json={"state": "visited"},
        headers=other_auth,
    )
    assert r.status_code == 403 and r.json()["code"] == "forbidden", r.text

    # A place that onboarding would never present for this context → 422.
    far = await client.post(
        "/v1/contexts",
        json={
            "name": "Far away",
            "meal_type": "dinner",
            "longitude": -73.98,
            "latitude": 40.75,
            "radius_meters": 500,
            "local_window_start": "18:00",
            "local_window_end": "21:00",
            "time_zone": "America/New_York",
        },
        headers=auth,
    )
    assert far.status_code == 201, far.text
    r = await client.put(
        f"/v1/contexts/{far.json()['id']}/onboarding-places/{place_id}/state",
        json={"state": "visited"},
        headers=auth,
    )
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "place_not_in_context"
    assert await _place_state(db, uid, place_id) is None

    # Invalid state value → schema validation error.
    r = await client.put(
        f"/v1/contexts/{ctx['id']}/onboarding-places/{place_id}/state",
        json={"state": "loved_it"},
        headers=auth,
    )
    assert r.status_code == 422 and r.json()["code"] == "validation_error", r.text


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
async def test_cuisine_stats_without_onboarding_history_are_neutral(client, db):
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
async def test_cuisine_stats_history_only_from_onboarding_and_outcomes_only_from_proposals(
    client, db
):
    from app.suggestions.service import _load_cuisine_stats

    await _seed_fixtures(db)
    uid, auth = _fresh_user()
    ctx = await _make_context(client, headers=auth)

    # 1. Pre-Nosh history: one onboarding Been.
    onboarding = (
        await client.get(f"/v1/contexts/{ctx['id']}/onboarding-places", headers=auth)
    ).json()
    been_id = onboarding[0]["place"]["id"]
    r = await client.put(
        f"/v1/contexts/{ctx['id']}/onboarding-places/{been_id}/state",
        json={"state": "visited"},
        headers=auth,
    )
    assert r.status_code == 200, r.text
    been_cuisine = await _primary_cuisine(db, been_id)

    stats = await _load_cuisine_stats(db, uid)
    assert stats[been_cuisine].history_frequency == 1.0
    assert all(s.history_frequency == 0.0 for c, s in stats.items() if c != been_cuisine)
    assert all(
        s.confirmed_positive_visits == 0 and s.confirmed_negative_visits == 0
        for s in stats.values()
    )

    # 2. Later Nosh visits: one positive, one negative.
    p1 = (await _new_session(client, ctx, "2026-10-12#dinner", auth))["current_proposal"]
    await _go_and_confirm(client, p1, "positive", auth)
    p2 = (await _new_session(client, ctx, "2026-10-13#dinner", auth))["current_proposal"]
    await _go_and_confirm(client, p2, "negative", auth)
    assert len({been_id, p1["place_id"], p2["place_id"]}) == 3

    # 3. A manual visit (no proposal) must not update cuisine preference (D015).
    manual_place = next(
        p["place"]["id"]
        for p in onboarding
        if p["place"]["id"] not in {been_id, p1["place_id"], p2["place_id"]}
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
    # History is unchanged: post-Nosh visits are never onboarding history.
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
# Dining-context and meal-window validation (stored-context paths)
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_patch_context_rejects_window_inconsistent_with_stored_bounds(client, db):
    _, auth = _fresh_user()
    ctx = await _make_context(client, headers=auth)  # 18:00–21:00
    url = f"/v1/contexts/{ctx['id']}"

    for body in (
        {"local_window_end": "17:00"},
        {"local_window_start": "21:30"},
        {"local_window_start": "21:00"},
        {"local_window_start": "22:00", "local_window_end": "02:00"},
    ):
        r = await client.patch(url, json=body, headers=auth)
        assert r.status_code == 422, (body, r.text)
        assert r.json()["code"] == "validation_error"
        assert r.json()["field"] == "local_window_end"

    unchanged = next(
        c for c in (await client.get("/v1/contexts", headers=auth)).json() if c["id"] == ctx["id"]
    )
    assert unchanged["version"] == ctx["version"]
    assert (unchanged["local_window_start"], unchanged["local_window_end"]) == ("18:00", "21:00")

    ok = await client.patch(url, json={"local_window_start": "17:00"}, headers=auth)
    assert ok.status_code == 200, ok.text
    assert ok.json()["version"] == ctx["version"] + 1


@pytest.mark.integration
async def test_session_key_must_match_context(client, db):
    await _seed_fixtures(db)
    _, auth = _fresh_user()
    resp = await client.post(
        "/v1/contexts",
        json={
            "name": "Weekday dinner",
            "meal_type": "dinner",
            "longitude": -122.419,
            "latitude": 37.759,
            "radius_meters": 5000,
            "local_window_start": "18:00",
            "local_window_end": "21:00",
            "time_zone": "America/Los_Angeles",
            "active_days": [0, 1, 2, 3, 4],
        },
        headers=auth,
    )
    assert resp.status_code == 201, resp.text
    ctx = resp.json()

    for key in (
        "2026-10-12#lunch",  # meal type mismatch (Monday)
        "2026-10-12#brunch",  # meal type mismatch
        "2026-10-11#dinner",  # Sunday: inactive day
        "2026-10-17#dinner",  # Saturday: inactive day
        "2026-02-30#dinner",  # impossible date
        "2026-00-10#dinner",  # impossible month
    ):
        r = await client.post(
            "/v1/suggestion-sessions",
            json={"dining_context_id": ctx["id"], "meal_window_key": key},
            headers=auth,
        )
        assert r.status_code == 422, (key, r.text)
        assert r.json()["code"] == "validation_error"
        assert r.json()["field"] == "meal_window_key"

    ok = await client.post(
        "/v1/suggestion-sessions",
        json={"dining_context_id": ctx["id"], "meal_window_key": "2026-10-12#dinner"},
        headers=auth,
    )
    assert ok.status_code == 201, ok.text


@pytest.mark.integration
async def test_session_rejected_for_legacy_context_with_invalid_schedule(client, db):
    """Rows written before strict validation cannot open a suggestion session."""
    from app.contexts.models import DiningContext

    uid, auth = _fresh_user()
    for tz, start, end in (
        ("Not/AZone", "18:00", "21:00"),
        ("America/Los_Angeles", "22:00", "02:00"),
        ("America/Los_Angeles", "25:99", "26:00"),
    ):
        legacy = DiningContext(
            user_id=uid,
            name="Legacy",
            meal_type="dinner",
            location="SRID=4326;POINT(-122.419 37.759)",
            radius_meters=1600,
            local_window_start=start,
            local_window_end=end,
            time_zone=tz,
            active_days=[0, 1, 2, 3, 4, 5, 6],
        )
        db.add(legacy)
        await db.flush()
        r = await client.post(
            "/v1/suggestion-sessions",
            json={"dining_context_id": str(legacy.id), "meal_window_key": "2026-10-12#dinner"},
            headers=auth,
        )
        assert r.status_code == 422, (tz, start, end, r.text)
        assert r.json()["code"] == "validation_error"


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
    ctx = await _make_context(client, headers=auth)
    created = await _new_session(client, ctx, "2026-10-12#dinner", auth)
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
    ctx = await _make_context(client, headers=auth)
    proposal = (await _new_session(client, ctx, "2026-10-12#dinner", auth))["current_proposal"]

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
    ctx = await _make_context(client, headers=auth)
    first = (await _new_session(client, ctx, "2026-10-12#dinner", auth))["current_proposal"]
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
async def test_concurrent_first_onboarding_classification_atomic(
    concurrent_setup, committing_factory
) -> None:
    """Two simultaneous first-time onboarding writes for one (user, place) both
    succeed and leave exactly one row.

    Repeated because the first round on cold connections rarely overlaps; the
    pre-fix SELECT-then-INSERT failed with a primary-key IntegrityError in
    nearly every later round.
    """
    from app.places.service import classify_onboarding_place

    setup_user, context_id, _, _, place_id = concurrent_setup

    for _ in range(_RACE_ROUNDS):
        await _clear_place_states(committing_factory, setup_user)
        barrier = asyncio.Barrier(2)

        async def attempt(barrier: asyncio.Barrier) -> bool:
            async with committing_factory() as session:
                await barrier.wait()
                row = await classify_onboarding_place(
                    session, setup_user, context_id, place_id, "visited"
                )
                return row.was_visited_before_nosh

        flags = await asyncio.gather(attempt(barrier), attempt(barrier))
        assert flags == [True, True]

        rows = await _place_state_rows(committing_factory, setup_user, place_id)
        assert len(rows) == 1
        assert rows[0].was_visited_before_nosh is True


@pytest.mark.integration
async def test_concurrent_onboarding_and_confirmation_keep_provenance(
    concurrent_setup, committing_factory
) -> None:
    """An onboarding Been racing a confirmation write for the same new
    (user, place): both succeed and pre-Nosh provenance survives either order."""
    from app.places.service import classify_onboarding_place, upsert_user_place_state

    setup_user, context_id, _, _, place_id = concurrent_setup

    for _ in range(_RACE_ROUNDS):
        await _clear_place_states(committing_factory, setup_user)
        barrier = asyncio.Barrier(2)

        async def onboarding(barrier: asyncio.Barrier) -> None:
            async with committing_factory() as session:
                await barrier.wait()
                await classify_onboarding_place(
                    session, setup_user, context_id, place_id, "visited"
                )

        async def confirmation(barrier: asyncio.Barrier) -> None:
            async with committing_factory() as session:
                await barrier.wait()
                await upsert_user_place_state(
                    session, setup_user, place_id, "visited", "confirmation"
                )
                await session.commit()

        await asyncio.gather(onboarding(barrier), confirmation(barrier))

        rows = await _place_state_rows(committing_factory, setup_user, place_id)
        assert len(rows) == 1
        assert rows[0].state == "visited"
        assert rows[0].was_visited_before_nosh is True
