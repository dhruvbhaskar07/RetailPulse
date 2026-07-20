"""Customer segmentation service — returns cluster assignments and segment summaries."""

import pandas as pd
from typing import Optional

class SegmentService:
    def __init__(self):
        self._segments: Optional[pd.DataFrame] = None

    def load_data(self, segments: pd.DataFrame):
        self._segments = segments

    def get_segment(self, customer_id: int) -> dict:
        if self._segments is None:
            raise ValueError("Segments not loaded")

        row = self._segments[self._segments["customer_id"] == customer_id]
        if len(row) == 0:
            raise ValueError("Customer not found")

        return {
            "customer_id": customer_id,
            "cluster": int(row["cluster"].values[0]),
            "segment_label": row["segment_label"].values[0],
            "rfm_score": int(row["RFM_score"].values[0]) if "RFM_score" in row.columns else None,
        }

    def get_summary(self) -> list:
        if self._segments is None:
            raise ValueError("Segments not loaded")
        summary = self._segments["segment_label"].value_counts().reset_index()
        summary.columns = ["segment", "count"]
        summary["percentage"] = (summary["count"] / summary["count"].sum() * 100).round(1)
        return summary.to_dict(orient="records")
