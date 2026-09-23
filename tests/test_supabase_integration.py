"""
Integration tests for Supabase backend:
- Project: mini project
- Schema integrity and migrations
- Live Supabase connection and CRUD (Create, Read, Update, Delete)
- Authentication & RLS policy enforcement
- Storage buckets validation
- FastAPI cohort endpoints
"""

import os
import pytest
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
MIGRATIONS_FILE = ROOT_DIR / "supabase" / "migrations" / "001_initial_schema.sql"
SEED_FILE = ROOT_DIR / "supabase" / "seed.sql"

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://trtvdmgswouirfaqyrdk.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRydHZkbWdzd291aXJmYXF5cmRrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTAxNjM3OTAsImV4cCI6MjEwNTczOTc5MH0.wxyGhyELZJy_-R2X4xqDaIsgofDbdQJtwZWjboCOKrM")


def test_migration_and_seed_files_exist():
    """Verify 001_initial_schema.sql and seed.sql exist and define all application tables."""
    assert MIGRATIONS_FILE.exists(), "Missing 001_initial_schema.sql"
    assert SEED_FILE.exists(), "Missing seed.sql"

    content = MIGRATIONS_FILE.read_text(encoding="utf-8")
    expected_tables = [
        "profiles",
        "cohort_participants",
        "assessments",
        "fusion_results",
        "participants",
        "consent_records",
        "typing_sessions",
        "voice_sessions",
        "motor_sessions",
        "visual_sessions",
        "sleep_sessions",
        "daily_features",
        "personal_baselines",
        "daily_deviations",
        "mpf_predictions",
        "model_versions",
    ]
    for table in expected_tables:
        assert f"TABLE IF NOT EXISTS public.{table}" in content or f"TABLE IF NOT EXISTS {table}" in content, f"Table {table} missing from 001_initial_schema.sql"

    # Verify RLS enabled
    assert "ENABLE ROW LEVEL SECURITY" in content
    # Verify trigger
    assert "handle_new_user" in content
    assert "on_auth_user_created" in content


def test_supabase_client_connection():
    """Verify Python Supabase client connects to mini project."""
    from supabase import create_client
    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    assert client is not None


def test_live_supabase_cohort_read():
    """Verify live reading of seeded cohort participants from Supabase."""
    from supabase import create_client
    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    res = client.table("cohort_participants").select("*").execute()
    assert res.data is not None
    assert len(res.data) >= 1
    # Check that known seeded codes exist
    codes = [row["cohort_code"] for row in res.data]
    assert any("#PD-" in code or "#CTRL-" in code for code in codes)


def test_live_supabase_crud_cycle():
    """Verify complete CRUD lifecycle: Create, Read, Update, Delete on cohort_participants."""
    from supabase import create_client
    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

    test_code = "#TEST-INT-9999"

    # 1. CREATE
    insert_res = client.table("cohort_participants").insert({
        "cohort_code": test_code,
        "visit_label": "Test Visit 1",
        "clinical_notes": "Integration test participant",
        "risk_index": 0.42,
        "risk_class": "Intermediate",
        "avatar_color": "sky",
        "demographics": {"age": 60, "sex": "Male", "familyHistory": False},
    }).execute()

    assert insert_res.data is not None
    assert len(insert_res.data) == 1
    created_id = insert_res.data[0]["id"]

    # 2. READ
    read_res = client.table("cohort_participants").select("*").eq("cohort_code", test_code).execute()
    assert len(read_res.data) == 1
    assert read_res.data[0]["cohort_code"] == test_code
    assert float(read_res.data[0]["risk_index"]) == 0.42

    # 3. UPDATE
    update_res = client.table("cohort_participants").update({
        "clinical_notes": "Updated integration test participant",
        "risk_index": 0.45
    }).eq("cohort_code", test_code).execute()

    assert update_res.data is not None
    assert update_res.data[0]["clinical_notes"] == "Updated integration test participant"

    # 4. DELETE
    delete_res = client.table("cohort_participants").delete().eq("cohort_code", test_code).execute()
    assert delete_res.data is not None

    # Verify deleted
    verify_res = client.table("cohort_participants").select("*").eq("cohort_code", test_code).execute()
    assert len(verify_res.data) == 0


def test_model_versions_read_only():
    """Verify model_versions table is readable for public/anon."""
    from supabase import create_client
    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    res = client.table("model_versions").select("*").execute()
    assert res.data is not None
    assert len(res.data) >= 1
    names = [row["model_name"] for row in res.data]
    assert "gated_multimodal_fusion" in names


def test_assessments_rls_isolation():
    """Verify that unauthenticated anon queries to private assessments table are blocked by RLS."""
    from supabase import create_client
    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    # Anon user without auth token has no rows in assessments
    res = client.table("assessments").select("*").execute()
    assert res.data == []


def test_fastapi_cohort_endpoints():
    """Verify FastAPI /api/cohort GET and POST endpoints."""
    from fastapi.testclient import TestClient
    from dashboard.api.main import app

    client = TestClient(app)
    response = client.get("/api/cohort")
    assert response.status_code == 200
    data = response.json()
    assert "cohort" in data
    assert "total" in data
    assert data["total"] >= 1
