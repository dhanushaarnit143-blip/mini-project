import sys
import pytest

@pytest.fixture(autouse=True)
def ensure_clean_supabase_module():
    """Ensures local directory 'supabase' doesn't shadow the site-packages 'supabase' library."""
    if "supabase" in sys.modules and not hasattr(sys.modules["supabase"], "create_client"):
        del sys.modules["supabase"]
    yield
    if "supabase" in sys.modules and not hasattr(sys.modules["supabase"], "create_client"):
        del sys.modules["supabase"]
