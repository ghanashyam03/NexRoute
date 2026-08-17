import random
import logging
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)

# Note on Codebase Audit:
# An audit of backend/app/ (including optimizer.py and traffic_manager.py)
# confirms that all random number generation relies either on Python's standard `random`
# module or NumPy's global random state (`np.random`).
# No local `np.random.default_rng()` or custom `np.random.Generator` objects
# are currently constructed in backend/app/. If any Generator objects are introduced
# in future work, ensure they are seeded using seeds derived from `set_global_seed`.


def set_global_seed(seed: Optional[int]) -> None:
    """
    Set the global random seed for Python's `random` module and NumPy's RNG.
    If seed is None, do nothing (leaving RNGs nondeterministic).
    """
    if seed is None:
        logger.info("No random seed provided; leaving RNGs in nondeterministic state.")
        return

    logger.info(f"Setting global random seed to: {seed}")
    random.seed(seed)
    np.random.seed(seed)
