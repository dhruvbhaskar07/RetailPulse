"""Generate all 5 Jupyter notebooks from the RetailPulse guide."""
import json
import nbformat as nbf
from pathlib import Path

NB_DIR = Path(__file__).parent

def save_notebook(cells, filename):
    nb = nbf.v4.new_notebook()
    nb.metadata = {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python",
            "version": "3.11.0"
        }
    }
    nb.cells = [nbf.v4.new_code_cell(src) for src in cells]
    path = NB_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        nbf.write(nb, f)
    print(f"  Created: {filename}")

def notebook_01_eda():
    cells = [
        '''# %% [markdown]
# # 01 — Exploratory Data Analysis (EDA)
# ## Online Retail II Dataset
# **RetailPulse — Zidio Development | March 2026**
''',
        '''# %% [markdown]
# ## Imports & Setup''',
        '''import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import missingno as msno
import warnings
warnings.filterwarnings('ignore')
plt.rcParams['figure.dpi'] = 120
plt.rcParams['savefig.dpi'] = 150
plt.rcParams['figure.figsize'] = (12, 5)''',
        '''# %% [markdown]
# ## Load Dataset''',
        '''df = pd.read_excel('../data/raw/online_retail_ii/online_retail_II.xlsx')
print(f"Shape: {df.shape}")
print(f"Columns: {list(df.columns)}")
print(df.info(null_counts=True))''',
        '''# %% [markdown]
# ## Data Cleaning''',
        '''print(f"Before cleaning: {df.shape}")

# Remove cancelled
df = df[~df['Invoice'].astype(str).str.startswith('C')]
df = df[df['Quantity'] > 0]
df = df[df['Price'] > 0]
df = df.dropna(subset=['Customer ID'])
df['Customer ID'] = df['Customer ID'].astype(int)
df['TotalAmount'] = df['Quantity'] * df['Price']
df = df.drop_duplicates()

print(f"After cleaning: {df.shape}")
print(f"Date range: {df['InvoiceDate'].min()} to {df['InvoiceDate'].max()}")
print(f"Unique customers: {df['Customer ID'].nunique():,}")
print(f"Unique invoices: {df['Invoice'].nunique():,}")
print(f"Unique products: {df['StockCode'].nunique():,}")
print(f"Countries: {df['Country'].nunique()}")''',
        '''# %%[markdown]
# ## Missing Values Matrix''',
        '''msno.matrix(df)
plt.title("Missing Values Matrix — Online Retail II")
plt.tight_layout()
plt.savefig('../reports/missing_values.png', bbox_inches='tight')
plt.show()''',
        '''# %%[markdown]
# ## Distribution Analysis''',
        '''fig, axes = plt.subplots(1, 2, figsize=(14, 5))
df['Quantity'].hist(ax=axes[0], bins=50, color='steelblue', edgecolor='black')
axes[0].set_title('Quantity Distribution')
axes[0].set_xlabel('Quantity')
df['Price'].hist(ax=axes[1], bins=50, color='coral', edgecolor='black')
axes[1].set_title('Price Distribution')
axes[1].set_xlabel('Price (£)')
plt.tight_layout()
plt.savefig('../reports/distributions.png', bbox_inches='tight')
plt.show()''',
        '''# %%[markdown]
# ## Correlation Heatmap''',
        '''df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
df['Year'] = df['InvoiceDate'].dt.year
df['Month'] = df['InvoiceDate'].dt.month
df['DayOfWeek'] = df['InvoiceDate'].dt.dayofweek
df['Hour'] = df['InvoiceDate'].dt.hour

numeric_df = df[['Quantity', 'Price', 'TotalAmount', 'Month', 'DayOfWeek']].dropna()
plt.figure(figsize=(8, 6))
sns.heatmap(numeric_df.corr(), annot=True, cmap='coolwarm', center=0, fmt='.2f')
plt.title('Correlation Heatmap')
plt.tight_layout()
plt.savefig('../reports/correlation_heatmap.png', bbox_inches='tight')
plt.show()

print(df[['Quantity', 'Price', 'TotalAmount', 'Month', 'DayOfWeek']].describe())''',
        '''# %%[markdown]
# ## Top Products by Revenue''',
        '''top_products = df.groupby('Description')['TotalAmount'].sum().sort_values(ascending=False).head(10)
plt.figure(figsize=(10, 6))
top_products.plot(kind='barh', color='teal', edgecolor='black')
plt.title('Top 10 Products by Revenue')
plt.xlabel('Total Revenue (£)')
plt.gca().invert_yaxis()
plt.tight_layout()
plt.savefig('../reports/top_products.png', bbox_inches='tight')
plt.show()''',
        '''# %%[markdown]
# ## Revenue by Country''',
        '''top_countries = df.groupby('Country')['TotalAmount'].sum().sort_values(ascending=False).head(10)
plt.figure(figsize=(10, 6))
top_countries.plot(kind='bar', color='orange', edgecolor='black')
plt.title('Revenue by Country (Top 10)')
plt.ylabel('Total Revenue (£)')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.savefig('../reports/revenue_by_country.png', bbox_inches='tight')
plt.show()

print(f"Total revenue: £{df['TotalAmount'].sum():,.2f}")
print(f"Avg order value: £{df['TotalAmount'].mean():.2f}")
print(f"Total transactions: {len(df):,}")''',
    ]
    save_notebook(cells, "01_EDA.ipynb")

