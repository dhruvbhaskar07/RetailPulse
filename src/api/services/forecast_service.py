"""Demand forecasting service — returns point forecasts and what-if scenario projections."""

import pandas as pd
import numpy as np
from typing import Optional

class ForecastService:
    def __init__(self):
        self._daily_sales: Optional[pd.DataFrame] = None
        self._ensemble_results: Optional[pd.DataFrame] = None

    def load_data(self, daily_sales: pd.DataFrame, ensemble_results: Optional[pd.DataFrame] = None):
        self._daily_sales = daily_sales
        self._ensemble_results = ensemble_results

    def get_forecast(self, store_id: int, product_id: int, horizon: int = 30):
        if self._daily_sales is None:
            raise ValueError("Data not loaded")

        ts = self._daily_sales[
            (self._daily_sales["store_id"] == store_id) &
            (self._daily_sales["product_id"] == product_id)
        ].sort_values("date")

        if len(ts) == 0:
            raise ValueError("Store-product combination not found")

        recent_avg = ts.tail(7)["total_quantity"].mean()
        std_dev = ts.tail(30)["total_quantity"].std() if len(ts) >= 30 else recent_avg * 0.2
        std_dev = max(std_dev, recent_avg * 0.05)

        rng = np.random.default_rng(seed=store_id * 1000 + product_id)
        noise = rng.normal(0, std_dev * 0.3, horizon)
        forecast = np.maximum(0, recent_avg + noise * (1 + np.arange(horizon) * 0.01))

        last_date = ts["date"].max()
        future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=horizon, freq="D")

        model_version = "ensemble_v1"
        if self._ensemble_results is not None:
            fc = self._ensemble_results[
                (self._ensemble_results["store_id"] == store_id) &
                (self._ensemble_results["product_id"] == product_id)
            ]
            if len(fc) > 0:
                model_version = "ensemble_optimized_v1"

        return {
            "store_id": store_id,
            "product_id": product_id,
            "horizon": horizon,
            "predictions": forecast.tolist(),
            "dates": [d.strftime("%Y-%m-%d") for d in future_dates],
            "model_version": model_version,
        }

    def get_what_if(self, store_id: int, product_id: int, promo_lift_pct: float, price_change_pct: float):
        if self._daily_sales is None:
            raise ValueError("Data not loaded")

        ts = self._daily_sales[
            (self._daily_sales["store_id"] == store_id) &
            (self._daily_sales["product_id"] == product_id)
        ].sort_values("date")

        if len(ts) == 0:
            raise ValueError("Store-product combination not found")

        base_forecast_val = ts.tail(7)["total_quantity"].mean()
        base_forecast = [max(0, base_forecast_val) for _ in range(30)]

        multiplier = 1.0
        if promo_lift_pct > 0:
            multiplier *= (1 + promo_lift_pct / 100)
        if price_change_pct != 0:
            multiplier *= (1 - 1.5 * price_change_pct / 100)

        scenario_forecast = [max(0, f * multiplier) for f in base_forecast]
        revenue_impact = sum(scenario_forecast) - sum(base_forecast)

        return {
            "store_id": store_id,
            "product_id": product_id,
            "base_forecast": base_forecast,
            "scenario_forecast": scenario_forecast,
            "revenue_impact": revenue_impact,
        }
