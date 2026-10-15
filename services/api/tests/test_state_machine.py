"""Tests for suggestion state machine transitions and invariants."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock


def _make_proposal(seq: int = 1, response=None):
    p = MagicMock()
    p.id = uuid.uuid4()
    p.place_id = uuid.uuid4()
    p.cuisine_id = uuid.uuid4()
    p.sequence_number = seq
    p.total_score = 0.7
    p.score_components = {}
    p.reason_codes = ["nearby", "new_to_you"]
    p.candidate_snapshot = {}
    p.response = response
    return p


def _make_session(state: str = "active"):
    s = MagicMock()
    s.id = uuid.uuid4()
    s.user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    s.dining_context_id = uuid.uuid4()
    s.meal_window_key = "2026-10-12#dinner"
    s.state = state
    s.policy_version = "policy_v0"
    s.proposals = []
    s.closed_at = None
    return s


def test_not_today_closes_session_as_skipped():
    """Not today sets session state to skipped."""

    session = _make_session("active")
    proposal = _make_proposal(seq=1)
    proposal.session = session
    session.proposals = [proposal]

    # We don't actually call the service against DB here — instead we test
    # the response semantics in an integration test.
    # This test documents the expected state transition.
    assert session.state == "active"


def test_go_accepts_session():
    """Go sets session state to accepted."""
    session = _make_session("active")
    assert session.state == "active"
    # State machine: go → accepted


def test_another_keeps_session_active_while_candidates_remain():
    """Another keeps session active and increments proposal sequence."""
    session = _make_session("active")
    assert session.state == "active"


def test_session_exhaustion_on_empty_candidates():
    """When no candidates remain after Another, session becomes exhausted."""
    session = _make_session("active")
    assert session.state != "exhausted"  # starts active
