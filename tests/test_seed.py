import pytest
import random
import numpy as np
from src.seeds import set_global_seed


def test_set_global_seed_reproducibility():
    """Verify that set_global_seed produces deterministic pseudo-random sequences in random and numpy."""
    set_global_seed(42)
    py_val_1 = random.random()
    np_val_1 = np.random.rand(5)

    set_global_seed(42)
    py_val_2 = random.random()
    np_val_2 = np.random.rand(5)

    assert py_val_1 == py_val_2
    np.testing.assert_array_equal(np_val_1, np_val_2)
