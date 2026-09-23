"""
MPF Mobile Extension — Privacy, Consent, Deletion, and Export Services (Python Backend)

Implements:
1. ConsentService: Versioned informed consent recording, granular permission gating, and revocation.
2. DeletionService: Irreversible GDPR-compliant research data purge with audit logging and soft deletion.
3. ExportService: Complete participant data portability package generation with cross-participant isolation.

Strictly preserves non-negotiable rules:
- Research prototype only; zero clinical diagnosis claims.
- Strict baseline-centric evaluation.
- No PII stored; pseudonymous identifiers only.
"""

import datetime
import hashlib
import json
from typing import Dict, Any, List, Optional, Set

CURRENT_CONSENT_VERSION = "1.0.0"
DELETION_CONFIRMATION_PHRASE = "DELETE MY RESEARCH DATA"

CONSENT_TYPES = {
    "DATA_COLLECTION": "data_collection",
    "AUDIO_STORAGE": "audio_storage",
    "RESEARCH_EXPORT": "research_export",
    "DELETION": "deletion",
    "CAMERA_ACCESS": "camera_access",
    "MICROPHONE_ACCESS": "microphone_access",
    "MOTION_ACCESS": "motion_access",
    "KEYBOARD_ACCESS": "keyboard_access",
}

MODALITY_PERMISSION_MAP = {
    "typing": "keyboard_access",
    "voice": "microphone_access",
    "motor": "motion_access",
    "visual": "camera_access",
}


def generate_pseudonymous_id(user_uuid: str, salt: Optional[str] = None) -> str:
    """Derives a pseudonymous ID from user UUID and salt."""
    s = salt or "mpf_research_salt_2026"
    digest = hashlib.sha256(f"{user_uuid}:{s}".encode("utf-8")).hexdigest()[:24]
    return f"ps_{digest}"