def notebook_02_segmentation():
    cells = [
        '''# %% [markdown]
# # 02 — Customer Segmentation (RFM + K-Means + DBSCAN)
# ## RetailPulse — Zidio Development | March 2026
''',
        '''# %% [markdown]
# ## Imports & Setup''',
        '''import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics import silhouette_score
import warnings
warnings.filterwarnings('ignore')
plt.rcParams['figure.dpi'] = 120
plt.rcParams['savefig.dpi'] = 150''',
        '''# %%[markdown]
# ## Load Cleaned Data''',
        '''sales = pd.read_parquet('../data/processed/sales_clean.parquet')
print(f"Sales: {len(sales):,} rows")
print(f"Date range: {sales['date'].min()} to {sales['date'].max()}")''',
        '''# %%[markdown]
# ## Compute RFM Features''',
        '''snapshot_date = sales['date'].max() + pd.Timedelta(days=1)

rfm = sales.groupby('customer_id').agg(
    Recency=('date', lambda x: (snapshot_date - x.max()).days),
    Frequency=('transaction_id', 'nunique'),
    Monetary=('revenue', 'sum')
).reset_index()

print(f"RFM shape: {rfm.shape}")
print(rfm.describe())''',
        '''# %%[markdown]
# ## RFM Scoring (1-5 Quantiles)''',
        '''rfm['R_Score'] = pd.qcut(rfm['Recency'], 5, labels=[5,4,3,2,1]).astype(int)
rfm['F_Score'] = pd.qcut(rfm['Frequency'].rank(method='first'), 5, labels=[1,2,3,4,5]).astype(int)
rfm['M_Score'] = pd.qcut(rfm['Monetary'].rank(method='first'), 5, labels=[1,2,3,4,5]).astype(int)
rfm['RFM_Score'] = rfm['R_Score'] + rfm['F_Score'] + rfm['M_Score']
rfm['RFM_Segment'] = rfm['R_Score'].astype(str) + rfm['F_Score'].astype(str) + rfm['M_Score'].astype(str)
print(rfm.head())''',
        '''# %%[markdown]
# ## Optimal K — Elbow + Silhouette''',
        '''features = ['Recency', 'Frequency', 'Monetary']
X = rfm[features].copy()
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

inertias = []
silhouettes = []
K_range = range(2, 11)

for k in K_range:
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    km.fit(X_scaled)
    inertias.append(km.inertia_)
    silhouettes.append(silhouette_score(X_scaled, km.labels_))

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
ax1.plot(K_range, inertias, 'bo-')
ax1.set_title('Elbow Method')
ax1.set_xlabel('K'); ax1.set_ylabel('Inertia')
ax2.plot(K_range, silhouettes, 'rs-')
ax2.set_title('Silhouette Score')
ax2.set_xlabel('K'); ax2.set_ylabel('Score')
plt.tight_layout()
plt.savefig('../reports/elbow_silhouette.png', bbox_inches='tight')
plt.show()

best_k = K_range[np.argmax(silhouettes)]
print(f"Optimal K (silhouette): {best_k}")''',
        '''# %%[markdown]
# ## K-Means Clustering (k=6)''',
        '''kmeans = KMeans(n_clusters=6, random_state=42, n_init=10)
rfm['KMeans_Cluster'] = kmeans.fit_predict(X_scaled)

segment_names = {
    0: 'Champions', 1: 'Loyal Customers', 2: 'Potential Loyalists',
    3: 'At-Risk Customers', 4: 'Lost Customers', 5: 'New Customers'
}
rfm['Segment_Name'] = rfm['KMeans_Cluster'].map(segment_names)

cluster_summary = rfm.groupby('KMeans_Cluster')[features].mean().round(2)
print("Cluster Summary:")
print(cluster_summary)
print(f"\\nSegment distribution:")
print(rfm['Segment_Name'].value_counts())''',
        '''# %%[markdown]
# ## DBSCAN Clustering''',
        '''dbscan = DBSCAN(eps=0.5, min_samples=5)
rfm['DBSCAN_Cluster'] = dbscan.fit_predict(X_scaled)
n_noise = (rfm['DBSCAN_Cluster'] == -1).sum()
print(f"DBSCAN clusters: {rfm['DBSCAN_Cluster'].nunique() - 1} (+ noise)")
print(f"Noise points: {n_noise} ({n_noise/len(rfm)*100:.1f}%)")''',
        '''# %%[markdown]
# ## 3D RFM Visualization''',
        '''from mpl_toolkits.mplot3d import Axes3D

fig = plt.figure(figsize=(12, 8))
ax = fig.add_subplot(111, projection='3d')
scatter = ax.scatter(rfm['Recency'], rfm['Frequency'], rfm['Monetary'],
                     c=rfm['KMeans_Cluster'], cmap='tab10', alpha=0.6, s=20)
ax.set_xlabel('Recency (days)')
ax.set_ylabel('Frequency')
ax.set_zlabel('Monetary (£)')
plt.title('Customer Segments — 3D RFM Space')
plt.colorbar(scatter, label='Cluster')
plt.savefig('../reports/rfm_3d_clusters.png', bbox_inches='tight')
plt.show()''',
        '''# %%[markdown]
# ## Save Results''',
        '''rfm.to_csv('../data/processed/rfm_segments.csv', index=False)
print(f"Saved rfm_segments.csv with {len(rfm)} customers")

# Save segment profiles for dashboard
segment_profiles = rfm.groupby('Segment_Name').agg(
    count=('customer_id', 'count'),
    avg_recency=('Recency', 'mean'),
    avg_frequency=('Frequency', 'mean'),
    avg_monetary=('Monetary', 'mean'),
).round(2).reset_index()
segment_profiles.to_csv('../data/processed/segment_profiles.csv', index=False)
print("Saved segment_profiles.csv")''',
    ]
    save_notebook(cells, "02_segmentation.ipynb")

