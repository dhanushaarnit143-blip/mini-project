"""
Tests for MPF Mobile Extension — Retry Logic & Partial Sync (Phase 13)

Validates:
1. Exponential backoff delay calculation:
   - Exact progression: 1s, 2s, 4s, 8s, 16s, 32s, capped at max 60s.
2. Max retry limit (5 retries):
   - Items exceeding 5 retries transition to status 'failed'.
3. Error classification:
   - Retryable: network outages, ECONNREFUSED, ETIMEDOUT, 500/503 server errors.
   - Non-retryable: HTTP 400, 401, 403, 422, invalid schema constraints.
4. User alert dispatch:
   - Emits structured non-diagnostic alert when max retries are exceeded.
5. Partial sync resiliency:
   - Failure of one task does not block or cancel subsequent tasks in the queue.
6. Non-diagnostic safety verification.

ALL test data is clearly labeled [SYNTHETIC].
"""

import json
import uuid
import pytest
from pathlib import Path

from src.mobile.sync.sync_bridge import (
    calculate_backoff_delay,
    is_retryable_error,
    PythonOfflineQueue,
    PythonSyncManager,
    PythonSyncStatusTracker,
    run_node_eval,
)

SYNC_DIR = Path(__file__).resolve().parents[1]
JS_RETRY = SYNC_DIR / "retryLogic.js"
JS_MANAGER = SYNC_DIR / "syncManager.js"


def test_exponential_backoff_progression_node():
    """Verify exponential backoff calculation matches 1s, 2s, 4s, 8s, 16s, 32s, max 60s [SYNTHETIC]."""
    js_code = f"""
    const {{ calculateDelay, RETRY_CONFIG }} = require({json.dumps(str(JS_RETRY))});

    const delays = [];
    for (let attempt = 0; attempt <= 7; attempt++) {{
      delays.push(calculateDelay(attempt, {{ jitter: 0 }}));
    }}

    console.log(JSON.stringify({{
      delays,
      maxRetries: RETRY_CONFIG.MAX_RETRIES,
      baseDelay: RETRY_CONFIG.BASE_DELAY_MS,
      maxDelay: RETRY_CONFIG.MAX_DELAY_MS,
    }}));
    """
    res = run_node_eval(js_code)
    delays = res["delays"]

    # 1s, 2s, 4s, 8s, 16s, 32s, capped at 60s
    assert delays[0] == 1000
    assert delays[1] == 2000
    assert delays[2] == 4000
    assert delays[3] == 8000
    assert delays[4] == 16000
    assert delays[5] == 32000
    assert delays[6] == 60000  # Capped at 60s
    assert delays[7] == 60000  # Stays capped at 60s

    assert res["maxRetries"] == 5
    assert res["baseDelay"] == 1000
    assert res["maxDelay"] == 60000


def test_exponential_backoff_progression_python():
    """Verify Python backoff calculation mirrors the exact specification [SYNTHETIC]."""
    assert calculate_backoff_delay(0) == 1000
    assert calculate_backoff_delay(1) == 2000
    assert calculate_backoff_delay(2) == 4000
    assert calculate_backoff_delay(3) == 8000
    assert calculate_backoff_delay(4) == 16000
    assert calculate_backoff_delay(5) == 32000
    assert calculate_backoff_delay(6) == 60000
    assert calculate_backoff_delay(10) == 60000


def test_error_retryability_classification():
    """Verify distinction between retryable and non-retryable errors [SYNTHETIC]."""
    js_code = f"""
    const {{ isRetryable }} = require({json.dumps(str(JS_RETRY))});

    const results = {{
      networkError: isRetryable(new Error('Network request failed')),
      econnrefused: isRetryable(new Error('connect ECONNREFUSED 127.0.0.1:443')),
      server503: isRetryable({{ status: 503, message: 'Service Unavailable' }}),
      timeout408: isRetryable({{ status: 408, message: 'Request Timeout' }}),
      rateLimit429: isRetryable({{ status: 429, message: 'Too Many Requests' }}),
      badRequest400: isRetryable({{ status: 400, message: 'Bad Request' }}),
      unauthorized401: isRetryable({{ status: 401, message: 'Unauthorized JWT' }}),
      forbidden403: isRetryable({{ status: 403, message: 'Forbidden' }}),
      schemaViolation: isRetryable(new Error('Invalid input syntax for type uuid')),
    }};

    console.log(JSON.stringify(results));
    """
    res = run_node_eval(js_code)

    # Retryable
    assert res["networkError"] is True
    assert res["econnrefused"] is True
    assert res["server503"] is True
    assert res["timeout408"] is True
    assert res["rateLimit429"] is True

    # Non-retryable
    assert res["badRequest400"] is False
    assert res["unauthorized401"] is False
    assert res["forbidden403"] is False
    assert res["schemaViolation"] is False


