"""
Tests for MPF Mobile Extension — Offline Queue Module (Phase 13)

Validates:
1. Offline collection works: Records enqueued locally when device is offline.
2. Queue data structure: Enforces session_id, participant_id, event_id, idempotency_key, payload, and table_name.
3. Protected/Encrypted local temporary storage: Payloads are encrypted in storage and decrypted on load.
4. FIFO retrieval: Pending records are returned in order of creation.
5. State transitions: pending -> syncing -> synced / failed.
6. Data preservation across reloads: Simulated app reboot/reload with persistent storage recovers pending items (ZERO data loss).
7. Queue statistics and memory reclamation (clearSynced).
8. Strict non-diagnostic safety verification.

ALL test data is clearly labeled [SYNTHETIC].
"""

import json
import os
import subprocess
import uuid
import pytest
from pathlib import Path

from src.mobile.sync.sync_bridge import (
    PythonOfflineQueue,
    run_node_eval,
)

SYNC_DIR = Path(__file__).resolve().parents[1]
JS_QUEUE = SYNC_DIR / "offlineQueue.js"

DISALLOWED_DIAGNOSTIC_TERMS = [
    "you have parkinson's",
    "parkinson's detected",
    "parkinsons detected",
    "diagnosed parkinson",
    "disease progression",
    "clinical deterioration",
]


def test_offline_enqueuing_structure_node():
    """Verify offline queue enqueuing and data structure via Node.js runtime [SYNTHETIC]."""
    participant_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    payload = {
        "typing_speed": 45.5,
        "mean_inter_key_interval": 120.2,
        "quality_score": 0.95,
        "feature_version": "1.0.0"
    }

    js_code = f"""
    const {{ OfflineQueue, MemoryStorageAdapter }} = require({json.dumps(str(JS_QUEUE))});

    (async () => {{
      const storage = new MemoryStorageAdapter();
      const queue = new OfflineQueue({{ storage }});
      await queue.init();

      const item = await queue.enqueue({{
        participant_id: {json.dumps(participant_id)},
        session_id: {json.dumps(session_id)},
        table_name: 'typing_sessions',
        payload: {json.dumps(payload)},
      }});

      const stats = queue.getStats();
      const pending = queue.getPending();

      console.log(JSON.stringify({{
        item,
        stats,
        pendingCount: pending.length,
        firstPendingId: pending[0].id
      }}));
    }})();
    """
    res = run_node_eval(js_code)
    item = res["item"]

    assert item["participant_id"] == participant_id
    assert item["session_id"] == session_id
    assert item["table_name"] == "typing_sessions"
    assert item["status"] == "pending"
    assert item["retry_count"] == 0
    assert "event_id" in item and len(item["event_id"]) > 0
    assert "idempotency_key" in item and len(item["idempotency_key"]) > 0
    assert item["payload"]["typing_speed"] == 45.5
    assert res["stats"]["total"] == 1
    assert res["stats"]["pending"] == 1
    assert res["pendingCount"] == 1


def test_queue_encryption_at_rest_node():
    """Verify that stored payloads are encrypted at rest in storage adapter [SYNTHETIC]."""
    participant_id = str(uuid.uuid4())
    secret_metrics = {"pitch_mean": 182.4, "jitter": 0.012, "shimmer": 0.035}

    js_code = f"""
    const {{ OfflineQueue, MemoryStorageAdapter }} = require({json.dumps(str(JS_QUEUE))});

    (async () => {{
      const storage = new MemoryStorageAdapter();
      const queue = new OfflineQueue({{ storage, storageKey: 'test_sec_queue' }});
      await queue.init();

      await queue.enqueue({{
        participant_id: {json.dumps(participant_id)},
        table_name: 'voice_sessions',
        payload: {json.dumps(secret_metrics)},
      }});

      // Inspect raw serialized string in storage adapter
      const rawStored = await storage.getItem('test_sec_queue');

      // Create new queue instance simulating reload with same storage
      const reloadedQueue = new OfflineQueue({{ storage, storageKey: 'test_sec_queue' }});
      await reloadedQueue.init();
      const reloadedItem = reloadedQueue.peek();

      console.log(JSON.stringify({{
        rawStored,
        reloadedPayload: reloadedItem.payload
      }}));
    }})();
    """
    res = run_node_eval(js_code)
    raw_stored = res["rawStored"]
    reloaded_payload = res["reloadedPayload"]

    # Verify that serialized raw storage contains encrypted payload, not raw cleartext metrics
    assert "182.4" not in raw_stored
    assert "payload_encrypted" in raw_stored

    # Verify that upon queue reload, the payload is transparently decrypted
    assert reloaded_payload["pitch_mean"] == 182.4
    assert reloaded_payload["jitter"] == 0.012


