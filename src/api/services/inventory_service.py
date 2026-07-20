"""Inventory optimisation service — returns reorder recommendations and stockout risk summaries."""

import pandas as pd
from typing import Optional

class InventoryService:
    def __init__(self):
        self._inventory: Optional[pd.DataFrame] = None

    def load_data(self, inventory: pd.DataFrame):
        self._inventory = inventory

    def get_recommendations(self, store_id: Optional[int] = None,
                            product_id: Optional[int] = None, top_n: int = 50) -> list:
        if self._inventory is None:
            raise ValueError("Inventory data not loaded")

        df = self._inventory.copy()
        if store_id is not None:
            df = df[df["store_id"] == store_id]
        if product_id is not None:
            df = df[df["product_id"] == product_id]

        df = df.nlargest(top_n, "urgency_score")

        items = []
        for _, row in df.iterrows():
            items.append({
                "store_id": int(row["store_id"]),
                "product_id": int(row["product_id"]),
                "stock_level": int(row["stock_level"]),
                "avg_daily_demand": float(row["avg_daily_demand"]),
                "safety_stock": float(row.get("safety_stock", 0)),
                "reorder_point": float(row.get("reorder_point_calculated", row.get("reorder_point", 0))),
                "recommended_order_qty": int(row["recommended_order_qty"]),
                "days_of_supply": float(row["days_of_supply"]),
                "urgency_score": float(row["urgency_score"]),
            })
        return items

    def get_summary(self) -> dict:
        if self._inventory is None:
            raise ValueError("Inventory data not loaded")
        inv = self._inventory
        return {
            "total_skus": len(inv),
            "below_reorder": int(inv["is_below_reorder"].sum()),
            "stockout_risk": int(inv["is_stockout_risk"].sum()),
            "total_recommended_qty": int(inv["recommended_order_qty"].sum()),
            "avg_days_of_supply": float(inv["days_of_supply"].mean()),
        }
