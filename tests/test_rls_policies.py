"""
Tests for Row Level Security (RLS) Policies and Supabase Authentication.

Validates:
- All 12 tables enable Row Level Security (RLS)
- Policy 1: Participants can READ their own data
- Policy 2: Participants can INSERT their own data
- Policy 3: Participants can UPDATE their own data
- Policy 4: Participants can DELETE their own data
- Policy 5: model_versions is read-only for all authenticated users
- Cross-participant access is strictly blocked (Participant A cannot read Participant B's data)
- Unauthenticated access is blocked
- Full authentication workflow (register, login, JWT verification, session refresh, password reset, logout)
"""

import re
import uuid
import time
import sys
from pathlib import Path
import pytest

_supabase_tests_dir = str(Path(__file__).resolve().parent.parent / "supabase" / "tests")
if _supabase_tests_dir not in sys.path:
    sys.path.insert(0, _supabase_tests_dir)

from auth_service import SupabaseAuthService

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "supabase" / "migrations"

ALL_12_TABLES = [
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

USER_DATA_TABLES = [
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
]


def test_rls_enabled_on_all_12_tables():
    """Verify that migration 009 enables RLS on every single table."""
    rls_path = MIGRATIONS_DIR / "009_create_rls_policies.sql"
    assert rls_path.exists(), "009_create_rls_policies.sql missing"
    content = rls_path.read_text(encoding="utf-8")

    for table in ALL_12_TABLES:
        pattern = re.compile(rf"ALTER\s+TABLE\s+{table}\s+ENABLE\s+ROW\s+LEVEL\s+SECURITY", re.IGNORECASE)
        assert pattern.search(content), f"RLS not enabled for table: {table}"


def test_rls_policies_for_participants_table():
    """Verify participants table has CRUD policies checking auth.uid() = id."""
    content = (MIGRATIONS_DIR / "009_create_rls_policies.sql").read_text(encoding="utf-8")
    assert re.search(r"CREATE\s+POLICY\s+\"Users can view own data\"\s+ON\s+participants\s+FOR\s+SELECT\s+USING\s*\(\s*auth\.uid\(\)\s*=\s*id\s*\)", content, re.IGNORECASE)
    assert re.search(r"CREATE\s+POLICY\s+\"Users can insert own data\"\s+ON\s+participants\s+FOR\s+INSERT\s+WITH\s+CHECK\s*\(\s*auth\.uid\(\)\s*=\s*id\s*\)", content, re.IGNORECASE)
    assert re.search(r"CREATE\s+POLICY\s+\"Users can update own data\"\s+ON\s+participants\s+FOR\s+UPDATE\s+USING\s*\(\s*auth\.uid\(\)\s*=\s*id\s*\)", content, re.IGNORECASE)
    assert re.search(r"CREATE\s+POLICY\s+\"Users can delete own data\"\s+ON\s+participants\s+FOR\s+DELETE\s+USING\s*\(\s*auth\.uid\(\)\s*=\s*id\s*\)", content, re.IGNORECASE)


def test_rls_policies_for_user_data_tables():
    """Verify all 10 user data tables define CRUD policies using auth.uid() = participant_id."""
    content = (MIGRATIONS_DIR / "009_create_rls_policies.sql").read_text(encoding="utf-8")
    for tbl in USER_DATA_TABLES:
        assert re.search(rf"CREATE\s+POLICY\s+\"Users can view own data\"\s+ON\s+{tbl}\s+FOR\s+SELECT\s+USING\s*\(\s*auth\.uid\(\)\s*=\s*participant_id\s*\)", content, re.IGNORECASE), f"Missing view policy for {tbl}"
        assert re.search(rf"CREATE\s+POLICY\s+\"Users can insert own data\"\s+ON\s+{tbl}\s+FOR\s+INSERT\s+WITH\s+CHECK\s*\(\s*auth\.uid\(\)\s*=\s*participant_id\s*\)", content, re.IGNORECASE), f"Missing insert policy for {tbl}"
        assert re.search(rf"CREATE\s+POLICY\s+\"Users can update own data\"\s+ON\s+{tbl}\s+FOR\s+UPDATE\s+USING\s*\(\s*auth\.uid\(\)\s*=\s*participant_id\s*\)", content, re.IGNORECASE), f"Missing update policy for {tbl}"
        assert re.search(rf"CREATE\s+POLICY\s+\"Users can delete own data\"\s+ON\s+{tbl}\s+FOR\s+DELETE\s+USING\s*\(\s*auth\.uid\(\)\s*=\s*participant_id\s*\)", content, re.IGNORECASE), f"Missing delete policy for {tbl}"


def test_model_versions_read_only_policy():
    """Verify model_versions allows SELECT for authenticated role and blocks modification."""
    content = (MIGRATIONS_DIR / "009_create_rls_policies.sql").read_text(encoding="utf-8")
    assert re.search(r"CREATE\s+POLICY\s+\"Anyone can read model versions\"\s+ON\s+model_versions\s+FOR\s+SELECT\s+USING\s*\(\s*auth\.role\(\)\s*=\s*'authenticated'\s*\)", content, re.IGNORECASE)
    # Ensure no open INSERT/UPDATE/DELETE policies exist on model_versions
    assert not re.search(r"CREATE\s+POLICY.*ON\s+model_versions\s+FOR\s+INSERT", content, re.IGNORECASE)
    assert not re.search(r"CREATE\s+POLICY.*ON\s+model_versions\s+FOR\s+UPDATE", content, re.IGNORECASE)
    assert not re.search(r"CREATE\s+POLICY.*ON\s+model_versions\s+FOR\s+DELETE", content, re.IGNORECASE)


class MockRLSEngine:
    """Simulates PostgreSQL Row Level Security evaluation engine."""

    def __init__(self):
        self.participants = {}
        self.typing_sessions = []
        self.voice_sessions = []
        self.daily_features = []
        self.mpf_predictions = []
        self.model_versions = [
            {"id": "m1", "model_name": "gated_multimodal_fusion", "version": "v1.0.0"}
        ]

    def evaluate_select(self, table: str, requesting_user_id: str, role: str = "authenticated"):
        if role != "authenticated":
            return []  # Unauthenticated access rejected

        if table == "model_versions":
            return list(self.model_versions)

        if table == "participants":
            return [p for p in self.participants.values() if p["id"] == requesting_user_id]

        data = getattr(self, table, [])
        return [row for row in data if row.get("participant_id") == requesting_user_id]

    def evaluate_insert(self, table: str, row: dict, requesting_user_id: str, role: str = "authenticated") -> bool:
        if role != "authenticated":
            return False

        if table == "model_versions":
            return False  # Read-only table for authenticated users

        if table == "participants":
            if row.get("id") != requesting_user_id:
                return False  # Cannot insert record with different id
            self.participants[requesting_user_id] = row
            return True

        # User data tables require auth.uid() == participant_id
        if row.get("participant_id") != requesting_user_id:
            return False

        getattr(self, table).append(row)
        return True


def test_participant_a_cannot_read_participant_b_data():
    """Verify cross-participant data isolation: Participant A cannot read Participant B's data."""
    engine = MockRLSEngine()

    user_a = "user-uuid-A"
    user_b = "user-uuid-B"

    # User B inserts data
    assert engine.evaluate_insert("participants", {"id": user_b, "email": "b@test.com"}, user_b)
    assert engine.evaluate_insert("typing_sessions", {"session_id": "s-b-1", "participant_id": user_b, "typing_speed": 4.5}, user_b)
    assert engine.evaluate_insert("voice_sessions", {"session_id": "v-b-1", "participant_id": user_b, "jitter": 0.01}, user_b)
    assert engine.evaluate_insert("daily_features", {"participant_id": user_b, "date": "2026-11-18"}, user_b)
    assert engine.evaluate_insert("mpf_predictions", {"participant_id": user_b, "risk_score": 0.35}, user_b)

    # User A attempts to read User B's data
    assert len(engine.evaluate_select("participants", user_a)) == 0
    assert len(engine.evaluate_select("typing_sessions", user_a)) == 0
    assert len(engine.evaluate_select("voice_sessions", user_a)) == 0
    assert len(engine.evaluate_select("daily_features", user_a)) == 0
    assert len(engine.evaluate_select("mpf_predictions", user_a)) == 0

    # User B can read own data
    assert len(engine.evaluate_select("participants", user_b)) == 1
    assert len(engine.evaluate_select("typing_sessions", user_b)) == 1
    assert len(engine.evaluate_select("voice_sessions", user_b)) == 1


def test_participant_cannot_insert_data_for_another_user():
    """Verify that User A cannot insert data with Participant B's ID."""
    engine = MockRLSEngine()
    user_a = "user-uuid-A"
    user_b = "user-uuid-B"

    # User A tries to insert typing session labeled with user B's ID
    allowed = engine.evaluate_insert(
        "typing_sessions",
        {"session_id": "spoofed-sess", "participant_id": user_b, "typing_speed": 3.0},
        requesting_user_id=user_a
    )
    assert allowed is False


def test_unauthenticated_access_is_blocked():
    """Verify that unauthenticated (anon/public) access cannot query user tables."""
    engine = MockRLSEngine()
    user_b = "user-uuid-B"
    engine.evaluate_insert("participants", {"id": user_b, "email": "b@test.com"}, user_b)

    # Anonymous user (no auth role)
    results = engine.evaluate_select("participants", requesting_user_id="", role="anon")
    assert len(results) == 0


def test_authenticated_user_can_read_model_versions_but_cannot_modify():
    """Verify model_versions is readable by authenticated users but insertion is blocked."""
    engine = MockRLSEngine()
    user_a = "user-uuid-A"

    # Read model versions
    models = engine.evaluate_select("model_versions", user_a, role="authenticated")
    assert len(models) == 1
    assert models[0]["model_name"] == "gated_multimodal_fusion"

    # Insert new model version is blocked for regular authenticated user
    insert_allowed = engine.evaluate_insert("model_versions", {"model_name": "retrained_model", "version": "v2"}, user_a)
    assert insert_allowed is False


def test_supabase_auth_flow_complete():
    """Verify complete authentication flow: registration, login, JWT verification, session refresh, and logout."""
    auth = SupabaseAuthService(jwt_secret="mpf-phase-a-secret-key-2026")
    email = "researcher.pd@mpf-study.org"
    password = "StrongPassword#2026!"

    # 1. Registration
    reg = auth.register_user(email, password)
    assert "user_id" in reg
    assert "access_token" in reg
    assert "refresh_token" in reg
    user_id = reg["user_id"]

    # 2. Duplicate registration rejection
    with pytest.raises(ValueError, match="already registered"):
        auth.register_user(email, password)

    # 3. Login with wrong password rejected
    with pytest.raises(PermissionError, match="Invalid email or password"):
        auth.login_user(email, "WrongPassword")

    # 4. Successful login
    login_res = auth.login_user(email, password)
    assert login_res["user_id"] == user_id
    token = login_res["access_token"]
    refresh_token = login_res["refresh_token"]

    # 5. Token verification & claims
    claims = auth.verify_jwt(token)
    assert claims is not None
    assert claims["sub"] == user_id
    assert claims["role"] == "authenticated"

    # 6. Session refresh (token rotation)
    ref_res = auth.refresh_access_token(refresh_token)
    assert "access_token" in ref_res
    new_token = ref_res["access_token"]
    assert new_token is not None

    # 7. Password reset workflow
    reset_token = auth.request_password_reset(email)
    assert reset_token != ""

    success = auth.complete_password_reset(reset_token, "NewStrongPassword#2026!")
    assert success is True

    # 8. Login with new password
    login_new = auth.login_user(email, "NewStrongPassword#2026!")
    assert login_new["user_id"] == user_id

    # 9. Logout
    logout_success = auth.logout_user(login_new["refresh_token"])
    assert logout_success is True
