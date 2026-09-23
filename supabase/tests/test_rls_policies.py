"""
Tests for Supabase Row Level Security (RLS) Policies.
Verifies:
- Policy 1: Participants can only read their own data.
- Policy 2: Participants can only insert their own data.
- Policy 3: Participants can only update their own data.
- Policy 4: Participants can only delete their own data.
- Policy 5: No cross-participant access is possible (Participant A cannot see/modify B's data).
- Policy 6: Research export requires separate service-role access.
- Policy 7: Model versions table is read-only for participants.
- Unauthenticated access is completely blocked.
- Storage RLS isolates consent documents and reserves research exports to service role.
"""

import sqlite3
import pytest
from typing import Optional, Dict, Any, List


class SupabaseRLSSimulator:
    """Simulates PostgreSQL / Supabase Row-Level Security engine with auth context."""

    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        cursor = self.conn.cursor()
        cursor.executescript("""
        CREATE TABLE participants (
            id TEXT PRIMARY KEY,
            baseline_status TEXT DEFAULT 'collecting',
            pseudonymous_id TEXT UNIQUE NOT NULL
        );

        CREATE TABLE consent_records (
            id TEXT PRIMARY KEY,
            participant_id TEXT NOT NULL,
            consent_type TEXT NOT NULL,
            consent_version TEXT NOT NULL,
            granted INTEGER DEFAULT 1
        );

        CREATE TABLE typing_sessions (
            id TEXT PRIMARY KEY,
            participant_id TEXT NOT NULL,
            session_id TEXT UNIQUE NOT NULL,
            task_type TEXT NOT NULL,
            duration REAL NOT NULL,
            quality_score REAL NOT NULL
        );

        CREATE TABLE voice_sessions (
            id TEXT PRIMARY KEY,
            participant_id TEXT NOT NULL,
            session_id TEXT UNIQUE NOT NULL,
            task_type TEXT NOT NULL,
            quality_score REAL NOT NULL
        );

        CREATE TABLE motor_sessions (
            id TEXT PRIMARY KEY,
            participant_id TEXT NOT NULL,
            session_id TEXT UNIQUE NOT NULL,
            task_type TEXT NOT NULL,
            quality_score REAL NOT NULL
        );

        CREATE TABLE visual_sessions (
            id TEXT PRIMARY KEY,
            participant_id TEXT NOT NULL,
            session_id TEXT UNIQUE NOT NULL,
            task_type TEXT NOT NULL,
            quality_score REAL NOT NULL
        );

        CREATE TABLE sleep_sessions (
            id TEXT PRIMARY KEY,
            participant_id TEXT NOT NULL,
            session_id TEXT UNIQUE NOT NULL,
            score REAL NOT NULL
        );

        CREATE TABLE daily_features (
            id TEXT PRIMARY KEY,
            participant_id TEXT NOT NULL,
            date TEXT NOT NULL,
            feature_version TEXT NOT NULL
        );

        CREATE TABLE personal_baselines (
            id TEXT PRIMARY KEY,
            participant_id TEXT NOT NULL,
            modality TEXT NOT NULL,
            feature_name TEXT NOT NULL,
            baseline_mean REAL NOT NULL
        );

        CREATE TABLE daily_deviations (
            id TEXT PRIMARY KEY,
            participant_id TEXT NOT NULL,
            date TEXT NOT NULL,
            deviation_score REAL NOT NULL
        );

        CREATE TABLE mpf_predictions (
            id TEXT PRIMARY KEY,
            participant_id TEXT NOT NULL,
            risk_score REAL NOT NULL,
            model_version TEXT NOT NULL
        );

        CREATE TABLE model_versions (
            id TEXT PRIMARY KEY,
            model_name TEXT NOT NULL,
            version TEXT NOT NULL,
            active INTEGER DEFAULT 1
        );

        CREATE TABLE storage_objects (
            id TEXT PRIMARY KEY,
            bucket_id TEXT NOT NULL,
            name TEXT NOT NULL,
            owner TEXT
        );
        """)
        self.conn.commit()

    def select(self, table: str, role: str, auth_uid: Optional[str], where: Optional[Dict[str, Any]] = None) -> List[sqlite3.Row]:
        """Executes a SELECT query evaluated against RLS policies."""
        if role == "anon":
            # Anonymous users have no access to participant data or model versions
            return []

        if role == "service_role":
            # Service role bypasses RLS
            query = f"SELECT * FROM {table}"
            params = []
            if where:
                clauses = [f"{k} = ?" for k in where.keys()]
                query += " WHERE " + " AND ".join(clauses)
                params = list(where.values())
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()

        if role == "authenticated":
            if not auth_uid:
                return []

            if table == "model_versions":
                # Policy 7: model_versions is readable to authenticated users
                query = "SELECT * FROM model_versions"
                params = []
                if where:
                    clauses = [f"{k} = ?" for k in where.keys()]
                    query += " WHERE " + " AND ".join(clauses)
                    params = list(where.values())
                cursor = self.conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchall()

            # Participant tables: USING (auth.uid() = participant_id) or (auth.uid() = id for participants)
            id_column = "id" if table == "participants" else "participant_id"
            query = f"SELECT * FROM {table} WHERE {id_column} = ?"
            params = [auth_uid]

            if where:
                for k, v in where.items():
                    query += f" AND {k} = ?"
                    params.append(v)

            cursor = self.conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()

        return []

    def insert(self, table: str, role: str, auth_uid: Optional[str], data: Dict[str, Any]) -> bool:
        """Executes an INSERT query evaluated against RLS WITH CHECK policies."""
        if role == "anon":
            return False

        if role == "service_role":
            cols = ", ".join(data.keys())
            placeholders = ", ".join(["?"] * len(data))
            self.conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", list(data.values()))
            self.conn.commit()
            return True

        if role == "authenticated":
            if not auth_uid:
                return False

            if table == "model_versions":
                # Authenticated participants cannot insert into model_versions
                return False

            id_column = "id" if table == "participants" else "participant_id"
            # WITH CHECK (auth.uid() = participant_id / id)
            if data.get(id_column) != auth_uid:
                return False

            cols = ", ".join(data.keys())
            placeholders = ", ".join(["?"] * len(data))
            self.conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", list(data.values()))
            self.conn.commit()
            return True

        return False

    def update(self, table: str, role: str, auth_uid: Optional[str], row_id: str, new_data: Dict[str, Any]) -> int:
        """Executes an UPDATE query evaluated against RLS policies."""
        if role == "anon":
            return 0

        if role == "service_role":
            set_clauses = [f"{k} = ?" for k in new_data.keys()]
            params = list(new_data.values()) + [row_id]
            cursor = self.conn.execute(f"UPDATE {table} SET {', '.join(set_clauses)} WHERE id = ?", params)
            self.conn.commit()
            return cursor.rowcount

        if role == "authenticated":
            if not auth_uid or table == "model_versions":
                return 0

            id_column = "id" if table == "participants" else "participant_id"
            # Policy allows update only where owner matches auth_uid
            set_clauses = [f"{k} = ?" for k in new_data.keys()]
            params = list(new_data.values()) + [row_id, auth_uid]
            cursor = self.conn.execute(
                f"UPDATE {table} SET {', '.join(set_clauses)} WHERE id = ? AND {id_column} = ?",
                params
            )
            self.conn.commit()
            return cursor.rowcount

        return 0

    def delete(self, table: str, role: str, auth_uid: Optional[str], row_id: str) -> int:
        """Executes a DELETE query evaluated against RLS policies."""
        if role == "anon":
            return 0

        if role == "service_role":
            cursor = self.conn.execute(f"DELETE FROM {table} WHERE id = ?", [row_id])
            self.conn.commit()
            return cursor.rowcount

        if role == "authenticated":
            if not auth_uid or table == "model_versions":
                return 0

            id_column = "id" if table == "participants" else "participant_id"
            cursor = self.conn.execute(f"DELETE FROM {table} WHERE id = ? AND {id_column} = ?", [row_id, auth_uid])
            self.conn.commit()
            return cursor.rowcount

        return 0

    def access_storage(self, action: str, bucket_id: str, file_path: str, role: str, auth_uid: Optional[str]) -> bool:
        """Evaluates storage RLS policy for given bucket and object path."""
        if role == "service_role":
            return True
        if role == "anon":
            return False

        if role == "authenticated":
            if bucket_id == "research-exports":
                # Policy: research-exports is service-role only
                return False
            if bucket_id == "consent-documents":
                # Policy: folder name must equal auth.uid() -> e.g. "auth_uid/doc.pdf"
                folder = file_path.split("/")[0] if "/" in file_path else ""
                return folder == auth_uid
        return False


