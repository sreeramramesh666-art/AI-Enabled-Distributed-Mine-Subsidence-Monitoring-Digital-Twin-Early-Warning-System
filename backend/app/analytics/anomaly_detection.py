import logging
from typing import Optional, Dict, Any, List, Tuple
import numpy as np
from sklearn.ensemble import IsolationForest
from backend.app.core.config import settings

logger = logging.getLogger("mineguard.ml")


class MultivariateAnomalyDetector:
    def __init__(self):
        self.model: Optional[IsolationForest] = None
        self.is_trained: bool = False
        self.feature_names = [
            "displacement_mm",
            "tilt_x_deg",
            "tilt_y_deg",
            "velocity_mm_hr",
            "vibration_rms_ms2",
            "temperature_c"
        ]
        self.medians: Dict[str, float] = {f: 0.0 for f in self.feature_names}
        self.sample_count: int = 0
        self.last_trained_at: Optional[str] = None

    def fit_baseline(self, records: List[Dict[str, Any]]) -> bool:
        """
        Train Isolation Forest on clean baseline telemetry records.
        Imputes missing values with medians and checks sample sufficiency.
        """
        if not settings.ML_ANOMALY_ENABLED:
            logger.info("ML Anomaly detection is disabled in settings.")
            return False

        if len(records) < settings.ML_MIN_SAMPLES_TRAIN:
            logger.info(f"Insufficient baseline samples ({len(records)}/{settings.ML_MIN_SAMPLES_TRAIN}) for ML model training.")
            return False

        # Extract feature matrix
        matrix = []
        for r in records:
            row = []
            for feat in self.feature_names:
                val = r.get(feat)
                row.append(val if val is not None else np.nan)
            matrix.append(row)

        X = np.array(matrix, dtype=float)

        # Compute medians for imputation
        for idx, feat in enumerate(self.feature_names):
            col = X[:, idx]
            valid = col[~np.isnan(col)]
            self.medians[feat] = float(np.median(valid)) if len(valid) > 0 else 0.0
            # Impute
            X[np.isnan(X[:, idx]), idx] = self.medians[feat]

        try:
            self.model = IsolationForest(
                n_estimators=100,
                contamination=settings.ML_CONTAMINATION,
                random_state=settings.SIMULATOR_RANDOM_SEED,
                n_jobs=1
            )
            self.model.fit(X)
            self.is_trained = True
            self.sample_count = len(records)
            from datetime import datetime, timezone
            self.last_trained_at = datetime.now(timezone.utc).isoformat()
            logger.info(f"Multivariate Isolation Forest trained on {self.sample_count} samples.")
            return True
        except Exception as e:
            logger.error(f"Failed to train Isolation Forest: {e}")
            self.is_trained = False
            return False

    def predict(self, observation: Dict[str, Any]) -> Tuple[bool, float, Optional[str]]:
        """
        Evaluate an observation.
        Returns:
            is_anomaly: bool
            anomaly_score: float (-1.0 to 1.0; lower is more anomalous)
            primary_factor: name of top contributing feature or None
        """
        if not self.is_trained or self.model is None:
            return False, 0.0, None

        # Prepare vector
        row = []
        for feat in self.feature_names:
            val = observation.get(feat)
            if val is None or np.isnan(val):
                val = self.medians.get(feat, 0.0)
            row.append(float(val))

        X_input = np.array([row], dtype=float)

        try:
            pred = self.model.predict(X_input)[0]  # -1 for anomaly, 1 for normal
            score = float(self.model.decision_function(X_input)[0])

            is_anomaly = bool(pred == -1 or score < 0.0)
            primary_factor = None
            if is_anomaly:
                # Find feature with greatest deviation from baseline median
                deviations = {
                    feat: abs(row[i] - self.medians[feat])
                    for i, feat in enumerate(self.feature_names)
                }
                primary_factor = max(deviations, key=deviations.get)

            return is_anomaly, round(score, 4), primary_factor
        except Exception as e:
            logger.warning(f"ML prediction error: {e}")
            return False, 0.0, None

    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": settings.ML_ANOMALY_ENABLED,
            "trained": self.is_trained,
            "sample_count": self.sample_count,
            "features": self.feature_names,
            "last_trained_at": self.last_trained_at,
            "note": "Isolation Forest anomaly scores identify multivariate outliers; they are NOT collapse probabilities."
        }


ml_detector = MultivariateAnomalyDetector()
