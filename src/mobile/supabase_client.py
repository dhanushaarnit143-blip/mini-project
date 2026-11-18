"""
Supabase Client Wrapper for MPF Mobile Extension.

Provides connection management, client initialization, singleton access,
and live connectivity health checks.
"""

import os
import logging
from typing import Optional, Any
from pathlib import Path
from dotenv import load_dotenv

# Ensure environment variables are loaded from the root .env
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

try:
    from supabase import create_client, Client
except ImportError:
    Client = Any  # type: ignore
    create_client = None  # type: ignore

logger = logging.getLogger("mpf.mobile.supabase_client")

_anon_client_instance: Optional[Any] = None
_service_role_client_instance: Optional[Any] = None


def init_supabase(
    url: Optional[str] = None,
    key: Optional[str] = None,
    use_service_role: bool = False,
) -> Any:
    """
    Initialize and cache a Supabase client instance.

    Args:
        url: Supabase project URL. If None, reads SUPABASE_URL from environment.
        key: API key. If None, reads SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY.
        use_service_role: If True, uses the service role key for admin tasks.

    Returns:
        Configured Supabase Client instance.
    """
    global _anon_client_instance, _service_role_client_instance

    target_url = url or os.getenv("SUPABASE_URL")
    if not target_url:
        raise ValueError("SUPABASE_URL must be provided or configured in environment variables.")

    if key is None:
        if use_service_role:
            target_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        else:
            target_key = os.getenv("SUPABASE_ANON_KEY")
    else:
        target_key = key

    if not target_key:
        raise ValueError("Supabase API key must be provided or configured in environment variables.")

    if create_client is None:
        raise ImportError("supabase package is not installed. Run `pip install supabase`.")

    client = create_client(target_url, target_key)

    if use_service_role:
        _service_role_client_instance = client
    else:
        _anon_client_instance = client

    logger.info("Supabase client initialized successfully (service_role=%s)", use_service_role)
    return client


def get_client(use_service_role: bool = False) -> Any:
    """
    Retrieve an active Supabase client singleton instance.
    Initializes a new instance if not already cached.

    Args:
        use_service_role: Whether to retrieve the service_role administrative client.

    Returns:
        Supabase Client instance.
    """
    global _anon_client_instance, _service_role_client_instance

    if use_service_role:
        if _service_role_client_instance is None:
            return init_supabase(use_service_role=True)
        return _service_role_client_instance
    else:
        if _anon_client_instance is None:
            return init_supabase(use_service_role=False)
        return _anon_client_instance


def test_connection(client: Optional[Any] = None) -> bool:
    """
    Execute a lightweight connectivity health check against Supabase.

    Args:
        client: Optional Supabase client instance. If None, uses get_client().

    Returns:
        True if connection and query succeed, False otherwise.
    """
    try:
        active_client = client or get_client()
        # Query model_versions table (read-only table accessible by authenticated/anon)
        response = active_client.table("model_versions").select("id").limit(1).execute()
        return response is not None and hasattr(response, "data")
    except Exception as exc:
        logger.warning("Supabase connection check failed: %s", exc)
        return False
