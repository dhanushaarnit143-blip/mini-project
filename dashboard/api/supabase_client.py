"""
Supabase client helper for FastAPI backend.
Project: mini project
"""

import os
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("mpf.supabase")

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://trtvdmgswouirfaqyrdk.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRydHZkbWdzd291aXJmYXF5cmRrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTAxNjM3OTAsImV4cCI6MjEwNTczOTc5MH0.wxyGhyELZJy_-R2X4xqDaIsgofDbdQJtwZWjboCOKrM")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", SUPABASE_ANON_KEY)

_client = None

def get_supabase():
    """Initializes or returns cached Supabase client."""
    global _client
    if _client is None:
        try:
            from supabase import create_client, Client
            key = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY
            _client = create_client(SUPABASE_URL, key)
            logger.info("Supabase Python client initialized successfully.")
        except Exception as e:
            logger.warning(f"Could not initialize Supabase client: {e}")
            _client = None
    return _client


def get_cohort_participants() -> List[Dict[str, Any]]:
    """Fetch cohort participants from Supabase."""
    client = get_supabase()
    if not client:
        return []
    try:
        res = client.table("cohort_participants").select("*").order("risk_index", desc=True).execute()
        return res.data or []
    except Exception as e:
        logger.error(f"Error reading cohort from Supabase: {e}")
        return []


def insert_cohort_participant(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Insert a new participant into Supabase cohort."""
    client = get_supabase()
    if not client:
        return None
    try:
        res = client.table("cohort_participants").insert(data).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(f"Error inserting participant into Supabase: {e}")
        return None


def insert_assessment_and_result(assessment_data: Dict[str, Any], result_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Saves assessment record and optional fusion results into Supabase."""
    client = get_supabase()
    if not client:
        return None
    try:
        res_assess = client.table("assessments").insert(assessment_data).execute()
        if not res_assess.data:
            return None
        assessment_id = res_assess.data[0]["id"]

        if result_data:
            result_data["assessment_id"] = assessment_id
            client.table("fusion_results").insert(result_data).execute()

        return assessment_id
    except Exception as e:
        logger.error(f"Error saving assessment/fusion to Supabase: {e}")
        return None