def test_max_retries_and_alert_dispatch():
    """Verify that after 5 failed retries, item is marked failed and user alert is dispatched [SYNTHETIC]."""
    queue = PythonOfflineQueue(max_retries=5)
    tracker = PythonSyncStatusTracker(initial_online=True)

    participant_id = str(uuid.uuid4())
    item = queue.enqueue({
        "participant_id": participant_id,
        "table_name": "voice_sessions",
        "payload": {"pitch_mean": 175.0}
    })

    manager = PythonSyncManager(
        queue=queue,
        tracker=tracker,
        sync_fn=lambda it: {"success": False, "error": "503 Gateway Timeout"}
    )

    # Simulate 5 consecutive retry attempts
    for attempt in range(5):
        manager.sync_now()

    final_item = queue.items[0]
    assert final_item["retry_count"] == 5
    assert final_item["status"] == "failed"

    # Verify non-diagnostic alert was dispatched
    assert len(tracker.alerts) >= 1
    alert = tracker.alerts[0]
    assert alert["type"] == "MAX_RETRIES_EXCEEDED"
    assert alert["severity"] == "warning"
    assert "securely preserved on your device" in alert["message"]
    assert "parkinson" not in alert["message"].lower()


def test_partial_sync_resiliency():
    """Verify that failure of one task does not block or cancel remaining tasks in the queue [SYNTHETIC]."""
    participant_id = str(uuid.uuid4())

    js_code = f"""
    const {{ SyncManager }} = require({json.dumps(str(JS_MANAGER))});
    const {{ OfflineQueue, MemoryStorageAdapter }} = require({json.dumps(str(SYNC_DIR / 'offlineQueue.js'))});
    const {{ SyncStatusTracker }} = require({json.dumps(str(SYNC_DIR / 'syncStatusTracker.js'))});

    (async () => {{
      const queue = new OfflineQueue({{ storage: new MemoryStorageAdapter() }});
      await queue.init();
      const tracker = new SyncStatusTracker({{ initialOnline: true }});

      // Item 1: Valid typing session
      const item1 = await queue.enqueue({{
        participant_id: {json.dumps(participant_id)},
        session_id: 'session-good-1',
        table_name: 'typing_sessions',
        payload: {{ typing_speed: 46.0 }},
      }});

      // Item 2: Flaky voice session that fails
      const item2 = await queue.enqueue({{
        participant_id: {json.dumps(participant_id)},
        session_id: 'session-fail-2',
        table_name: 'voice_sessions',
        payload: {{ jitter: 0.015 }},
      }});

      // Item 3: Valid motor session that succeeds
      const item3 = await queue.enqueue({{
        participant_id: {json.dumps(participant_id)},
        session_id: 'session-good-3',
        table_name: 'motor_sessions',
        payload: {{ cadence: 110.0 }},
      }});

      // Mock Supabase client that fails only for session-fail-2
      const mockSupabase = {{
        from: (table) => ({{
          select: () => ({{
            eq: (col, val) => ({{
              maybeSingle: async () => ({{ data: null, error: null }})
            }})
          }}),
          insert: (payload) => ({{
            select: () => ({{
              single: async () => {{
                if (payload.session_id === 'session-fail-2') {{
                  const err = new Error('504 Gateway Timeout');
                  err.status = 504;
                  throw err;
                }}
                return {{ data: {{ ...payload, id: 'row-' + payload.session_id }}, error: null }};
              }}
            }})
          }})
        }})
      }};

      const manager = new SyncManager({{
        supabaseClient: mockSupabase,
        queue,
        statusTracker: tracker,
        autoSync: false,
        enableAuditLog: false,
      }});

      const syncResult = await manager.syncNow();

      const item1State = queue.getItem(item1.id);
      const item2State = queue.getItem(item2.id);
      const item3State = queue.getItem(item3.id);

      console.log(JSON.stringify({{
        totalProcessed: syncResult.totalProcessed,
        syncedCount: syncResult.syncedCount,
        failedCount: syncResult.failedCount,
        item1Status: item1State.status,
        item2Status: item2State.status,
        item2Retries: item2State.retry_count,
        item3Status: item3State.status,
      }}));
    }})();
    """
    res = run_node_eval(js_code)

    assert res["totalProcessed"] == 3
    assert res["syncedCount"] == 2
    assert res["failedCount"] == 1

    # Item 1 and Item 3 synced successfully
    assert res["item1Status"] == "synced"
    assert res["item3Status"] == "synced"

    # Item 2 failed without interrupting Item 3
    assert res["item2Status"] == "pending"  # Still pending because retry_count (1) < 5
    assert res["item2Retries"] == 1


def test_retry_logic_safety_phrasing():
    """Verify retry logic files contain zero clinical diagnostic claims."""
    with open(JS_RETRY, "r", encoding="utf-8") as f:
        content = f.read().lower()

    assert "you have parkinson's" not in content
    assert "parkinson's progression" not in content
    assert "clinical diagnosis" not in content
