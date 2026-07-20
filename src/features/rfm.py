import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.config import DATA_PROCESSED, RFM_QUANTILES, RANDOM_SEED


def compute_rfm(sales: pd.DataFrame, snapshot_date: pd.Timestamp) -> pd.DataFrame:
    """
    Compute RFM (Recency, Frequency, Monetary) scores for each customer.
    
    Args:
        sales: Clean sales data with customer_id, date, revenue, quantity
        snapshot_date: Reference date for recency calculation
    
    Returns:
        DataFrame with customer_id, recency, frequency, monetary, and RFM scores
    """
    # Aggregate per customer
    customer_agg = sales.groupby("customer_id").agg(
        last_purchase_date=("date", "max"),
        frequency=("transaction_id", "count"),
        monetary=("revenue", "sum"),
        total_quantity=("quantity", "sum"),
        avg_basket_value=("revenue", "mean"),
        unique_products=("product_id", "nunique"),
        unique_stores=("store_id", "nunique"),
        first_purchase_date=("date", "min")
    ).reset_index()
    
    # Recency: days since last purchase
    customer_agg["recency"] = (snapshot_date - customer_agg["last_purchase_date"]).dt.days
    
    # Tenure: days since first purchase
    customer_agg["tenure_days"] = (snapshot_date - customer_agg["first_purchase_date"]).dt.days
    
    # Purchase frequency rate (purchases per 30 days)
    customer_agg["purchase_rate"] = customer_agg["frequency"] / (customer_agg["tenure_days"] / 30 + 1)
    
    return customer_agg


def assign_rfm_scores(rfm_df: pd.DataFrame, n_quantiles: int = 5) -> pd.DataFrame:
    """
    Assign RFM scores using quantile-based binning.
    
    Args:
        rfm_df: DataFrame with recency, frequency, monetary columns
        n_quantiles: Number of quantile bins (default 5 for 1-5 scoring)
    
    Returns:
        DataFrame with R_score, F_score, M_score, RFM_score columns
    """
    df = rfm_df.copy()
    
    # Use rank-based binning to avoid duplicate edge issues
    # Recency: lower is better (recent), so reverse the labels
    df["R_score"] = pd.qcut(df["recency"].rank(method="first"), q=n_quantiles, labels=range(n_quantiles, 0, -1), duplicates="drop").astype(int)
    
    # Frequency: higher is better
    df["F_score"] = pd.qcut(df["frequency"].rank(method="first"), q=n_quantiles, labels=range(1, n_quantiles + 1), duplicates="drop").astype(int)
    
    # Monetary: higher is better
    df["M_score"] = pd.qcut(df["monetary"].rank(method="first"), q=n_quantiles, labels=range(1, n_quantiles + 1), duplicates="drop").astype(int)
    
    # Combined RFM score
    df["RFM_score"] = df["R_score"] * 100 + df["F_score"] * 10 + df["M_score"]
    
    # RFM segment (string)
    df["RFM_segment"] = df["R_score"].astype(str) + df["F_score"].astype(str) + df["M_score"].astype(str)
    
    return df


def assign_segment_labels(rfm_df: pd.DataFrame) -> pd.DataFrame:
    """
    Assign business-friendly segment labels based on RFM scores.
    """
    df = rfm_df.copy()
    
    def label_segment(row):
        r, f, m = row["R_score"], row["F_score"], row["M_score"]
        
        # Champions: high R, high F, high M
        if r >= 4 and f >= 4 and m >= 4:
            return "Champions"
        # Loyal Customers: high F, high M
        elif f >= 4 and m >= 4:
            return "Loyal Customers"
        # Potential Loyalists: good R, good F
        elif r >= 3 and f >= 3:
            return "Potential Loyalists"
        # New Customers: high R, low F
        elif r >= 4 and f <= 2:
            return "New Customers"
        # Promising: good R, low F, low M
        elif r >= 3 and f <= 2:
            return "Promising"
        # Need Attention: medium R, low F
        elif r == 3 and f <= 2:
            return "Need Attention"
        # At Risk: low R, high F/M in past
        elif r <= 2 and (f >= 3 or m >= 3):
            return "At Risk"
        # Lost: low R, low F, low M
        else:
            return "Lost"
    
    df["segment_label"] = df.apply(label_segment, axis=1)
    return df


