import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.config import DATA_RAW, DATA_PROCESSED

def load_raw_data():
    """Load all raw CSV files"""
    sales = pd.read_csv(DATA_RAW / "sales.csv", parse_dates=["date"])
    customers = pd.read_csv(DATA_RAW / "customers.csv", parse_dates=["signup_date"])
    products = pd.read_csv(DATA_RAW / "products.csv")
    stores = pd.read_csv(DATA_RAW / "stores.csv", parse_dates=["opening_date"])
    inventory = pd.read_csv(DATA_RAW / "inventory.csv", parse_dates=["date"])
    holidays = pd.read_csv(DATA_RAW / "holidays.csv", parse_dates=["date"])
    
    return sales, customers, products, stores, inventory, holidays


def clean_sales(sales: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    """Clean and enrich sales data"""
    df = sales.copy()
    
    # Remove negative quantities (returns handled separately)
    df = df[df["quantity"] > 0].copy()
    
    # Ensure revenue = quantity * unit_price * (1 - promo_discount)
    df["expected_revenue"] = df["quantity"] * df["unit_price"] * (1 - df["is_promo"] * 0.15)
    df["revenue_diff"] = (df["revenue"] - df["expected_revenue"]).abs()
    
    # Fix revenue if mismatch > 1%
    mask = df["revenue_diff"] > df["expected_revenue"] * 0.01
    df.loc[mask, "revenue"] = df.loc[mask, "expected_revenue"]
    
    # Add category from products
    df = df.merge(products[["product_id", "category", "subcategory"]], on="product_id", how="left")
    
    # Add store info
    # stores = pd.read_parquet(DATA_PROCESSED / "stores_clean.parquet")
    # df = df.merge(stores[["store_id", "region", "store_type"]], on="store_id", how="left")
    
    # Date features
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["day_of_week"] = df["date"].dt.dayofweek
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    df["week_of_year"] = df["date"].dt.isocalendar().week
    
    # Sort
    df = df.sort_values(["date", "store_id", "product_id", "customer_id"]).reset_index(drop=True)
    
    return df


def clean_customers(customers: pd.DataFrame) -> pd.DataFrame:
    """Clean customer data"""
    df = customers.copy()
    
    # Standardize segment names
    segment_map = {
        "Premium": "Premium",
        "Regular": "Regular", 
        "Budget": "Budget",
        "Occasional": "Occasional"
    }
    df["segment"] = df["segment"].map(segment_map).fillna("Regular")
    
    # Standardize age groups
    age_order = ["18-25", "26-35", "36-45", "46-55", "56-65", "65+"]
    df["age_group"] = pd.Categorical(df["age_group"], categories=age_order, ordered=True)
    
    # Tenure in days
    df["tenure_days"] = (pd.Timestamp("2024-12-31") - df["signup_date"]).dt.days
    
    return df


def clean_products(products: pd.DataFrame) -> pd.DataFrame:
    """Clean product data"""
    df = products.copy()
    
    # Standardize category names
    df["category"] = df["category"].str.strip()
    df["subcategory"] = df["subcategory"].str.strip()
    df["brand_tier"] = df["brand_tier"].str.strip()
    
    # Price validation
    df = df[df["unit_price"] > df["unit_cost"]].copy()
    df["margin"] = (df["unit_price"] - df["unit_cost"]) / df["unit_price"]
    
    return df


def clean_stores(stores: pd.DataFrame) -> pd.DataFrame:
    """Clean store data"""
    df = stores.copy()
    df["region"] = df["region"].str.strip()
    df["store_type"] = df["store_type"].str.strip()
    return df


def clean_inventory(inventory: pd.DataFrame, sales: pd.DataFrame, products: pd.DataFrame, stores: pd.DataFrame) -> pd.DataFrame:
    """Clean and enrich inventory data (chunked for memory efficiency)"""
    daily_demand = sales.groupby(["date", "store_id", "product_id"])["quantity"].sum().reset_index()
    daily_demand.columns = ["date", "store_id", "product_id", "actual_demand"]

    results = []
    chunk_size = 200000
    for start in range(0, len(inventory), chunk_size):
        chunk = inventory.iloc[start:start + chunk_size].copy()
        chunk = chunk.merge(daily_demand, on=["date", "store_id", "product_id"], how="left")
        chunk["actual_demand"] = chunk["actual_demand"].fillna(0)
        chunk["is_stockout"] = (chunk["stock_level"] == 0).astype(int)
        chunk["days_of_supply"] = np.where(
            chunk["actual_demand"] > 0,
            chunk["stock_level"] / chunk["actual_demand"],
            999
        )
        chunk["reorder_needed"] = (chunk["stock_level"] <= chunk["reorder_point"]).astype(int)
        results.append(chunk)

    return pd.concat(results, ignore_index=True)


def clean_holidays(holidays: pd.DataFrame) -> pd.DataFrame:
    """Clean holidays"""
    df = holidays.copy()
    df["holiday_name"] = df["holiday_name"].str.strip()
    return df


def create_daily_sales_aggregate(sales: pd.DataFrame) -> pd.DataFrame:
    """Create daily aggregate per store-product for forecasting"""
    sales["promo_quantity"] = sales["quantity"] * sales["is_promo"]
    daily = sales.groupby(["date", "store_id", "product_id"], sort=False).agg(
        total_quantity=("quantity", "sum"),
        total_revenue=("revenue", "sum"),
        transaction_count=("transaction_id", "count"),
        unique_customers=("customer_id", "nunique"),
        promo_quantity=("promo_quantity", "sum"),
    ).reset_index()
    daily = daily.sort_values(["store_id", "product_id", "date"]).reset_index(drop=True)
    return daily


def save_processed_data(sales, customers, products, stores, inventory, holidays, daily_sales):
    """Save all cleaned data as parquet"""
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    
    sales.to_parquet(DATA_PROCESSED / "sales_clean.parquet", index=False)
    customers.to_parquet(DATA_PROCESSED / "customers_clean.parquet", index=False)
    products.to_parquet(DATA_PROCESSED / "products_clean.parquet", index=False)
    stores.to_parquet(DATA_PROCESSED / "stores_clean.parquet", index=False)
    inventory.to_parquet(DATA_PROCESSED / "inventory_clean.parquet", index=False)
    holidays.to_parquet(DATA_PROCESSED / "holidays_clean.parquet", index=False)
    daily_sales.to_parquet(DATA_PROCESSED / "daily_sales_ts.parquet", index=False)
    
    print("Saved processed data:")
    print(f"  sales_clean.parquet:        {len(sales):,} rows")
    print(f"  customers_clean.parquet:    {len(customers):,} rows")
    print(f"  products_clean.parquet:     {len(products):,} rows")
    print(f"  stores_clean.parquet:       {len(stores):,} rows")
    print(f"  inventory_clean.parquet:    {len(inventory):,} rows")
    print(f"  holidays_clean.parquet:     {len(holidays):,} rows")
    print(f"  daily_sales_ts.parquet:     {len(daily_sales):,} rows")


def run_etl():
    """Run complete ETL pipeline"""
    print("Starting ETL pipeline...")
    
    # Load raw data
    print("Loading raw data...")
    sales, customers, products, stores, inventory, holidays = load_raw_data()
    print(f"  Raw sales: {len(sales):,} rows")
    print(f"  Raw customers: {len(customers):,} rows")
    print(f"  Raw products: {len(products):,} rows")
    print(f"  Raw stores: {len(stores):,} rows")
    print(f"  Raw inventory: {len(inventory):,} rows")
    print(f"  Raw holidays: {len(holidays):,} rows")
    
    # Clean each dataset
    print("\nCleaning data...")
    sales_clean = clean_sales(sales, products)
    customers_clean = clean_customers(customers)
    products_clean = clean_products(products)
    stores_clean = clean_stores(stores)
    inventory_clean = clean_inventory(inventory, sales_clean, products_clean, stores_clean)
    holidays_clean = clean_holidays(holidays)
    
    # Create daily aggregate for forecasting
    print("\nCreating daily sales aggregates...")
    daily_sales = create_daily_sales_aggregate(sales_clean)
    
    # Save
    print("\nSaving processed data...")
    save_processed_data(sales_clean, customers_clean, products_clean, stores_clean, 
                        inventory_clean, holidays_clean, daily_sales)
    
    print("\nETL pipeline completed successfully!")
    
    return {
        "sales": sales_clean,
        "customers": customers_clean,
        "products": products_clean,
        "stores": stores_clean,
        "inventory": inventory_clean,
        "holidays": holidays_clean,
        "daily_sales": daily_sales
    }


if __name__ == "__main__":
    run_etl()