def test_fifo_ordering_and_state_transitions_node():
    """Verify FIFO dequeue ordering and state transitions [SYNTHETIC]."""
    participant_id = str(uuid.uuid4())

    js_code = f"""
    const {{ OfflineQueue, MemoryStorageAdapter }} = require({json.dumps(str(JS_QUEUE))});

    (async () => {{
      const queue = new OfflineQueue({{ storage: new MemoryStorageAdapter() }});
      await queue.init();

      const item1 = await queue.enqueue({{
        participant_id: {json.dumps(participant_id)},
        table_name: 'motor_sessions',
        payload: {{ task_type: 'walking', cadence: 110.0 }},
      }});

      const item2 = await queue.enqueue({{
        participant_id: {json.dumps(participant_id)},
        table_name: 'visual_sessions',
        payload: {{ task_type: 'blink', blink_rate: 18.5 }},
      }});

      // FIFO check
      const firstPending = queue.peek();
      const isFifoCorrect = firstPending.id === item1.id;

      // Mark syncing
      await queue.markSyncing(item1.id);
      const afterSyncing = queue.getItem(item1.id).status;

      // Mark synced
      await queue.markSynced(item1.id, {{ status: 200 }});
      const afterSynced = queue.getItem(item1.id).status;

      // Item 2 failure test (retry_count 0 -> 1, remains pending)
      await queue.markFailed(item2.id, new Error('Network timeout'), true);
      const item2StatusAfterOneFail = queue.getItem(item2.id).status;
      const item2Retry1Count = queue.getItem(item2.id).retry_count;

      // Max retries reached (simulate reaching maxRetries 5)
      item2.retry_count = 4;
      await queue.markFailed(item2.id, new Error('Server 503'), true);
      const item2MaxFailed = queue.getItem(item2.id);

      console.log(JSON.stringify({{
        isFifoCorrect,
        afterSyncing,
        afterSynced,
        item2StatusAfterOneFail,
        item2RetryCount: item2Retry1Count,
        item2StatusAfterMaxRetries: item2MaxFailed.status,
        item2FinalRetryCount: item2MaxFailed.retry_count,
        stats: queue.getStats(),
      }}));
    }})();
    """
    res = run_node_eval(js_code)

    assert res["isFifoCorrect"] is True
    assert res["afterSyncing"] == "syncing"
    assert res["afterSynced"] == "synced"
    assert res["item2StatusAfterOneFail"] == "pending"
    assert res["item2RetryCount"] == 1
    assert res["item2StatusAfterMaxRetries"] == "failed"
    assert res["item2FinalRetryCount"] == 5
    assert res["stats"]["synced"] == 1
    assert res["stats"]["failed"] == 1


def test_zero_data_loss_on_offline_restarts():
    """Verify queue items are preserved and recovered with ZERO data loss across restarts [SYNTHETIC]."""
    participant_id = str(uuid.uuid4())

    js_code = f"""
    const {{ OfflineQueue, MemoryStorageAdapter }} = require({json.dumps(str(JS_QUEUE))});

    (async () => {{
      const sharedStorage = new MemoryStorageAdapter();

      // Session 1: App creates items while offline
      const app1Queue = new OfflineQueue({{ storage: sharedStorage, storageKey: 'persisted_offline' }});
      await app1Queue.init();

      await app1Queue.enqueue({{
        participant_id: {json.dumps(participant_id)},
        table_name: 'sleep_sessions',
        payload: {{ sleep_duration: 7.2, sleep_quality: 4.0, score: 85 }},
      }});
      await app1Queue.enqueue({{
        participant_id: {json.dumps(participant_id)},
        table_name: 'typing_sessions',
        payload: {{ typing_speed: 52.0, pause_rate: 0.12 }},
      }});

      // Simulate App Process Restart / Crash
      const app2Queue = new OfflineQueue({{ storage: sharedStorage, storageKey: 'persisted_offline' }});
      await app2Queue.init();

      const recoveredPending = app2Queue.getPending();
      const stats = app2Queue.getStats();

      console.log(JSON.stringify({{
        totalRecovered: stats.total,
        pendingRecovered: stats.pending,
        firstTable: recoveredPending[0].table_name,
        secondTable: recoveredPending[1].table_name,
        firstSleepDuration: recoveredPending[0].payload.sleep_duration,
      }}));
    }})();
    """
    res = run_node_eval(js_code)

    assert res["totalRecovered"] == 2
    assert res["pendingRecovered"] == 2
    assert res["firstTable"] == "sleep_sessions"
    assert res["secondTable"] == "typing_sessions"
    assert res["firstSleepDuration"] == 7.2


def test_clear_synced_reclaims_storage():
    """Verify clearSynced removes synced records while keeping pending/failed items intact [SYNTHETIC]."""
    participant_id = str(uuid.uuid4())

    queue = PythonOfflineQueue(max_retries=5)
    item1 = queue.enqueue({
        "participant_id": participant_id,
        "table_name": "typing_sessions",
        "payload": {"speed": 40.0}
    })
    item2 = queue.enqueue({
        "participant_id": participant_id,
        "table_name": "voice_sessions",
        "payload": {"pitch": 190.0}
    })

    queue.mark_synced(item1["id"])

    stats_before = queue.get_stats()
    assert stats_before["synced"] == 1
    assert stats_before["pending"] == 1
    assert stats_before["total"] == 2

    removed = queue.clear_synced()
    assert removed == 1

    stats_after = queue.get_stats()
    assert stats_after["synced"] == 0
    assert stats_after["pending"] == 1
    assert stats_after["total"] == 1
    assert queue.items[0]["id"] == item2["id"]


def test_non_diagnostic_safety_compliance():
    """Verify that queue code and metadata contains zero diagnostic claims."""
    with open(JS_QUEUE, "r", encoding="utf-8") as f:
        content = f.read().lower()

    for disallowed in DISALLOWED_DIAGNOSTIC_TERMS:
        assert disallowed not in content, f"Disallowed diagnostic phrase found in offlineQueue.js: {disallowed}"
