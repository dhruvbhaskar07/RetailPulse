# Feature Store

This directory stores feature-engineered datasets generated during the ETL pipeline and notebook execution. Each file contains derived features ready for model training, prediction, or dashboard consumption.

## Contents

| File | Description | Source |
|------|-------------|--------|
| `rfm_segments.csv` | Customer RFM scores (Recency, Frequency, Monetary) + segment labels | `02_segmentation.ipynb` / `src/features/rfm.py` |
| `customer_features.parquet` | Feature vectors for churn prediction, including rolling averages and lag features | `src/data/etl.py` |
| `daily_sales_ts.parquet` | Daily time-series aggregates per store-product (total qty, revenue, transaction count) | `src/data/etl.py` |
| `product_demand.csv` | Product-level demand signals and rolling means | `03_forecasting.ipynb` |
