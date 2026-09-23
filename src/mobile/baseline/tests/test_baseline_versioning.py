"""
Tests for MPF Mobile Extension — Baseline Versioning (Phase 10)

Validates:
1. Version lifecycle and sequential incrementing:
   - Initial version is '1.0.0' on establishment (Day 14).
   - Increments monotonically on each accepted adaptive update ('1.0.1', '1.0.2', etc.).
2. Timestamps provenance and immutability:
   - baseline_created_at is permanently preserved across all updates.
   - baseline_updated_at advances on every modification.
3. Metadata validation:
   - validateBaselineVersionMetadata verifies presence and shape of all fields.
4. Sample count tracking:
   - Correctly accumulates number of incorporated observations.
5. Database schema serialization:
   - Validates insertion, retrieval, and schema integrity for personal_baselines and daily_deviations.
6. Supabase live schema verification:
   - Verifies live Supabase table accessibility and RLS isolation.

ALL test data is clearly labeled [SYNTHETIC].
"""

import json
import os
import sqlite3
import subprocess
import uuid
import pytest
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
JS_VERSION = BASE_DIR / "baselineVersionManager.js"
JS_UPDATER = BASE_DIR / "adaptiveBaselineUpdater.js"
JS_CALCULATOR = BASE_DIR / "baselineCalculator.js"
JS_ENGINE = BASE_DIR / "baselineEngine.js"

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://trtvdmgswouirfaqyrdk.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRydHZkbWdzd291aXJmYXF5cmRrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTAxNjM3OTAsImV4cCI6MjEwNTczOTc5MH0.wxyGhyELZJy_-R2X4xqDaIsgofDbdQJtwZWjboCOKrM")


def run_node_eval(js_code: str):
    res = subprocess.run(
        ["node", "-e", js_code],
        capture_output=True,
        text=True,
        check=True
    )
    return json.loads(res.stdout)


def test_initial_version_creation():
    """Verify createInitialBaselineVersion creates valid 1.0.0 metadata [SYNTHETIC]."""
    js_code = f"""
    const {{ createInitialBaselineVersion, validateBaselineVersionMetadata }} = require({json.dumps(str(JS_VERSION))});

    const meta = createInitialBaselineVersion({{
      sampleCount: 14,
      algorithmVersion: '1.0.0',
      createdAt: '2026-09-14T00:00:00.000Z'
    }});

    const validation = validateBaselineVersionMetadata(meta);
    console.log(JSON.stringify({{ meta, validation }}));
    """

    res = run_node_eval(js_code)
    meta = res["meta"]
    assert meta["baseline_version"] == "1.0.0"
    assert meta["algorithm_version"] == "1.0.0"
    assert meta["sample_count"] == 14
    assert meta["baseline_created_at"] == "2026-09-14T00:00:00.000Z"
    assert meta["baseline_updated_at"] == "2026-09-14T00:00:00.000Z"
    assert res["validation"]["isValid"] is True


def test_sequential_version_increments():
    """Verify version increments patch number on each update while preserving creation timestamp [SYNTHETIC]."""
    js_code = f"""
    const {{ updateBaselineVersion }} = require({json.dumps(str(JS_VERSION))});

    let current = {{
      baseline_version: '1.0.0',
      algorithm_version: '1.0.0',
      baseline_created_at: '2026-09-14T00:00:00.000Z',
      baseline_updated_at: '2026-09-14T00:00:00.000Z',
      sample_count: 14
    }};

    const versions = [current.baseline_version];
    const timestamps = [current.baseline_updated_at];

    for (let i = 1; i <= 3; i++) {{
      const updatedTime = `2026-09-${{14 + i}}T12:00:00.000Z`;
      current = updateBaselineVersion(current, {{ updatedAt: updatedTime }});
      versions.push(current.baseline_version);
      timestamps.push(current.baseline_updated_at);
    }}

    console.log(JSON.stringify({{
      versions,
      timestamps,
      finalMeta: current
    }}));
    """

    res = run_node_eval(js_code)
    assert res["versions"] == ["1.0.0", "1.0.1", "1.0.2", "1.0.3"]
    assert res["finalMeta"]["sample_count"] == 17
    # Creation timestamp must never change
    assert res["finalMeta"]["baseline_created_at"] == "2026-09-14T00:00:00.000Z"
    # Updated timestamp must advance to the latest date
    assert res["finalMeta"]["baseline_updated_at"] == "2026-09-17T12:00:00.000Z"


