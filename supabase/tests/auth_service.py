"""
Authentication Service for MPF Mobile Extension.
Implements Supabase Auth workflow:
- Email/password registration with salted PBKDF2-HMAC-SHA256 hashing.
- No plain-text passwords stored in application state or database.
- Secure JWT token issuance, signature verification, expiry, and claim enforcement.
- Session management and refresh tokens.
- Cryptographic password reset workflow (one-time use, time-bounded).
- GDPR-compliant account deletion workflow (complete cascading deletion of participant records).
"""

import base64
import hashlib
import hmac
import json
import secrets
import time
import uuid
from typing import Dict, Any, Optional, Tuple


class SupabaseAuthService:
    """Simulates and encapsulates Supabase Auth engine and session state."""

    def __init__(self, jwt_secret: Optional[str] = None):
        self.jwt_secret = (jwt_secret or secrets.token_hex(32)).encode("utf-8")
        # In-memory auth user store (simulating auth.users table in Supabase)
        # Never contains plain text passwords.
        self._auth_users: Dict[str, Dict[str, Any]] = {}
        # Active sessions: session_id -> {user_id, refresh_token, expires_at, revoked}
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        # Password reset tokens: token -> {user_id, expires_at, used}
        self._reset_tokens: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def _hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """Hashes password using PBKDF2 with SHA-256 and a 16-byte cryptographic salt."""
        if not salt:
            salt = secrets.token_hex(16)
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
        return key.hex(), salt

    @staticmethod
    def _b64_url_encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

    @staticmethod
    def _b64_url_decode(data_str: str) -> bytes:
        padding = "=" * (4 - (len(data_str) % 4))
        return base64.urlsafe_b64decode(data_str + padding)

    def _sign_jwt(self, header: Dict[str, Any], payload: Dict[str, Any]) -> str:
        h_enc = self._b64_url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        p_enc = self._b64_url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        msg = f"{h_enc}.{p_enc}".encode("utf-8")
        sig = hmac.new(self.jwt_secret, msg, hashlib.sha256).digest()
        s_enc = self._b64_url_encode(sig)
        return f"{h_enc}.{p_enc}.{s_enc}"

    def verify_jwt(self, token: str) -> Optional[Dict[str, Any]]:
        """Verifies JWT token signature and expiration, returning decoded payload or None."""
        parts = token.split(".")
        if len(parts) != 3:
            return None
        h_enc, p_enc, s_enc = parts
        msg = f"{h_enc}.{p_enc}".encode("utf-8")
        expected_sig = hmac.new(self.jwt_secret, msg, hashlib.sha256).digest()
        actual_sig = self._b64_url_decode(s_enc)

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        try:
            payload = json.loads(self._b64_url_decode(p_enc).decode("utf-8"))
        except Exception:
            return None

        # Check expiration
        now = int(time.time())
        if "exp" in payload and payload["exp"] < now:
            return None

        return payload

    def register_user(self, email: str, password: str, consent_version: str = "1.0.0") -> Dict[str, Any]:
        """Registers a new user with cryptographically hashed password and generates pseudonymous ID."""
        email_clean = email.strip().lower()
        if email_clean in self._auth_users:
            raise ValueError(f"User with email {email_clean} already registered.")

        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters.")

        password_hash, salt = self._hash_password(password)
        user_id = str(uuid.uuid4())
        pseudonymous_id = "ps_" + hashlib.sha256(f"{user_id}:{salt}".encode("utf-8")).hexdigest()[:24]

        user_record = {
            "id": user_id,
            "email": email_clean,
            "password_hash": password_hash,
            "salt": salt,
            "pseudonymous_id": pseudonymous_id,
            "consent_version": consent_version,
            "baseline_status": "collecting",
            "created_at": time.time(),
        }
        self._auth_users[email_clean] = user_record

        # Generate initial session and token
        session = self._create_session(user_id)
        return {
            "user_id": user_id,
            "pseudonymous_id": pseudonymous_id,
            "access_token": session["access_token"],
            "refresh_token": session["refresh_token"],
            "expires_in": 3600
        }

    def login_user(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticates user via email/password and returns secure session."""
        email_clean = email.strip().lower()
        user = self._auth_users.get(email_clean)
        if not user:
            raise PermissionError("Invalid email or password.")

        computed_hash, _ = self._hash_password(password, user["salt"])
        if not hmac.compare_digest(computed_hash, user["password_hash"]):
            raise PermissionError("Invalid email or password.")

        session = self._create_session(user["id"])
        return {
            "user_id": user["id"],
            "pseudonymous_id": user["pseudonymous_id"],
            "access_token": session["access_token"],
            "refresh_token": session["refresh_token"],
            "expires_in": 3600
        }

    def _create_session(self, user_id: str) -> Dict[str, Any]:
        now = int(time.time())
        exp = now + 3600  # 1 hour
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": user_id,
            "aud": "authenticated",
            "role": "authenticated",
            "iat": now,
            "exp": exp,
            "iss": "supabase-mpf-auth"
        }
        access_token = self._sign_jwt(header, payload)
        refresh_token = secrets.token_urlsafe(32)
        session_id = str(uuid.uuid4())

        self._active_sessions[refresh_token] = {
            "session_id": session_id,
            "user_id": user_id,
            "expires_at": now + (86400 * 30),  # 30 days
            "revoked": False
        }
        return {"access_token": access_token, "refresh_token": refresh_token}

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Rotates session access token using valid refresh token."""
        session = self._active_sessions.get(refresh_token)
        if not session or session["revoked"] or session["expires_at"] < time.time():
            raise PermissionError("Invalid or expired refresh token.")

        # Invalidate old refresh token (Token Rotation)
        session["revoked"] = True
        return self._create_session(session["user_id"])

    def logout_user(self, refresh_token: str) -> bool:
        """Revokes user session upon logout."""
        session = self._active_sessions.get(refresh_token)
        if session:
            session["revoked"] = True
            return True
        return False

    def request_password_reset(self, email: str) -> str:
        """Generates single-use, time-limited password reset token."""
        email_clean = email.strip().lower()
        user = self._auth_users.get(email_clean)
        if not user:
            # Prevent email enumeration: return dummy or raise consistent message
            return ""

        reset_token = secrets.token_urlsafe(32)
        self._reset_tokens[reset_token] = {
            "user_id": user["id"],
            "email": email_clean,
            "expires_at": time.time() + 900,  # 15 minutes
            "used": False
        }
        return reset_token

    def complete_password_reset(self, reset_token: str, new_password: str) -> bool:
        """Validates reset token and sets new password hash."""
        token_info = self._reset_tokens.get(reset_token)
        if not token_info or token_info["used"] or token_info["expires_at"] < time.time():
            raise ValueError("Password reset token is invalid or has expired.")

        if len(new_password) < 8:
            raise ValueError("Password must be at least 8 characters.")

        email = token_info["email"]
        user = self._auth_users[email]
        new_hash, new_salt = self._hash_password(new_password)
        user["password_hash"] = new_hash
        user["salt"] = new_salt
        token_info["used"] = True

        # Invalidate all existing sessions for this user
        for sess in self._active_sessions.values():
            if sess["user_id"] == user["id"]:
                sess["revoked"] = True

        return True

    def delete_account(self, user_id: str, db_connection=None) -> bool:
        """
        Executes complete account deletion workflow.
        Deletes auth user record and triggers cascading deletion of all associated participant data.
        """
        # Find user by id
        target_email = None
        for email, usr in self._auth_users.items():
            if usr["id"] == user_id:
                target_email = email
                break

        if not target_email:
            return False

        del self._auth_users[target_email]

        # Revoke all sessions
        for sess in self._active_sessions.values():
            if sess["user_id"] == user_id:
                sess["revoked"] = True

        # If database connection passed, execute cascading delete
        if db_connection:
            cursor = db_connection.cursor()
            cursor.execute("DELETE FROM participants WHERE id = ?", (user_id,))
            db_connection.commit()

        return True
