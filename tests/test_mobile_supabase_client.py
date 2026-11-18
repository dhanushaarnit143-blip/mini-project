"""
Tests for src.mobile.supabase_client module.
Validates init_supabase, get_client, and test_connection.
"""

import os
from unittest.mock import MagicMock
import pytest

from src.mobile import supabase_client


def test_init_and_get_client():
    """Verify init_supabase and get_client return client instances."""
    client = supabase_client.get_client()
    assert client is not None
    assert hasattr(client, "table") or hasattr(client, "supabase_url")


def test_connectivity_check_live_or_mocked():
    """Verify test_connection returns a boolean."""
    # Test with mock client
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.data = [{"id": "mock-id"}]
    mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = mock_resp

    result = supabase_client.test_connection(mock_client)
    assert result is True

    # Test error handling
    failing_client = MagicMock()
    failing_client.table.return_value.select.return_value.limit.return_value.execute.side_effect = Exception("Network down")
    assert supabase_client.test_connection(failing_client) is False
