import pytest


def test_imports():
    """Verify that all core Phase 0 modules are importable without errors."""
    import src
    import src.config
    import src.logging_utils
    import src.seeds
    import src.healthcheck

    assert src is not None
    assert src.config is not None
    assert src.logging_utils is not None
    assert src.seeds is not None
    assert src.healthcheck is not None
