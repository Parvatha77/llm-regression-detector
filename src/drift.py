"""
Drift detection: EWMA-based sliding window to flag gradual pass-rate degradation.
"""

from collections import deque
from dataclasses import dataclass


@dataclass
class DriftResult:
    """Result of a drift check over a sequence of run pass rates."""
    ewma: float            # current smoothed value
    delta_from_start: float  # EWMA now vs first EWMA in window
    is_drifting: bool
    status: str            # "ok" or "warning"


def check_drift(
    pass_rates: list[float],
    alpha: float = 0.3,
    threshold: float = 0.05,
    window: int = 7,
) -> DriftResult:
    """
    Run an EWMA (Exponentially Weighted Moving Average) over the last `window`
    pass-rate values and flag drift when the smoothed value has dropped more
    than `threshold` from its initial value in the window.

    Args:
        pass_rates: Chronological list of pass-rate floats (0.0–1.0).
        alpha:      EWMA smoothing factor (0 < alpha <= 1).
        threshold:  Fraction drop that triggers a "warning" (default 5%).
        window:     Maximum history length to consider.

    Returns:
        DriftResult with EWMA, delta, and status.
    """
    if not pass_rates:
        return DriftResult(ewma=0.0, delta_from_start=0.0, is_drifting=False, status="ok")

    recent = list(deque(pass_rates, maxlen=window))

    ewma = recent[0]
    first_ewma = ewma
    for rate in recent[1:]:
        ewma = alpha * rate + (1 - alpha) * ewma

    delta = ewma - first_ewma
    is_drifting = delta < -threshold

    return DriftResult(
        ewma=round(ewma, 4),
        delta_from_start=round(delta, 4),
        is_drifting=is_drifting,
        status="warning" if is_drifting else "ok",
    )