def create_customer_features(sales: pd.DataFrame, customers: pd.DataFrame,
                              products: pd.DataFrame = None,
                              snapshot_date: pd.Timestamp = None) -> pd.DataFrame:
    if snapshot_date is None:
        snapshot_date = sales["date"].max()

    print(f"Computing RFM features with snapshot date: {snapshot_date}")

    rfm = compute_rfm(sales, snapshot_date)
    rfm = assign_rfm_scores(rfm, n_quantiles=RFM_QUANTILES)
    rfm = assign_segment_labels(rfm)
    rfm = rfm.merge(customers, on="customer_id", how="left")

    if products is None:
        from src.config import DATA_PROCESSED as _dp
        from pathlib import Path
        _p = Path(__file__).parent.parent.parent / "data" / "processed"
        products_path = _p / "products_clean.parquet"
        if products_path.exists():
            products = pd.read_parquet(products_path)

    if products is not None:
        sales_with_cat = sales.merge(products[["product_id", "category"]], on="product_id", how="left")
        cat_diversity = sales_with_cat.groupby("customer_id")["category"].nunique().reset_index(name="category_diversity")
        rfm = rfm.merge(cat_diversity, on="customer_id", how="left")
    
    # Average days between purchases
    purchase_dates = sales.groupby("customer_id")["date"].apply(list).reset_index()
    def avg_gap(dates):
        if len(dates) < 2:
            return 999
        sorted_dates = sorted(dates)
        gaps = [(sorted_dates[i+1] - sorted_dates[i]).days for i in range(len(sorted_dates)-1)]
        return np.mean(gaps)
    
    purchase_dates["avg_purchase_gap"] = purchase_dates["date"].apply(avg_gap)
    rfm = rfm.merge(purchase_dates[["customer_id", "avg_purchase_gap"]], on="customer_id", how="left")
    
    # Promo sensitivity
    promo_sales = sales[sales["is_promo"] == 1].groupby("customer_id").size().reset_index(name="promo_purchases")
    total_sales = sales.groupby("customer_id").size().reset_index(name="total_purchases")
    promo_sensitivity = promo_sales.merge(total_sales, on="customer_id")
    promo_sensitivity["promo_sensitivity"] = promo_sensitivity["promo_purchases"] / promo_sensitivity["total_purchases"]
    rfm = rfm.merge(promo_sensitivity[["customer_id", "promo_sensitivity"]], on="customer_id", how="left")
    
    # Payment method diversity
    pay_diversity = sales.groupby("customer_id")["payment_method"].nunique().reset_index(name="payment_diversity")
    rfm = rfm.merge(pay_diversity, on="customer_id", how="left")
    
    # Fill NaN
    numeric_cols = rfm.select_dtypes(include=[np.number]).columns
    rfm[numeric_cols] = rfm[numeric_cols].fillna(0)
    
    print(f"Created features for {len(rfm)} customers")
    return rfm


def save_customer_features(features: pd.DataFrame):
    """Save customer features to processed data"""
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    features.to_parquet(DATA_PROCESSED / "customer_features.parquet", index=False)
    print(f"Saved customer features to {DATA_PROCESSED / 'customer_features.parquet'}")


if __name__ == "__main__":
    from src.config import DATA_PROCESSED
    
    sales = pd.read_parquet(DATA_PROCESSED / "sales_clean.parquet")
    customers = pd.read_parquet(DATA_PROCESSED / "customers_clean.parquet")
    
    snapshot_date = pd.Timestamp("2024-12-31")
    features = create_customer_features(sales, customers, snapshot_date)
    save_customer_features(features)
    
    # Print segment distribution
    print("\nSegment Distribution:")
    print(features["segment_label"].value_counts())