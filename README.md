# RetailPulse — AI-Powered Customer Analytics & Demand Forecasting Platform

[![CI/CD](https://github.com/dhruvbhaskar07/RetailPulse/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/dhruvbhaskar07/RetailPulse/actions/workflows/ci-cd.yml)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-red.svg)](https://streamlit.io)
[![Docker](https://img.shields.io/badge/Docker-ready-blue.svg)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An end-to-end data science platform for retail businesses — predict demand, segment customers, detect churn, and optimise inventory using the **Online Retail II** dataset (UCI, 1M+ transactions across 41 countries).

---

## Features

| Feature | Technology | Target |
|---------|-----------|--------|
| **Demand Forecasting** | Prophet + LSTM ensemble | MAPE ≤ 12% (30-day ahead) |
| **Customer Segmentation** | RFM + K-Means / DBSCAN | Silhouette ≥ 0.4 |
| **Churn Prediction** | XGBoost + SHAP explainability | AUC-ROC ≥ 0.88 |
| **Inventory Optimisation** | Safety stock, reorder points, Monte Carlo | Stockout risk reduced 30–50% |
| **Interactive Dashboard** | 9-page Streamlit app with global filters | — |
| **REST API** | FastAPI with JWT auth, rate limiting, audit logging | — |
| **MLOps** | MLflow tracking, Evidently AI drift, Prefect orchestration | — |
| **Production** | Docker, Kubernetes, Prometheus/Grafana, CI/CD | — |

---

## Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Online      │───▶│  ETL +       │───▶│  Feature     │
│  Retail II   │    │  Validation  │    │  Store       │
└──────────────┘    └──────────────┘    └──────┬───────┘
                                                │
                    ┌──────────────┐    ┌───────▼───────┐
                    │   Models     │◀───│  MLflow       │
                    │              │    │  Tracking     │
                    │ • Prophet    │    └───────────────┘
                    │ • LSTM       │          │
                    │ • XGBoost    │          ▼
                    │ • K-Means    │    ┌──────────────┐
                    └──────┬───────┘    │  FastAPI     │
                           │            └──────┬───────┘
                           ▼                   │
                    ┌──────────────┐    ┌───────▼───────┐
                    │  Dashboard   │◀───│  Services     │
                    │  (Streamlit) │    └───────────────┘
                    └──────────────┘
```

---

## Quick Start

### Prerequisites
- Python 3.11+

### Local Development

```powershell
# Step 1 — One-time setup (venv, deps, data):
python setup.py

# Step 2 — Launch everything (trains models if needed, starts API + Dashboard):
python launcher.py
```

Then open:

| Service | URL | Credentials |
|---------|-----|-------------|
| **Dashboard** | http://localhost:8501 | admin / admin123 |
| **API Docs** | http://localhost:8000/docs | (use token from login) |
| **Health** | http://localhost:8000/health | — |

### Docker Compose (Full Stack)

```bash
docker-compose up -d

# Services: API :8000, Dashboard :8501, MLflow :5000,
#           Prometheus :9090, Grafana :3000 (admin/admin)
```

### Retrain Models on New Data

1. Login as **admin / admin123**
2. Go to **Models** page
3. Click **"Retrain All Models on New Data"** button
4. Pipeline runs in background — status updates live

---

## Project Structure

```
retailpulse/
├── src/
│   ├── config.py                     # Central configuration
│   ├── data/
│   │   ├── etl.py                    # ETL pipeline
│   │   ├── generate.py               # Synthetic data generator
│   │   ├── validation.py             # Quality checks
│   │   ├── sequences.py              # Time-series stationarity utilities
│   │   └── adapters/
│   │       └── online_retail_ii.py   # UCI dataset transformer
│   ├── features/
│   │   └── rfm.py                    # RFM scoring
│   ├── models/
│   │   ├── segmentation.py           # K-Means / DBSCAN + Optuna tuning
│   │   ├── forecasting.py            # Prophet + ensemble
│   │   ├── churn.py                  # XGBoost + SHAP + Optuna
│   │   ├── inventory.py              # Safety stock, Monte Carlo
│   │   └── lstm_forecasting.py       # PyTorch LSTM with attention
│   ├── api/
│   │   ├── main.py                   # FastAPI entry point
│   │   ├── config.py                 # JWT, CORS, DB URIs
│   │   ├── middleware.py             # Metrics + audit middleware
│   │   ├── auth/                     # JWT auth + role enforcement
│   │   ├── routers/                  # forecast, churn, segments, inventory, simulator, admin
│   │   ├── schemas/                  # Pydantic request/response models
│   │   └── services/                 # Business logic layer
│   ├── dashboard/
│   │   ├── app.py                    # Streamlit main app
│   │   ├── config.py                 # Dashboard config & constants
│   │   ├── utils.py                  # Auth, caching, filtering
│   │   ├── assets/styles.css         # Premium UI styles (43 KB)
│   │   ├── components/ui.py          # Cards, headers, tables, skeletons
│   │   └── pages/                    # 9 dashboard page modules
│   └── utils/
│       ├── data_loader.py            # Thread-safe cached data loader
│       ├── drift.py                  # Evidently AI drift detection
│       ├── mlflow_utils.py           # MLflow experiment helpers
│       └── validate.py               # Sklearn validation utilities
├── data/
│   ├── raw/                          # Raw input CSVs + Online Retail II.xlsx
│   ├── processed/                    # Cleaned parquet + model artifacts
│   └── features/                     # Feature-engineered outputs
├── notebooks/
│   ├── 01_EDA.ipynb                 # Exploratory data analysis
│   ├── 02_segmentation.ipynb        # Customer segmentation
│   ├── 03_forecasting.ipynb         # Demand forecasting
│   ├── 04_churn.ipynb               # Churn prediction
│   ├── 05_inventory.ipynb           # Inventory optimisation
│   └── generate_notebooks.py        # Notebook generator from spec
├── reports/                          # 13 PNG visualisations from notebooks
├── docs/
│   └── powerbi_dashboards.md         # Power BI setup guide
├── dags/
│   └── retrain_flows.py              # Prefect retraining DAG
├── monitoring/
│   ├── prometheus/                   # Prometheus config + alert rules
│   └── grafana/                      # Grafana dashboard JSON
├── k8s/                              # Kubernetes manifests
├── tests/
│   ├── load_test.py                  # Locust-style load test
│   └── test_performance.py           # Prediction speed test
├── .github/workflows/ci-cd.yml       # GitHub Actions CI/CD
├── mlruns/                           # MLflow experiment DB
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── setup.py
├── launcher.py
└── README.md
```

---

## API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/auth/login` | POST | — | JWT login |
| `/auth/logout` | POST | Bearer | Revoke token |
| `/auth/refresh` | POST | Bearer | Refresh token |
| `/forecast` | POST | Bearer | Demand forecast (store × product) |
| `/churn-risk` | POST | Bearer | Customer churn probability |
| `/segments/summary` | GET | Bearer | Segment distribution |
| `/segment` | POST | Bearer | Single customer segment |
| `/inventory` | POST | Bearer | Reorder recommendations |
| `/what-if` | POST | Bearer | Promo/price scenario |
| `/admin/retrain` | POST | Admin | Retrain all models |
| `/admin/models` | GET | Admin | Model version status |
| `/admin/audit/logs` | GET | Admin | Audit log query |
| `/health` | GET | — | Health check |
| `/metrics` | GET | — | Prometheus metrics |

---

## Dashboard Pages

| # | Page | Description |
|---|------|-------------|
| 1 | **Overview** | KPIs, revenue trend, country map, top products |
| 2 | **Forecast** | Prophet + LSTM ensemble, MAPE tracking, store/product selector |
| 3 | **Segments** | RFM distribution, 3D cluster visualisation, segment profiles |
| 4 | **Churn** | Risk distribution, top at-risk customers, SHAP explanations |
| 5 | **Inventory** | Stockout risk, days of supply, reorder recommendations |
| 6 | **Simulator** | What-if promo/price scenario modelling |
| 7 | **Drift** | Evidently AI data drift reports with alerts |
| 8 | **Models** | Performance targets, feature importance, retrain controls |
| 9 | **Import** | Custom CSV/Excel/JSON/Parquet dataset import |

---

## Jupyter Notebooks

All notebooks are generated from the project spec and executed against the real Online Retail II dataset:

| Notebook | Outputs |
|----------|---------|
| `01_EDA.ipynb` | Missing values, distributions, correlation, top products, country revenue |
| `02_segmentation.ipynb` | RFM segments, elbow/silhouette, 3D clusters |
| `03_forecasting.ipynb` | Prophet forecast, seasonal decomposition, components |
| `04_churn.ipynb` | SHAP summary + waterfall, feature importance |
| `05_inventory.ipynb` | Inventory status, stockout analysis |

Report images are saved to `reports/`.

---

## Model Performance Targets

| Model | Metric | Target | Status |
|-------|--------|--------|--------|
| Demand Forecast | MAPE | ≤ 12% | Tracked in dashboard |
| Churn Prediction | AUC-ROC | ≥ 0.88 | Tracked in dashboard |
| Customer Segmentation | Silhouette Score | ≥ 0.4 | Tracked in dashboard |
| Inventory Optimisation | Stockout Reduction | 30–50% | Tracked in dashboard |
| Churn (Feature Importance) | SHAP Analysis | Top 5 drivers | Generated in `04_churn.ipynb` |

---

## MLOps

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Experiment Tracking | MLflow (SQLite) | Log params, metrics, model artifacts |
| Drift Detection | Evidently AI | Data + target drift monitoring |
| Orchestration | Prefect | Daily retraining flows |
| Monitoring | Prometheus + Grafana | API metrics, dashboards |
| CI/CD | GitHub Actions | Lint, test, Docker build & push |
| Containerisation | Docker + docker-compose | Full stack orchestration |
| Orchestration | Kubernetes | Deployment, HPA, ingress |

---

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feat/amazing-feature`)
3. Commit changes (`git commit -m 'feat: add amazing feature'`)
4. Push to branch (`git push origin feat/amazing-feature`)
5. Open Pull Request

## License

MIT License — see [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Online Retail II** dataset — UCI Machine Learning Repository
- **Prophet** by Facebook/Meta
- **XGBoost**, **SHAP**, **Evidently AI**, **Streamlit** communities
- Zidio Development Data Science & Analytics Domain