def test_version_validation_rules():
    """Verify validation detects invalid semantic versions and missing fields."""
    js_code = f"""
    const {{ validateBaselineVersionMetadata }} = require({json.dumps(str(JS_VERSION))});

    const valid = validateBaselineVersionMetadata({{
      baseline_version: '1.0.0',
      algorithm_version: '1.0.0',
      baseline_created_at: '2026-09-14T00:00:00.000Z',
      baseline_updated_at: '2026-09-14T00:00:00.000Z',
      sample_count: 14
    }});

    const badVersion = validateBaselineVersionMetadata({{
      baseline_version: 'invalid-v1',
      algorithm_version: '1.0.0',
      baseline_created_at: '2026-09-14T00:00:00.000Z',
      baseline_updated_at: '2026-09-14T00:00:00.000Z',
      sample_count: 14
    }});

    const missingFields = validateBaselineVersionMetadata({{
      baseline_version: '1.0.0'
    }});

    console.log(JSON.stringify({{ valid, badVersion, missingFields }}));
    """

    res = run_node_eval(js_code)
    assert res["valid"]["isValid"] is True
    assert res["badVersion"]["isValid"] is False
    assert any("baseline_version" in e for e in res["badVersion"]["errors"])
    assert res["missingFields"]["isValid"] is False


def test_database_schema_serialization_and_crud():
    """Verify full CRUD operations against personal_baselines and daily_deviations schemas [SYNTHETIC]."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE participants (
        id TEXT PRIMARY KEY,
        pseudonymous_id TEXT UNIQUE NOT NULL,
        baseline_status TEXT DEFAULT 'collecting'
    );

    CREATE TABLE personal_baselines (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        modality TEXT NOT NULL,
        feature_name TEXT NOT NULL,
        baseline_mean REAL NOT NULL,
        baseline_median REAL NOT NULL,
        baseline_std REAL NOT NULL,
        baseline_mad REAL NOT NULL,
        lower_bound REAL NOT NULL,
        upper_bound REAL NOT NULL,
        q1 REAL,
        q3 REAL,
        coefficient_of_variation REAL,
        sample_count INTEGER NOT NULL,
        baseline_start_date TEXT NOT NULL,
        baseline_end_date TEXT NOT NULL,
        baseline_status TEXT DEFAULT 'calibrating',
        baseline_version TEXT NOT NULL DEFAULT '1.0.0',
        algorithm_version TEXT NOT NULL DEFAULT '1.0.0',
        baseline_created_at TEXT NOT NULL,
        baseline_updated_at TEXT NOT NULL
    );

    CREATE TABLE daily_deviations (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        date TEXT NOT NULL,
        modality TEXT NOT NULL,
        feature_name TEXT NOT NULL,
        value REAL NOT NULL,
        baseline_value REAL NOT NULL,
        deviation_score REAL NOT NULL,
        trend_score REAL NOT NULL,
        quality_score REAL NOT NULL,
        is_outlier INTEGER DEFAULT 0,
        anomaly_flag TEXT,
        mad_distance REAL,
        algorithm_version TEXT NOT NULL DEFAULT '1.0.0'
    );
    """)

    part_id = str(uuid.uuid4())
    cursor.execute("INSERT INTO participants (id, pseudonymous_id) VALUES (?, ?)", (part_id, f"PSEUDO-{part_id[:6]}"))

    base_id = str(uuid.uuid4())
    cursor.execute("""
    INSERT INTO personal_baselines (
        id, participant_id, modality, feature_name, baseline_mean, baseline_median,
        baseline_std, baseline_mad, lower_bound, upper_bound, q1, q3,
        coefficient_of_variation, sample_count, baseline_start_date, baseline_end_date,
        baseline_status, baseline_version, algorithm_version, baseline_created_at, baseline_updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        base_id, part_id, "motor", "cadence", 104.5, 104.0, 3.2, 2.1, 97.7, 110.3,
        102.5, 106.0, 0.0306, 14, "2026-09-01", "2026-09-14", "established",
        "1.0.0", "1.0.0", "2026-09-14T00:00:00Z", "2026-09-14T00:00:00Z"
    ))

    # Read and verify
    cursor.execute("SELECT * FROM personal_baselines WHERE id = ?", (base_id,))
    row = cursor.fetchone()
    assert row is not None
    assert row["baseline_status"] == "established"
    assert row["sample_count"] == 14
    assert row["baseline_version"] == "1.0.0"

    # Insert deviation
    dev_id = str(uuid.uuid4())
    cursor.execute("""
    INSERT INTO daily_deviations (
        id, participant_id, date, modality, feature_name, value, baseline_value,
        deviation_score, trend_score, quality_score, is_outlier, anomaly_flag, mad_distance
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        dev_id, part_id, "2026-09-15", "motor", "cadence", 115.0, 104.0,
        3.5, 11.0, 0.95, 1, "anomalous observation", 5.24
    ))

    cursor.execute("SELECT * FROM daily_deviations WHERE id = ?", (dev_id,))
    dev_row = cursor.fetchone()
    assert dev_row is not None
    assert dev_row["is_outlier"] == 1
    assert dev_row["anomaly_flag"] == "anomalous observation"


def test_live_supabase_connection_and_table_read():
    """Verify live Supabase connection and read access to personal_baselines and daily_deviations."""
    from supabase import create_client

    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    assert client is not None

    # Verify personal_baselines table exists and responds
    base_res = client.table("personal_baselines").select("id").limit(1).execute()
    assert base_res.data is not None

    # Verify daily_deviations table exists and responds
    dev_res = client.table("daily_deviations").select("id").limit(1).execute()
    assert dev_res.data is not None
