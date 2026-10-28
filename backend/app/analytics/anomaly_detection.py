import logging
from typing import Optional, Dict, Any, List, Tuple
import numpy as np
from sklearn.ensemble import IsolationForest
from backend.app.core.config import settings

logger = logging.getLogger("mineguard.ml")


class MultivariateAnomalyDetector:
    """
    Separate, explicitly labelled unsupervised Multivariate Anomaly Detection model using Isolation Forest.
    Strictly outputs decision outlier distances (-1.0 to 1.0).
    NEVER presents model scores as probabilities of slope or mine collapse.
    Requires sufficient baseline training samples (>= settings.ML_MIN_SAMPLES_TRAIN).
    """

    def __init__(self):
        self.model: Optional[IsolationForest] = None
        self.is_trained: bool = False
        self.model_label: str = "ML_ISOLATION_FOREST_OUTLIER"
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
        Requires >= settings.ML_MIN_SAMPLES_TRAIN (default 30) valid observation frames.
        Imputes missing values with medians and checks sample sufficiency.
        """
        if not settings.ML_ANOMALY_ENABLED:
            logger.info("ML Anomaly detection is disabled in settings.")
            return False

        if len(records) < settings.ML_MIN_SAMPLES_TRAIN:
            logger.info(
                f"Insufficient baseline samples ({len(records)}/{settings.ML_MIN_SAMPLES_TRAIN}) "
                "for ML Isolation Forest training. Model remains untrained."
            )
            self.is_trained = False
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
            logger.info(f"Multivariate Isolation Forest trained successfully on {self.sample_count} samples.")
            return True
        except Exception as e:
            logger.error(f"Failed to train Isolation Forest: {e}")
            self.is_trained = False
            return False

    def predict(
        self,
        observation: Dict[str, Any],
        include_metadata: bool = False
    ) -> Any:
        """
        Evaluate an observation against baseline manifold.
        Returns:
            is_anomaly: bool
            anomaly_score: float (-1.0 to 1.0; lower is more anomalous)
            primary_factor: name of top contributing feature or None
            (optional metadata dict if include_metadata=True)
        """
        base_meta = {
            "model_name": self.model_label,
            "model_version": "1.0.0",
            "is_trained": self.is_trained,
            "sample_count": self.sample_count,
            "features_analyzed": self.feature_names,
            "contamination_parameter": settings.ML_CONTAMINATION,
            "is_probability_of_collapse": False,
            "disclaimer": (
                "Isolation Forest anomaly score represents an unsupervised multivariate outlier decision distance "
                "(-1.0 to 1.0) relative to training baseline. This score is NOT an empirical probability of slope failure or collapse."
            )
        }

        if not self.is_trained or self.model is None:
            if include_metadata:
                base_meta["status"] = "UNTRAINED_INSUFFICIENT_DATA"
                return False, 0.0, None, base_meta
            return False, 0.0, None

        # Prepare feature vector
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
                # Find feature with greatest normalized deviation from baseline median
                deviations = {}
                for i, feat in enumerate(self.feature_names):
                    diff = abs(row[i] - self.medians[feat])
                    deviations[feat] = diff
                primary_factor = max(deviations, key=deviations.get)

            if include_metadata:
                base_meta["anomaly_score"] = round(score, 4)
                base_meta["primary_factor"] = primary_factor
                return is_anomaly, round(score, 4), primary_factor, base_meta

            return is_anomaly, round(score, 4), primary_factor
        except Exception as e:
            logger.warning(f"ML prediction error: {e}")
            if include_metadata:
                base_meta["error"] = str(e)
                return False, 0.0, None, base_meta
            return False, 0.0, None

    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": settings.ML_ANOMALY_ENABLED,
            "trained": self.is_trained,
            "model_name": self.model_label,
            "sample_count": self.sample_count,
            "features": self.feature_names,
            "last_trained_at": self.last_trained_at,
            "is_probability_of_collapse": False,
            "disclaimer": (
                "Isolation Forest anomaly score represents an unsupervised multivariate outlier decision distance "
                "(-1.0 to 1.0). This metric is NOT an empirical probability of ground collapse or slope failure."
            ),
            "note": "Isolation Forest identifies multi-sensor statistical anomalies. It does NOT produce an empirical collapse probability."
        }


ml_detector = MultivariateAnomalyDetector()