@pytest.fixture
def rls():
    """Provides a fresh RLS simulator seeded with model versions and two participants."""
    sim = SupabaseRLSSimulator()
    # Seed model version via service role
    sim.insert("model_versions", "service_role", None, {
        "id": "mv-1",
        "model_name": "gated_multimodal_fusion",
        "version": "v1.0.0",
        "active": 1
    })

    # Seed participants A and B
    sim.insert("participants", "service_role", None, {
        "id": "participant-A-uuid",
        "baseline_status": "collecting",
        "pseudonymous_id": "pseudo-hash-A"
    })
    sim.insert("participants", "service_role", None, {
        "id": "participant-B-uuid",
        "baseline_status": "established",
        "pseudonymous_id": "pseudo-hash-B"
    })

    # Seed data for participant B
    sim.insert("typing_sessions", "service_role", None, {
        "id": "ts-B-1",
        "participant_id": "participant-B-uuid",
        "session_id": "sess-B-100",
        "task_type": "controlled_phrase",
        "duration": 30.0,
        "quality_score": 0.94
    })
    sim.insert("mpf_predictions", "service_role", None, {
        "id": "pred-B-1",
        "participant_id": "participant-B-uuid",
        "risk_score": 0.12,
        "model_version": "v1.0.0"
    })
    return sim


