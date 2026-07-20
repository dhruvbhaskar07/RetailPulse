"""Churn prediction service — returns risk scores, levels, and SHAP explanations."""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any

class ChurnService:
    def __init__(self):
        self._churn_scores: Optional[pd.DataFrame] = None
        self._customer_features: Optional[pd.DataFrame] = None
        self._model = None
        self._feature_cols: List[str] = []

    def load_data(self, churn_scores: pd.DataFrame, customer_features: Optional[pd.DataFrame] = None,
                  model_artifact: Optional[dict] = None):
        self._churn_scores = churn_scores
        self._customer_features = customer_features
        if model_artifact:
            self._model = model_artifact.get("model")
            self._feature_cols = model_artifact.get("feature_cols", [])

    def get_churn_risk(self, customer_id: int) -> dict:
        if self._churn_scores is None:
            raise ValueError("Churn scores not loaded")

        row = self._churn_scores[self._churn_scores["customer_id"] == customer_id]
        if len(row) == 0:
            raise ValueError("Customer not found")

        prob = float(row["churn_risk_score"].values[0])
        level = row["churn_risk_level"].values[0]

        top_factors = None
        if self._model is not None and self._customer_features is not None and self._feature_cols:
            try:
                import shap
                cust_row = self._customer_features[self._customer_features["customer_id"] == customer_id]
                if len(cust_row) > 0:
                    X = cust_row[self._feature_cols].fillna(0)
                    explainer = shap.TreeExplainer(self._model)
                    shap_values = explainer.shap_values(X)
                    mean_shap = np.abs(shap_values).mean(axis=0) if shap_values.ndim > 1 else np.abs(shap_values)
                    top_indices = np.argsort(mean_shap)[-5:][::-1]
                    top_factors = [
                        {"feature": self._feature_cols[i], "impact": float(shap_values[0][i] if shap_values.ndim > 1 else shap_values[i])}
                        for i in top_indices
                    ]
            except Exception:
                pass

        return {
            "customer_id": customer_id,
            "churn_probability": prob,
            "risk_level": level,
            "top_factors": top_factors,
        }

    def get_summary(self) -> dict:
        if self._churn_scores is None:
            raise ValueError("Churn scores not loaded")
        summary = self._churn_scores["churn_risk_level"].value_counts()
        return {
            "risk_levels": summary.to_dict(),
            "total": len(self._churn_scores),
            "avg_risk": float(self._churn_scores["churn_risk_score"].mean()),
            "high_risk_count": int((self._churn_scores["churn_risk_score"] > 0.5).sum()),
        }