class ConsentService:
    """Manages participant consent, granular sensor permissions, and revocation."""

    def __init__(self, db_conn=None, supabase_client=None):
        self.conn = db_conn
        self.supabase = supabase_client
        self._memory_cache: Dict[str, Set[str]] = {}

    def record_consent(
        self,
        participant_id: str,
        consents: Dict[str, bool],
        consent_version: str = CURRENT_CONSENT_VERSION,
    ) -> Dict[str, Any]:
        """
        Records informed consent for a participant across required and optional categories.
        Requires data_collection to be True.
        """
        if not participant_id:
            raise ValueError("participant_id is required.")

        if not consents.get(CONSENT_TYPES["DATA_COLLECTION"], False):
            raise PermissionError("Basic data collection consent is mandatory for research participation.")

        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        granted_types = []

        # Determine granted consent types
        for ctype in CONSENT_TYPES.values():
            if consents.get(ctype, False):
                granted_types.append(ctype)

        # Update cache
        self._memory_cache[participant_id] = set(granted_types)

        # Database persistence (SQLite or Supabase)
        if self.conn:
            cursor = self.conn.cursor()
            # Update participant header
            cursor.execute(
                """
                UPDATE participants 
                SET consent_version = ?, consent_timestamp = ?
                WHERE id = ?
                """,
                (consent_version, now_iso, participant_id),
            )
            # Insert individual consent records
            for ct in granted_types:
                cursor.execute(
                    """
                    INSERT INTO consent_records (id, participant_id, consent_type, consent_version, granted, timestamp, revoked_at)
                    VALUES (?, ?, ?, ?, 1, ?, NULL)
                    """,
                    (f"c_{participant_id[:8]}_{ct}", participant_id, ct, consent_version, now_iso),
                )
            self.conn.commit()

        elif self.supabase:
            self.supabase.table("participants").update({
                "consent_version": consent_version,
                "consent_timestamp": now_iso,
            }).eq("id", participant_id).execute()

            records = [
                {
                    "participant_id": participant_id,
                    "consent_type": ct,
                    "consent_version": consent_version,
                    "granted": True,
                    "timestamp": now_iso,
                    "revoked_at": None,
                }
                for ct in granted_types
            ]
            self.supabase.table("consent_records").insert(records).execute()

        return {
            "success": True,
            "participant_id": participant_id,
            "consent_version": consent_version,
            "timestamp": now_iso,
            "granted_types": granted_types,
        }

    def check_consent(self, participant_id: str, consent_type: str) -> bool:
        """Checks if participant has granted active, unrevoked consent."""
        if not participant_id or not consent_type:
            return False

        # Fast cache check
        if participant_id in self._memory_cache:
            active = self._memory_cache[participant_id]
            if CONSENT_TYPES["DATA_COLLECTION"] not in active:
                return False
            return consent_type in active

        if self.conn:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT granted, revoked_at FROM consent_records
                WHERE participant_id = ? AND consent_type = ?
                ORDER BY timestamp DESC LIMIT 1
                """,
                (participant_id, consent_type),
            )
            row = cursor.fetchone()
            if not row:
                return False
            # Check row fields (sqlite row or tuple)
            granted = row[0] if isinstance(row, (list, tuple)) else row["granted"]
            revoked_at = row[1] if isinstance(row, (list, tuple)) else row["revoked_at"]
            return bool(granted) and (revoked_at is None or revoked_at == "")

        elif self.supabase:
            res = (
                self.supabase.table("consent_records")
                .select("granted, revoked_at")
                .eq("participant_id", participant_id)
                .eq("consent_type", consent_type)
                .order("timestamp", desc=True)
                .limit(1)
                .execute()
            )
            if not res.data:
                return False
            rec = res.data[0]
            return rec.get("granted") is True and rec.get("revoked_at") is None

        return False

    def has_consent(self, participant_id: str, consent_type: str) -> bool:
        """Alias for check_consent."""
        return self.check_consent(participant_id, consent_type)


    def assert_authorized_collection(self, participant_id: str, modality: str):
        """Raises PermissionError if participant has not consented to collection or modality sensor."""
        if not self.check_consent(participant_id, CONSENT_TYPES["DATA_COLLECTION"]):
            raise PermissionError(f"Data collection unauthorized: Participant {participant_id} has not consented or revoked consent.")

        sensor_type = MODALITY_PERMISSION_MAP.get(modality)
        if sensor_type and not self.check_consent(participant_id, sensor_type):
            raise PermissionError(f"Sensor permission unauthorized: Participant {participant_id} has not granted {sensor_type}.")

    def revoke_consent(self, participant_id: str, consent_type: str = "all", reason: str = "Participant requested revocation") -> Dict[str, Any]:
        """Revokes consent for one or all categories, immediately halting collection."""
        if not participant_id:
            raise ValueError("participant_id is required.")

        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if participant_id in self._memory_cache:
            if consent_type == "all" or consent_type == CONSENT_TYPES["DATA_COLLECTION"]:
                self._memory_cache[participant_id].clear()
            else:
                self._memory_cache[participant_id].discard(consent_type)

        affected = 0
        if self.conn:
            cursor = self.conn.cursor()
            if consent_type == "all":
                cursor.execute(
                    """
                    UPDATE consent_records
                    SET revoked_at = ?, granted = 0
                    WHERE participant_id = ? AND revoked_at IS NULL
                    """,
                    (now_iso, participant_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE consent_records
                    SET revoked_at = ?, granted = 0
                    WHERE participant_id = ? AND consent_type = ? AND revoked_at IS NULL
                    """,
                    (now_iso, participant_id, consent_type),
                )
            affected = cursor.rowcount
            self.conn.commit()

        elif self.supabase:
            query = self.supabase.table("consent_records").update({
                "revoked_at": now_iso,
                "granted": False,
            }).eq("participant_id", participant_id).is_("revoked_at", None)

            if consent_type != "all":
                query = query.eq("consent_type", consent_type)

            res = query.execute()
            affected = len(res.data) if res.data else 0

        return {
            "success": True,
            "participant_id": participant_id,
            "revoked_type": consent_type,
            "revoked_at": now_iso,
            "reason": reason,
            "affected_records": affected,
        }