def notebook_03_forecasting():
    cells = [
        '''# %% [markdown]
# # 03 — Demand Forecasting (Prophet + LSTM Ensemble)
# ## RetailPulse — Zidio Development | March 2026
''',
        '''# %%[markdown]
# ## Imports & Setup''',
        '''import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.seasonal import seasonal_decompose
from prophet import Prophet
import warnings
warnings.filterwarnings('ignore')
plt.rcParams['figure.dpi'] = 120
plt.rcParams['savefig.dpi'] = 150''',
        '''# %%[markdown]
# ## Load Daily Sales Data''',
        '''daily_sales = pd.read_parquet('../data/processed/daily_sales_ts.parquet')
print(f"Rows: {len(daily_sales):,}")
# Aggregate to total daily revenue for time series
ts = daily_sales.groupby('date')['total_revenue'].sum().reset_index()
ts.columns = ['ds', 'y']
ts['ds'] = pd.to_datetime(ts['ds'])
ts = ts.sort_values('ds').reset_index(drop=True)

# Fill missing dates
date_range = pd.date_range(ts['ds'].min(), ts['ds'].max(), freq='D')
ts = ts.set_index('ds').reindex(date_range).fillna(0).reset_index()
ts.columns = ['ds', 'y']

print(f"Date range: {ts['ds'].min()} to {ts['ds'].max()}")
print(f"Total days: {len(ts)}")
print(f"Total revenue: £{ts['y'].sum():,.0f}")''',
        '''# %%[markdown]
# ## Stationarity Test (ADF)''',
        '''adf_result = adfuller(ts['y'].dropna())
print(f"ADF Statistic: {adf_result[0]:.4f}")
print(f"p-value: {adf_result[1]:.4f}")
print(f"Stationary: {adf_result[1] < 0.05}")
print(f"Critical values: {adf_result[4]}")''',
        '''# %%[markdown]
# ## Seasonal Decomposition''',
        '''decomp = seasonal_decompose(ts.set_index('ds')['y'], model='additive', period=7)
fig = decomp.plot()
fig.set_size_inches(12, 10)
plt.suptitle('Seasonal Decomposition (7-day period)', fontsize=14)
plt.tight_layout()
plt.savefig('../reports/seasonal_decomposition.png', bbox_inches='tight')
plt.show()''',
        '''# %%[markdown]
# ## Prophet Model — Baseline''',
        '''train = ts[ts['ds'] < '2010-10-01']
test = ts[ts['ds'] >= '2010-10-01']
print(f"Train: {len(train)} days, Test: {len(test)} days")

model = Prophet(
    yearly_seasonality=True,
    weekly_seasonality=True,
    daily_seasonality=False,
    changepoint_prior_scale=0.05,
    seasonality_mode='multiplicative'
)
model.add_country_holidays(country_name='GB')
model.fit(train)

future = model.make_future_dataframe(periods=30)
forecast = model.predict(future)''',
        '''# %%[markdown]
# ## Evaluate''',
        '''merged = test.merge(forecast[['ds', 'yhat']], on='ds', how='inner')
mape = (abs(merged['y'] - merged['yhat']) / (merged['y'] + 1e-6)).mean() * 100
print(f"Prophet MAPE: {mape:.2f}%")
print(f"Within target (≤12%): {mape <= 12}")

fig1 = model.plot(forecast)
plt.title(f'Prophet Forecast (MAPE: {mape:.2f}%)')
plt.savefig('../reports/prophet_forecast.png', bbox_inches='tight')
plt.show()

fig2 = model.plot_components(forecast)
plt.savefig('../reports/prophet_components.png', bbox_inches='tight')
plt.show()''',
        '''# %%[markdown]
# ## Save Forecast Results''',
        '''forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].to_csv(
    '../data/processed/forecast_results.csv', index=False)
print(f"Saved forecast_results.csv with {len(forecast)} rows")

# Save for ensemble
ensemble = forecast[['ds', 'yhat']].copy()
ensemble['model'] = 'prophet'
ensemble['mape'] = mape
ensemble.to_csv('../data/processed/ensemble_forecast_results.csv', index=False)
print("Saved ensemble_forecast_results.csv")''',
    ]
    save_notebook(cells, "03_forecasting.ipynb")

