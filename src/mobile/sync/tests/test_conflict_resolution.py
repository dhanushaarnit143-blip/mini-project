"""
Tests for MPF Mobile Extension — Conflict Resolution Module (Phase 13)

Validates:
1. Authoritative "Server Wins" policy:
   - When local queue payload differs from existing server record, server record takes precedence.
2. Conflict detection and divergent field extraction:
   - Accurately enumerates fields that diverge between client and server.
3. Audit logging of conflict events:
   - Emits structured metadata documenting resolution strategy and divergent properties.
4. Non-conflicting idempotent matches:
   - Records with matching metrics are flagged as idempotent matches without conflict.
5. Concurrent race condition recovery:
   - Recovers from unique constraint errors by re-fetching and applying server-wins policy.
6. Strict non-diagnostic safety verification.

ALL test data is clearly labeled [SYNTHETIC].
"""

import json
import uuid
import pytest
from pathlib import Path

from src.mobile.sync.sync_bridge import (
    PythonConflictResolver,
    run_node_eval,
)

SYNC_DIR = Path(__file__).resolve().parents[1]
JS_CONFLICT = SYNC_DIR / "conflictResolver.js"

DISALLOWED_TERMS = [
    "you have parkinson's",
    "parkinson's detected",
    "disease progression",
    "clinical deterioration",
]


def test_server_wins_divergent_fields_node():
    """Verify that divergent fields resolve in favor of the server (Server Wins) [SYNTHETIC]."""
    participant_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    js_code = f"""
    const {{ ConflictResolver }} = require({json.dumps(str(JS_CONFLICT))});

    const resolver = new ConflictResolver({{ strategy: 'server_wins' }});

    const serverRecord = {{
      session_id: {json.dumps(session_id)},
      participant_id: {json.dumps(participant_id)},
      blink_rate: 18.2,
      gaze_stability: 0.94,
      quality_score: 0.92,
      synced: true,
    }};

    const localPayload = {{
      session_id: {json.dumps(session_id)},
      participant_id: {json.dumps(participant_id)},
      blink_rate: 22.0,      // Divergent
      gaze_stability: 0.94,  // Identical
      quality_score: 0.85,   // Divergent
    }};

    const result = resolver.resolve(localPayload, serverRecord);

    console.log(JSON.stringify(result));
    """
    res = run_node_eval(js_code)

    assert res["conflict"] is True
    assert res["resolution"] == "server_wins"
    # Server values must be authoritative
    assert res["resolvedRecord"]["blink_rate"] == 18.2
    assert res["resolvedRecord"]["quality_score"] == 0.92
    assert "blink_rate" in res["differences"]
    assert "quality_score" in res["differences"]
    assert "gaze_stability" not in res["differences"]


def test_server_wins_python_resolver():
    """Verify PythonConflictResolver implements server_wins identically [SYNTHETIC]."""
    resolver = PythonConflictResolver()

    local_rec = {
        "session_id": "sess-1",
        "typing_speed": 55.0,
        "pause_rate": 0.08
    }
    server_rec = {
        "session_id": "sess-1",
        "typing_speed": 48.0,
        "pause_rate": 0.08,
        "synced": True
    }

    res = resolver.resolve(local_rec, server_rec)
    assert res["conflict"] is True
    assert res["resolution"] == "server_wins"
    assert res["resolved_record"]["typing_speed"] == 48.0
    assert "typing_speed" in res["differences"]


def test_idempotent_match_no_conflict():
    """Verify identical records produce clean idempotent match without conflict flag [SYNTHETIC]."""
    resolver = PythonConflictResolver()

    local_rec = {
        "session_id": "sess-match",
        "stride_variability": 0.04,
        "cadence": 112.0
    }
    server_rec = {
        "session_id": "sess-match",
        "stride_variability": 0.04,
        "cadence": 112.0,
        "synced": True
    }

    res = resolver.resolve(local_rec, server_rec)
    assert res["conflict"] is False
    assert res["resolution"] == "idempotent_match"
    assert len(res["differences"]) == 0


def test_conflict_resolver_race_condition_handling():
    """Verify ConflictResolver recovers from PostgreSQL 23505 concurrent insert conflict [SYNTHETIC]."""
    participant_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    js_code = f"""
    const {{ ConflictResolver }} = require({json.dumps(str(JS_CONFLICT))});

    (async () => {{
      const resolver = new ConflictResolver();

      const existingRecordOnServer = {{
        id: 'server-row-concurrent',
        session_id: {json.dumps(session_id)},
        participant_id: {json.dumps(participant_id)},
        score: 82,
        synced: true,
      }};

      // Simulate a client that sees no existing record on pre-check,
      // but fails on insert with 23505 duplicate key error due to concurrent worker.
      let checkCalled = false;
      const mockSupabase = {{
        from: (table) => ({{
          select: () => ({{
            eq: () => ({{
              maybeSingle: async () => ({{ data: null, error: null }}),
              single: async () => ({{ data: existingRecordOnServer, error: null }})
            }})
          }}),
          insert: () => ({{
            select: () => ({{
              single: async () => {{
                const err = new Error('duplicate key value violates unique constraint');
                err.code = '23505';
                throw err;
              }}
            }})
          }})
        }})
      }};

      const syncResult = await resolver.syncRecord(mockSupabase, 'sleep_sessions', {{
        session_id: {json.dumps(session_id)},
        participant_id: {json.dumps(participant_id)},
        score: 85, // slightly different local score
      }});

      console.log(JSON.stringify(syncResult));
    }})();
    """
    res = run_node_eval(js_code)

    assert res["success"] is True
    assert res["resolution"] == "server_wins"
    assert res["conflict"] is True
    assert res["data"]["score"] == 82
    assert res["data"]["id"] == "server-row-concurrent"


def test_conflict_resolver_safety():
    """Verify conflict resolver contains zero clinical diagnostic terms."""
    with open(JS_CONFLICT, "r", encoding="utf-8") as f:
        content = f.read().lower()

    for disallowed in DISALLOWED_TERMS:
        assert disallowed not in content
