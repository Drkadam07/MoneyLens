import math
from decimal import Decimal
from typing import Any, Dict, List, Optional
import numpy as np
from sklearn.ensemble import IsolationForest


class AnomalyDetector:
    """Detects spending anomalies using statistical baselines (Z-Score, MAD) and IsolationForest."""

    def __init__(self, z_score_threshold: float = 2.5, contamination: float = 0.05):
        self.z_score_threshold = z_score_threshold
        self.contamination = contamination

    def detect_amount_outliers_zscore(
        self, amounts: List[float], descriptions: List[str]
    ) -> List[Dict[str, Any]]:
        """Identify individual transactions whose amount significantly exceeds user history."""
        if len(amounts) < 5:
            return []

        arr = np.array(amounts)
        mean = float(np.mean(arr))
        std = float(np.std(arr))

        if std == 0:
            return []

        anomalies = []
        for idx, (amt, desc) in enumerate(zip(amounts, descriptions)):
            z_score = (amt - mean) / std
            if z_score >= self.z_score_threshold:
                anomalies.append({
                    "index": idx,
                    "amount": amt,
                    "description": desc,
                    "detector": "ZSCORE",
                    "score": round(float(z_score), 2),
                    "reason": f"Amount ₹{amt:,.2f} is {z_score:.1f} standard deviations above the average spending of ₹{mean:,.2f}.",
                })
        return anomalies

    def detect_amount_outliers_mad(
        self, amounts: List[float], descriptions: List[str]
    ) -> List[Dict[str, Any]]:
        """Robust outlier detection using Median Absolute Deviation (MAD)."""
        if len(amounts) < 5:
            return []

        arr = np.array(amounts)
        median = float(np.median(arr))
        diff = np.abs(arr - median)
        mad = float(np.median(diff))

        if mad == 0:
            return []

        anomalies = []
        for idx, (amt, desc) in enumerate(zip(amounts, descriptions)):
            modified_z_score = 0.6745 * (amt - median) / mad
            if modified_z_score >= 3.0:
                anomalies.append({
                    "index": idx,
                    "amount": amt,
                    "description": desc,
                    "detector": "MAD",
                    "score": round(float(modified_z_score), 2),
                    "reason": f"Amount ₹{amt:,.2f} is significantly unusual relative to median spending of ₹{median:,.2f}.",
                })
        return anomalies

    def detect_multivariate_isolation_forest(
        self,
        features: List[List[float]],
        descriptions: List[str]
    ) -> List[Dict[str, Any]]:
        """Detect multi-feature anomalies (amount, day-of-week, frequency) using Isolation Forest."""
        if len(features) < 15:
            # Need minimum historical samples
            return []

        x = np.array(features)
        model = IsolationForest(contamination=self.contamination, random_state=42)
        preds = model.fit_predict(x)
        scores = -model.decision_function(x)

        anomalies = []
        for idx, (pred, score, desc) in enumerate(zip(preds, scores, descriptions)):
            if pred == -1:  # Outlier
                anomalies.append({
                    "index": idx,
                    "amount": features[idx][0],
                    "description": desc,
                    "detector": "ISOLATION_FOREST",
                    "score": round(float(score), 3),
                    "reason": f"Multi-attribute spending anomaly detected for '{desc}' (anomaly score: {score:.2f}).",
                })
        return anomalies