def notebook_04_churn():
    cells = [
        '''# %% [markdown]
# # 04 — Churn Prediction (XGBoost + SHAP)
# ## RetailPulse — Zidio Development | March 2026
''',
        '''# %%[markdown]
# ## Imports & Setup''',
        '''import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import xgboost as xgb
import shap
import optuna
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix
import warnings
warnings.filterwarnings('ignore')
plt.rcParams['figure.dpi'] = 120
plt.rcParams['savefig.dpi'] = 150''',
        '''# %%[markdown]
# ## Load Data & Build Churn Features''',
        '''sales = pd.read_parquet('../data/processed/sales_clean.parquet')
rfm = pd.read_csv('../data/processed/rfm_segments.csv')

print(f"Sales: {len(sales):,} rows")
print(f"RFM: {len(rfm):,} customers")''',
        '''# %%[markdown]
# ## Define Churn (90-day threshold)''',
        '''snapshot_date = sales['date'].max()
churn_threshold = 90
rfm['Churned'] = (rfm['Recency'] > churn_threshold).astype(int)
print(f"Churn rate: {rfm['Churned'].mean()*100:.1f}%")
print(f"Churned: {rfm['Churned'].sum():,} / {len(rfm):,}")''',
        '''# %%[markdown]
# ## Additional Behavioral Features''',
        '''customer_features = sales.groupby('customer_id').agg(
    avg_basket_size=('revenue', 'mean'),
    std_basket_size=('revenue', 'std'),
    total_items=('quantity', 'sum'),
    unique_products=('product_id', 'nunique'),
    total_transactions=('transaction_id', 'nunique'),
    days_active=('date', lambda x: (x.max() - x.min()).days)
).reset_index()

churn_df = rfm.merge(customer_features, on='customer_id', how='left').fillna(0)

feature_cols = ['Recency', 'Frequency', 'Monetary', 'RFM_Score',
                'avg_basket_size', 'std_basket_size', 'total_items',
                'unique_products', 'total_transactions', 'days_active']

X = churn_df[feature_cols]
y = churn_df['Churned']

print(f"Feature matrix: {X.shape}")
print(f"Features: {feature_cols}")''',
        '''# %%[markdown]
# ## Train/Test Split''',
        '''X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"Train: {len(X_train)}, Test: {len(X_test)}")
print(f"Train churn rate: {y_train.mean()*100:.1f}%")''',
        '''# %%[markdown]
# ## XGBoost Baseline''',
        '''model = xgb.XGBClassifier(
    n_estimators=300, max_depth=6, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8,
    scale_pos_weight=(y_train == 0).sum() / (y_train == 1).sum(),
    random_state=42, eval_metric='auc'
)
model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=50)

y_pred_proba = model.predict_proba(X_test)[:, 1]
auc = roc_auc_score(y_test, y_pred_proba)
print(f"\\nAUC-ROC: {auc:.4f}")
print(f"Within target (≥0.88): {auc >= 0.88}")
print(f"\\nClassification Report:")
print(classification_report(y_test, model.predict(X_test)))

threshold = np.percentile(y_pred_proba, 80)
top20_mask = y_pred_proba >= threshold
precision_top20 = y_test[top20_mask].mean()
print(f"Precision@Top20%: {precision_top20:.4f}")''',
        '''# %%[markdown]
# ## SHAP Explainability''',
        '''explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)

plt.figure(figsize=(10, 6))
shap.summary_plot(shap_values, X_test, show=False)
plt.tight_layout()
plt.savefig('../reports/shap_summary.png', bbox_inches='tight')
plt.show()

# Waterfall for first prediction
shap.initjs()
plt.figure()
shap.waterfall_plot(shap.Explanation(
    values=shap_values[0],
    base_values=explainer.expected_value,
    data=X_test.iloc[0].values,
    feature_names=feature_cols
))
plt.savefig('../reports/shap_waterfall.png', bbox_inches='tight')
plt.show()''',
        '''# %%[markdown]
# ## Save Churn Scores & Model''',
        '''churn_df['Churn_Probability'] = model.predict_proba(X)[:, 1]
churn_df['Churn_Risk'] = pd.cut(churn_df['Churn_Probability'],
                                 bins=[0, 0.3, 0.6, 1.0],
                                 labels=['Low', 'Medium', 'High'])

churn_df.to_csv('../data/processed/churn_scores.csv', index=False)
print(f"Saved churn_scores.csv with {len(churn_df)} customers")

import joblib
joblib.dump(model, '../data/processed/models/churn_model.pkl')
print("Saved churn_model.pkl")

# Feature importance
importance_df = pd.DataFrame({
    'feature': feature_cols,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)
importance_df.to_csv('../data/processed/churn_importance.csv', index=False)
print("Saved churn_importance.csv")
print(f"\\nTop 5 features:")
print(importance_df.head())''',
    ]
    save_notebook(cells, "04_churn.ipynb")