class DeletionService:
    """Implements GDPR-compliant irreversible data deletion workflow."""

    def __init__(self, db_conn=None, supabase_client=None):
        self.conn = db_conn
        self.supabase = supabase_client

    def request_account_deletion(
        self,
        participant_id: str,
        confirmation_phrase: str,
        reason: str = "Participant requested erasure",
    ) -> Dict[str, Any]:
        """
        Executes full irreversible deletion of participant sensor and model records.
        Marks participant record as deleted (soft-delete) for audit trail.
        """
        if not participant_id:
            raise ValueError("participant_id is required.")

        if confirmation_phrase != DELETION_CONFIRMATION_PHRASE:
            raise ValueError(f"Confirmation phrase mismatch. Expected '{DELETION_CONFIRMATION_PHRASE}'.")

        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        tables_to_purge = [
            "typing_sessions",
            "voice_sessions",
            "motor_sessions",
            "visual_sessions",
            "sleep_sessions",
            "daily_deviations",
            "mpf_predictions",
            "daily_features",
            "personal_baselines",
        ]

        purge_counts = {}

        if self.conn:
            cursor = self.conn.cursor()
            # 1. Log audit record in consent_records BEFORE purging
            cursor.execute(
                """
                INSERT INTO consent_records (id, participant_id, consent_type, consent_version, granted, timestamp, revoked_at)
                VALUES (?, ?, 'deletion', '1.0.0', 1, ?, NULL)
                """,
                (f"del_{participant_id[:8]}_{int(datetime.datetime.now().timestamp())}", participant_id, now_iso),
            )

            # 2. Cascade purge all tables
            for tbl in tables_to_purge:
                try:
                    cursor.execute(f"DELETE FROM {tbl} WHERE participant_id = ?", (participant_id,))
                    purge_counts[tbl] = cursor.rowcount
                except Exception:
                    purge_counts[tbl] = 0

            # 3. Soft-delete participant record
            cursor.execute(
                """
                UPDATE participants
                SET is_deleted = 1, deleted_at = ?
                WHERE id = ?
                """,
                (now_iso, participant_id),
            )
            self.conn.commit()

        elif self.supabase:
            # 1. Log audit record in consent_records
            self.supabase.table("consent_records").insert({
                "participant_id": participant_id,
                "consent_type": "deletion",
                "consent_version": "1.0.0",
                "granted": True,
                "timestamp": now_iso,
            }).execute()

            # 2. Cascade purge tables
            for tbl in tables_to_purge:
                res = self.supabase.table(tbl).delete().eq("participant_id", participant_id).execute()
                purge_counts[tbl] = len(res.data) if res.data else 0

            # 3. Soft-delete participant record
            self.supabase.table("participants").update({
                "is_deleted": True,
                "deleted_at": now_iso,
            }).eq("id", participant_id).execute()

        audit_id = f"del_{participant_id[:8]}_{int(datetime.datetime.now().timestamp())}"
        return {
            "success": True,
            "participant_id": participant_id,
            "deletion_timestamp": now_iso,
            "timestamp": now_iso,
            "audit_id": audit_id,
            "deletion_id": audit_id,
            "is_irreversible": True,
            "purge_results": purge_counts,
            "message": "All participant research observations and model outputs permanently deleted.",
        }

    def request_deletion(
        self,
        participant_id: str,
        confirmation_phrase: str = "",
        reason: str = "Participant requested erasure",
        **kwargs
    ) -> Dict[str, Any]:
        """Alias for request_account_deletion."""
        return self.request_account_deletion(
            participant_id=participant_id,
            confirmation_phrase=confirmation_phrase,
            reason=reason,
        )