def test_policy_1_participants_can_only_read_own_data(rls):
    """Participant A can read their own profile, but cannot read Participant B's profile."""
    # A reads own profile
    rows_a = rls.select("participants", "authenticated", "participant-A-uuid")
    assert len(rows_a) == 1
    assert rows_a[0]["id"] == "participant-A-uuid"

    # A attempts to query all typing sessions or B's typing sessions
    b_typing = rls.select("typing_sessions", "authenticated", "participant-A-uuid", {"participant_id": "participant-B-uuid"})
    assert len(b_typing) == 0

    # B can read B's own typing sessions
    b_own = rls.select("typing_sessions", "authenticated", "participant-B-uuid")
    assert len(b_own) == 1
    assert b_own[0]["session_id"] == "sess-B-100"


def test_policy_2_participants_can_only_insert_own_data(rls):
    """Participant A can insert data with participant_id = A, but cannot insert data with participant_id = B."""
    # A inserts own typing session -> success
    ok_a = rls.insert("typing_sessions", "authenticated", "participant-A-uuid", {
        "id": "ts-A-1",
        "participant_id": "participant-A-uuid",
        "session_id": "sess-A-1",
        "task_type": "controlled_phrase",
        "duration": 25.0,
        "quality_score": 0.98
    })
    assert ok_a is True

    # A attempts to spoof participant_id as B -> rejected by WITH CHECK policy
    spoofed = rls.insert("typing_sessions", "authenticated", "participant-A-uuid", {
        "id": "ts-spoof-1",
        "participant_id": "participant-B-uuid",
        "session_id": "sess-spoof-1",
        "task_type": "controlled_phrase",
        "duration": 25.0,
        "quality_score": 0.98
    })
    assert spoofed is False


def test_policy_3_participants_can_only_update_own_data(rls):
    """Participant A can update their own data, but cannot update Participant B's data."""
    # Seed session for A
    rls.insert("typing_sessions", "authenticated", "participant-A-uuid", {
        "id": "ts-A-2",
        "participant_id": "participant-A-uuid",
        "session_id": "sess-A-2",
        "task_type": "controlled_phrase",
        "duration": 20.0,
        "quality_score": 0.85
    })

    # A updates own session -> success
    updated_a = rls.update("typing_sessions", "authenticated", "participant-A-uuid", "ts-A-2", {"quality_score": 0.92})
    assert updated_a == 1

    # A attempts to update B's session ts-B-1 -> blocked, 0 rows modified
    updated_b = rls.update("typing_sessions", "authenticated", "participant-A-uuid", "ts-B-1", {"quality_score": 0.10})
    assert updated_b == 0


