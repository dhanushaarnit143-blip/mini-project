"""
Tests for Supabase Authentication, JWT Token Management, Session Lifecycle,
and Privacy-Compliant Account Deletion Flow.
"""

import sqlite3
import time
import pytest
from supabase.tests.auth_service import SupabaseAuthService


@pytest.fixture
def auth_service():
    """Returns a fresh SupabaseAuthService instance."""
    return SupabaseAuthService(jwt_secret="super-secret-mpf-jwt-key-2026")


@pytest.fixture
def integrated_db():
    """Sets up an in-memory SQLite database representing all participant tables with ON DELETE CASCADE."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()
    cursor.executescript("""
    CREATE TABLE participants (
        id TEXT PRIMARY KEY,
        created_at TEXT DEFAULT (datetime('now')),
        pseudonymous_id TEXT UNIQUE NOT NULL
    );

    CREATE TABLE consent_records (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        consent_type TEXT NOT NULL,
        consent_version TEXT NOT NULL
    );

    CREATE TABLE typing_sessions (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        session_id TEXT UNIQUE NOT NULL
    );

    CREATE TABLE voice_sessions (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        session_id TEXT UNIQUE NOT NULL
    );

    CREATE TABLE motor_sessions (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        session_id TEXT UNIQUE NOT NULL
    );

    CREATE TABLE visual_sessions (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        session_id TEXT UNIQUE NOT NULL
    );

    CREATE TABLE sleep_sessions (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        session_id TEXT UNIQUE NOT NULL
    );

    CREATE TABLE daily_features (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        date TEXT NOT NULL
    );

    CREATE TABLE personal_baselines (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        modality TEXT NOT NULL
    );

    CREATE TABLE daily_deviations (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        date TEXT NOT NULL
    );

    CREATE TABLE mpf_predictions (
        id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        risk_score REAL NOT NULL
    );
    """)
    conn.commit()
    yield conn
    conn.close()


def test_user_registration_and_password_hashing(auth_service):
    """Test user registration hashes password and generates a pseudonymous ID."""
    reg = auth_service.register_user("participant1@mpf-research.org", "SecurePassword#2026")
    assert "user_id" in reg
    assert "pseudonymous_id" in reg
    assert reg["pseudonymous_id"].startswith("ps_")
    assert "access_token" in reg
    assert "refresh_token" in reg

    # Verify no plain-text password is stored
    user_record = auth_service._auth_users["participant1@mpf-research.org"]
    assert user_record["password_hash"] != "SecurePassword#2026"
    assert len(user_record["password_hash"]) == 64  # SHA-256 hex length
    assert len(user_record["salt"]) == 32  # 16 bytes hex


def test_duplicate_registration_rejected(auth_service):
    """Duplicate email registration is rejected."""
    auth_service.register_user("duplicate@mpf-research.org", "Pass123456!")
    with pytest.raises(ValueError, match="already registered"):
        auth_service.register_user("duplicate@mpf-research.org", "Pass123456!")


def test_login_flow(auth_service):
    """Test valid login yields valid tokens, invalid login fails."""
    auth_service.register_user("user_login@mpf-research.org", "CorrectPassword123")

    # Valid login
    login_res = auth_service.login_user("user_login@mpf-research.org", "CorrectPassword123")
    assert login_res["access_token"] is not None

    # Invalid password
    with pytest.raises(PermissionError, match="Invalid email or password"):
        auth_service.login_user("user_login@mpf-research.org", "WrongPassword!")

    # Nonexistent user
    with pytest.raises(PermissionError, match="Invalid email or password"):
        auth_service.login_user("nonexistent@mpf-research.org", "AnyPassword123")


def test_jwt_verification_and_claims(auth_service):
    """Test JWT token verification, claim inspection, and tampering detection."""
    reg = auth_service.register_user("jwt_test@mpf-research.org", "ValidPassword#1")
    token = reg["access_token"]

    payload = auth_service.verify_jwt(token)
    assert payload is not None
    assert payload["sub"] == reg["user_id"]
    assert payload["role"] == "authenticated"
    assert payload["aud"] == "authenticated"
    assert payload["exp"] > time.time()

    # Tampered token test: alter payload character
    parts = token.split(".")
    tampered_payload_b64 = parts[1][:-2] + "AA"
    tampered_token = f"{parts[0]}.{tampered_payload_b64}.{parts[2]}"
    assert auth_service.verify_jwt(tampered_token) is None


def test_token_expiration(auth_service):
    """Test that expired JWT tokens are rejected."""
    # Create an already expired token
    now = int(time.time()) - 3600
    exp = now - 60
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": "u-123", "role": "authenticated", "iat": now, "exp": exp}
    expired_token = auth_service._sign_jwt(header, payload)

    assert auth_service.verify_jwt(expired_token) is None


def test_session_refresh_and_logout(auth_service):
    """Test session refresh with token rotation and session revocation upon logout."""
    reg = auth_service.register_user("session_test@mpf-research.org", "MySessionPassword#1")
    old_refresh = reg["refresh_token"]

    # Refresh session
    new_session = auth_service.refresh_access_token(old_refresh)
    assert "access_token" in new_session
    assert "refresh_token" in new_session
    assert new_session["refresh_token"] != old_refresh

    # Old refresh token is revoked (rotation)
    with pytest.raises(PermissionError, match="Invalid or expired refresh token"):
        auth_service.refresh_access_token(old_refresh)

    # Logout
    logout_ok = auth_service.logout_user(new_session["refresh_token"])
    assert logout_ok is True

    # After logout, refresh fails
    with pytest.raises(PermissionError, match="Invalid or expired refresh token"):
        auth_service.refresh_access_token(new_session["refresh_token"])


def test_password_reset_flow(auth_service):
    """Test requesting and completing a time-limited, single-use password reset."""
    email = "reset_user@mpf-research.org"
    auth_service.register_user(email, "InitialPassword123")

    # Request reset token
    reset_token = auth_service.request_password_reset(email)
    assert reset_token != ""

    # Complete reset with new password
    success = auth_service.complete_password_reset(reset_token, "BrandNewPassword2026")
    assert success is True

    # Login with new password succeeds
    login_new = auth_service.login_user(email, "BrandNewPassword2026")
    assert login_new["access_token"] is not None

    # Login with old password fails
    with pytest.raises(PermissionError):
        auth_service.login_user(email, "InitialPassword123")

    # Token cannot be reused
    with pytest.raises(ValueError, match="invalid or has expired"):
        auth_service.complete_password_reset(reset_token, "AnotherPassword123")


def test_account_deletion_workflow_and_cascading_purge(auth_service, integrated_db):
    """
    Test GDPR Right-to-Erasure workflow.
    When a participant deletes their account, all biometric sessions, baselines,
    and predictions across all tables are cleanly purged with zero orphaned rows.
    """
    email = "gdpr_participant@mpf-research.org"
    reg = auth_service.register_user(email, "GdprPassword123")
    user_id = reg["user_id"]

    cursor = integrated_db.cursor()
    # Insert participant record
    cursor.execute("INSERT INTO participants (id, pseudonymous_id) VALUES (?, ?)", (user_id, reg["pseudonymous_id"]))

    # Insert data across all 10 child tables
    cursor.execute("INSERT INTO consent_records (id, participant_id, consent_type, consent_version) VALUES ('c-1', ?, 'data_collection', '1.0.0')", (user_id,))
    cursor.execute("INSERT INTO typing_sessions (id, participant_id, session_id) VALUES ('t-1', ?, 'sess-t-1')", (user_id,))
    cursor.execute("INSERT INTO voice_sessions (id, participant_id, session_id) VALUES ('v-1', ?, 'sess-v-1')", (user_id,))
    cursor.execute("INSERT INTO motor_sessions (id, participant_id, session_id) VALUES ('m-1', ?, 'sess-m-1')", (user_id,))
    cursor.execute("INSERT INTO visual_sessions (id, participant_id, session_id) VALUES ('vis-1', ?, 'sess-vis-1')", (user_id,))
    cursor.execute("INSERT INTO sleep_sessions (id, participant_id, session_id) VALUES ('sl-1', ?, 'sess-sl-1')", (user_id,))
    cursor.execute("INSERT INTO daily_features (id, participant_id, date) VALUES ('df-1', ?, '2026-09-23')", (user_id,))
    cursor.execute("INSERT INTO personal_baselines (id, participant_id, modality) VALUES ('pb-1', ?, 'typing')", (user_id,))
    cursor.execute("INSERT INTO daily_deviations (id, participant_id, date) VALUES ('dd-1', ?, '2026-09-23')", (user_id,))
    cursor.execute("INSERT INTO mpf_predictions (id, participant_id, risk_score) VALUES ('mp-1', ?, 0.05)", (user_id,))
    integrated_db.commit()

    # Verify rows exist
    child_tables = [
        "consent_records", "typing_sessions", "voice_sessions", "motor_sessions",
        "visual_sessions", "sleep_sessions", "daily_features", "personal_baselines",
        "daily_deviations", "mpf_predictions"
    ]
    for table in child_tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE participant_id = ?", (user_id,))
        assert cursor.fetchone()[0] == 1, f"Table {table} did not receive test record"

    # Execute deletion workflow
    deleted = auth_service.delete_account(user_id, db_connection=integrated_db)
    assert deleted is True

    # Verify auth record is gone
    assert email not in auth_service._auth_users

    # Verify participant table record is gone
    cursor.execute("SELECT COUNT(*) FROM participants WHERE id = ?", (user_id,))
    assert cursor.fetchone()[0] == 0

    # Verify ALL child records are purged via CASCADE (Zero orphaned data)
    for table in child_tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE participant_id = ?", (user_id,))
        count = cursor.fetchone()[0]
        assert count == 0, f"Orphaned record found in {table} after account deletion!"