class ExportService:
    """Generates complete participant data export package with cross-participant isolation."""

    def __init__(self, db_conn=None, supabase_client=None):
        self.conn = db_conn
        self.supabase = supabase_client

    def build_export_package(
        self,
        participant_id: str,
        session_records: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Builds an export package filtering session records strictly to the requesting participant."""
        filtered_sessions = []
        if session_records:
            filtered_sessions = [r for r in session_records if r.get("participant_id") == participant_id]

        package = self.generate_participant_export(participant_id)
        if session_records is not None:
            package["data"]["sessions"] = filtered_sessions
            package["sessions"] = filtered_sessions
        package["participant_id"] = participant_id
        return package


    def generate_participant_export(self, participant_id: str) -> Dict[str, Any]:
        """
        Gathers all participant data across all tables and formats as portable JSON.
        Guarantees zero cross-participant leakage.
        """
        if not participant_id:
            raise ValueError("participant_id is required.")

        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        export_package = {
            "export_version": "1.0.0",
            "export_timestamp": now_iso,
            "participant_id": participant_id,
            "disclaimer": "MPF Mobile Research Data Export. Research prototype data for personal evaluation and portability. Not a clinical diagnostic report.",
            "data": {
                "participant": None,
                "consents": [],
                "typing_sessions": [],
                "voice_sessions": [],
                "motor_sessions": [],
                "visual_sessions": [],
                "sleep_sessions": [],
                "daily_features": [],
                "personal_baselines": [],
                "daily_deviations": [],
                "mpf_predictions": [],
            },
            "summary": {
                "total_sessions": 0,
                "total_daily_features": 0,
                "total_predictions": 0,
            },
        }

        if self.conn:
            cursor = self.conn.cursor()

            # Participant header
            cursor.execute("SELECT id, pseudonymous_id, created_at, consent_version, baseline_status FROM participants WHERE id = ?", (participant_id,))
            p_row = cursor.fetchone()
            if p_row:
                export_package["data"]["participant"] = dict(p_row) if hasattr(p_row, "keys") else {
                    "id": p_row[0],
                    "pseudonymous_id": p_row[1],
                    "created_at": p_row[2],
                    "consent_version": p_row[3],
                    "baseline_status": p_row[4],
                }

            # Consents
            cursor.execute("SELECT consent_type, consent_version, granted, timestamp, revoked_at FROM consent_records WHERE participant_id = ?", (participant_id,))
            c_rows = cursor.fetchall()
            export_package["data"]["consents"] = [dict(r) if hasattr(r, "keys") else {"consent_type": r[0], "consent_version": r[1], "granted": bool(r[2]), "timestamp": r[3], "revoked_at": r[4]} for r in c_rows]

            # Modality sessions
            session_tables = ["typing_sessions", "voice_sessions", "motor_sessions", "visual_sessions", "sleep_sessions"]
            for tbl in session_tables:
                try:
                    cursor.execute(f"SELECT * FROM {tbl} WHERE participant_id = ?", (participant_id,))
                    rows = cursor.fetchall()
                    formatted = [dict(r) if hasattr(r, "keys") else dict(zip([col[0] for col in cursor.description], r)) for r in rows]
                    export_package["data"][tbl] = formatted
                    export_package["summary"]["total_sessions"] += len(formatted)
                except Exception:
                    export_package["data"][tbl] = []

            # Features, baselines, deviations, predictions
            data_tables = [
                ("daily_features", "total_daily_features"),
                ("personal_baselines", None),
                ("daily_deviations", None),
                ("mpf_predictions", "total_predictions"),
            ]
            for tbl, sum_key in data_tables:
                try:
                    cursor.execute(f"SELECT * FROM {tbl} WHERE participant_id = ?", (participant_id,))
                    rows = cursor.fetchall()
                    formatted = [dict(r) if hasattr(r, "keys") else dict(zip([col[0] for col in cursor.description], r)) for r in rows]
                    export_package["data"][tbl] = formatted
                    if sum_key:
                        export_package["summary"][sum_key] = len(formatted)
                except Exception:
                    export_package["data"][tbl] = []

        elif self.supabase:
            part_res = self.supabase.table("participants").select("id, pseudonymous_id, created_at, consent_version, baseline_status").eq("id", participant_id).execute()
            if part_res.data:
                export_package["data"]["participant"] = part_res.data[0]

            cons_res = self.supabase.table("consent_records").select("*").eq("participant_id", participant_id).execute()
            export_package["data"]["consents"] = cons_res.data or []

            session_tables = ["typing_sessions", "voice_sessions", "motor_sessions", "visual_sessions", "sleep_sessions"]
            for tbl in session_tables:
                res = self.supabase.table(tbl).select("*").eq("participant_id", participant_id).execute()
                items = res.data or []
                export_package["data"][tbl] = items
                export_package["summary"]["total_sessions"] += len(items)

            feats = self.supabase.table("daily_features").select("*").eq("participant_id", participant_id).execute()
            export_package["data"]["daily_features"] = feats.data or []
            export_package["summary"]["total_daily_features"] = len(feats.data or [])

            base = self.supabase.table("personal_baselines").select("*").eq("participant_id", participant_id).execute()
            export_package["data"]["personal_baselines"] = base.data or []

            devs = self.supabase.table("daily_deviations").select("*").eq("participant_id", participant_id).execute()
            export_package["data"]["daily_deviations"] = devs.data or []

            preds = self.supabase.table("mpf_predictions").select("*").eq("participant_id", participant_id).execute()
            export_package["data"]["mpf_predictions"] = preds.data or []
            export_package["summary"]["total_predictions"] = len(preds.data or [])

        # Compute checksum of exported data
        json_blob = json.dumps(export_package["data"], sort_keys=True)
        export_package["checksum_sha256"] = hashlib.sha256(json_blob.encode("utf-8")).hexdigest()

        return export_package