def notebook_05_inventory():
    cells = [
        '''# %% [markdown]
# # 05 — Inventory Optimization (Safety Stock + EOQ)
# ## RetailPulse — Zidio Development | March 2026
''',
        '''# %%[markdown]
# ## Imports & Setup''',
        '''import pandas as pd
import numpy as np
from scipy.stats import norm
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')
plt.rcParams['figure.dpi'] = 120
plt.rcParams['savefig.dpi'] = 150''',
        '''# %%[markdown]
# ## Load Processed Data''',
        '''sales = pd.read_parquet('../data/processed/sales_clean.parquet')
products = pd.read_parquet('../data/processed/products_clean.parquet')
print(f"Sales: {len(sales):,} rows")
print(f"Products: {len(products):,}")''',
        '''# %%[markdown]
# ## InventoryOptimizer Class''',
        '''class InventoryOptimizer:
    def __init__(self, service_level=0.95, lead_time_days=7, ordering_cost=50, 
                 holding_cost_pct=0.25, unit_cost=10):
        self.service_level = service_level
        self.lead_time_days = lead_time_days
        self.ordering_cost = ordering_cost
        self.holding_cost_pct = holding_cost_pct
        self.unit_cost = unit_cost
        self.z_score = norm.ppf(service_level)
    
    def compute_safety_stock(self, demand_std, lead_time=None):
        lt = lead_time or self.lead_time_days
        return self.z_score * demand_std * np.sqrt(lt)
    
    def compute_reorder_point(self, avg_daily_demand, demand_std, lead_time=None):
        lt = lead_time or self.lead_time_days
        ss = self.compute_safety_stock(demand_std, lt)
        return round(avg_daily_demand * lt + ss, 0), round(ss, 0)
    
    def compute_eoq(self, annual_demand):
        H = self.unit_cost * self.holding_cost_pct
        return round(np.sqrt((2 * annual_demand * self.ordering_cost) / H), 0)
    
    def generate_recommendations(self, df_products):
        recs = []
        for _, row in df_products.iterrows():
            rop, ss = self.compute_reorder_point(row['avg_daily_demand'], row['demand_std'])
            eoq = self.compute_eoq(row['annual_demand'])
            status = 'REORDER NOW' if row['current_stock'] <= rop else 'OK'
            recs.append({
                'product_id': row['product_id'],
                'Current_Stock': row['current_stock'],
                'Reorder_Point': rop,
                'Safety_Stock': ss,
                'EOQ': eoq,
                'Status': status,
                'Urgency': 'HIGH' if row['current_stock'] <= ss else 'NORMAL'
            })
        return pd.DataFrame(recs)''',
        '''# %%[markdown]
# ## Compute Product-Level Demand''',
        '''product_demand = sales.groupby('product_id').agg(
    avg_daily_demand=('quantity', lambda x: x.sum() / sales['date'].nunique()),
    demand_std=('quantity', 'std'),
    annual_demand=('quantity', 'sum'),
).reset_index()

# Add product names and mock current stock
product_demand = product_demand.merge(products[['product_id', 'category']], on='product_id', how='left')
np.random.seed(42)
product_demand['current_stock'] = np.random.randint(10, 500, len(product_demand))

print(f"Products with demand data: {len(product_demand):,}")
print(product_demand.describe())''',
        '''# %%[markdown]
# ## Generate Recommendations''',
        '''optimizer = InventoryOptimizer(service_level=0.95, lead_time_days=7)
recommendations = optimizer.generate_recommendations(product_demand.head(1000))

print(f"Recommendations generated: {len(recommendations)}")
reorder_now = recommendations[recommendations['Status'] == 'REORDER NOW']
print(f"Need reorder: {len(reorder_now)} products")
print(f"\\nTop urgent items:")
print(recommendations[recommendations['Urgency'] == 'HIGH'].head(10))''',
        '''# %%[markdown]
# ## Visualize Stock Status''',
        '''fig, axes = plt.subplots(1, 2, figsize=(14, 5))
status_counts = recommendations['Status'].value_counts()
axes[0].bar(status_counts.index, status_counts.values, color=['red', 'green'])
axes[0].set_title('Inventory Status')
axes[0].set_ylabel('Count')

urgency_counts = recommendations['Urgency'].value_counts()
axes[1].bar(urgency_counts.index, urgency_counts.values, color=['red', 'orange'])
axes[1].set_title('Urgency Distribution')
axes[1].set_ylabel('Count')
plt.tight_layout()
plt.savefig('../reports/inventory_status.png', bbox_inches='tight')
plt.show()''',
        '''# %%[markdown]
# ## Save Recommendations''',
        '''recommendations.to_csv('../data/processed/inventory_recommendations.csv', index=False)
print(f"Saved inventory_recommendations.csv with {len(recommendations)} recommendations")
product_demand.to_csv('../data/processed/product_demand.csv', index=False)

print(f"\\nInventory Optimization Summary:")
print(f"  Service Level: {optimizer.service_level*100:.0f}%")
print(f"  Lead Time: {optimizer.lead_time_days} days")
print(f"  Products Analyzed: {len(recommendations)}")
print(f"  Reorder Required: {len(reorder_now)} ({len(reorder_now)/len(recommendations)*100:.1f}%)")''',
    ]
    save_notebook(cells, "05_inventory.ipynb")

if __name__ == "__main__":
    print("Generating notebooks...")
    notebook_01_eda()
    notebook_02_segmentation()
    notebook_03_forecasting()
    notebook_04_churn()
    notebook_05_inventory()
    print("Done! All 5 notebooks created.")
