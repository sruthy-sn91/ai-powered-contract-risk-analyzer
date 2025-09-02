from __future__ import annotations
import numpy as np

class CalibrationService:
    def __init__(self):
        self.residuals = np.array([0.05, -0.05])  # default tiny band

    def fit(self, y_true, y_pred):
        y_true = np.asarray(y_true, dtype=float)
        y_pred = np.asarray(y_pred, dtype=float)
        res = y_true - y_pred
        self.residuals = res
        return {
            "n": int(len(res)),
            "mean_residual": float(np.mean(res)),
            "p90_abs_error": float(np.percentile(np.abs(res), 90))
        }

    def interval(self, y_pred: float, alpha: float = 0.1):
        # conformal-style: quantile of absolute residuals
        q = np.percentile(np.abs(self.residuals), 100 * (1 - alpha))
        lo = float(max(0.0, y_pred - q))
        hi = float(min(1.0, y_pred + q))
        return lo, hi