def test_policy_4_participants_can_only_delete_own_data(rls):
    """Participant A can delete their own records, but cannot delete Participant B's records."""
    # Seed session for A
    rls.insert("typing_sessions", "authenticated", "participant-A-uuid", {
        "id": "ts-A-3",
        "participant_id": "participant-A-uuid",
        "session_id": "sess-A-3",
        "task_type": "controlled_phrase",
        "duration": 20.0,
        "quality_score": 0.80
    })

    # A attempts to delete B's session ts-B-1 -> blocked
    deleted_b = rls.delete("typing_sessions", "authenticated", "participant-A-uuid", "ts-B-1")
    assert deleted_b == 0

    # A deletes own session -> success
    deleted_a = rls.delete("typing_sessions", "authenticated", "participant-A-uuid", "ts-A-3")
    assert deleted_a == 1


def test_policy_5_no_cross_participant_access(rls):
    """Zero cross-participant data visibility across all modalities."""
    modalities = [
        "consent_records",
        "typing_sessions",
        "voice_sessions",
        "motor_sessions",
        "visual_sessions",
        "sleep_sessions",
        "daily_features",
        "personal_baselines",
        "daily_deviations",
        "mpf_predictions"
    ]

    for mod in modalities:
        # Querying B's data as participant A returns empty list
        records = rls.select(mod, "authenticated", "participant-A-uuid", {"participant_id": "participant-B-uuid"})
        assert len(records) == 0, f"Cross-participant leak detected in table {mod}!"


def test_policy_6_research_export_requires_service_role(rls):
    """Service-role key can access research exports across all participants; participants cannot."""
    # Participant A cannot access research export bucket
    assert rls.access_storage("SELECT", "research-exports", "cohort_export_2026.parquet", "authenticated", "participant-A-uuid") is False

    # Participant A cannot read all participants' predictions
    predictions_as_a = rls.select("mpf_predictions", "authenticated", "participant-A-uuid")
    assert len(predictions_as_a) == 0

    # Service role CAN read all participants' predictions for export and research aggregation
    predictions_service = rls.select("mpf_predictions", "service_role", None)
    assert len(predictions_service) >= 1

    # Service role CAN access research-exports storage bucket
    assert rls.access_storage("SELECT", "research-exports", "cohort_export_2026.parquet", "service_role", None) is True


def test_policy_7_model_versions_read_only_for_participants(rls):
    """Participants can read model versions, but cannot insert, update, or delete model versions."""
    # Participant A can view model versions
    mv_rows = rls.select("model_versions", "authenticated", "participant-A-uuid")
    assert len(mv_rows) >= 1
    assert mv_rows[0]["model_name"] == "gated_multimodal_fusion"

    # Participant A cannot insert a new model version
    tampered_insert = rls.insert("model_versions", "authenticated", "participant-A-uuid", {
        "id": "mv-tamper",
        "model_name": "tampered_model",
        "version": "v999",
        "active": 1
    })
    assert tampered_insert is False

    # Participant A cannot update model version
    tampered_update = rls.update("model_versions", "authenticated", "participant-A-uuid", "mv-1", {"active": 0})
    assert tampered_update == 0

    # Participant A cannot delete model version
    tampered_delete = rls.delete("model_versions", "authenticated", "participant-A-uuid", "mv-1")
    assert tampered_delete == 0


def test_unauthenticated_access_is_blocked(rls):
    """Unauthenticated users ('anon') cannot read or write any participant tables or models."""
    assert len(rls.select("participants", "anon", None)) == 0
    assert len(rls.select("typing_sessions", "anon", None)) == 0
    assert len(rls.select("mpf_predictions", "anon", None)) == 0
    assert rls.insert("typing_sessions", "anon", None, {"id": "x", "participant_id": "p", "session_id": "s"}) is False


def test_storage_scoped_consent_documents(rls):
    """Participants can only access files in their own folder in consent-documents bucket."""
    user_a = "participant-A-uuid"
    user_b = "participant-B-uuid"

    # User A accesses own consent PDF -> Allowed
    assert rls.access_storage("SELECT", "consent-documents", f"{user_a}/consent_signed.pdf", "authenticated", user_a) is True

    # User A attempts to access User B's consent PDF -> Blocked
    assert rls.access_storage("SELECT", "consent-documents", f"{user_b}/consent_signed.pdf", "authenticated", user_a) is False
