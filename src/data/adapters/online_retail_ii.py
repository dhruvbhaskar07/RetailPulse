"""Online Retail II dataset adapter.

Transforms the UCI Online Retail II Excel dataset into the internal
RetailPulse schema, producing six CSV files:
- sales.csv (779K transactions), customers.csv (5.9K), products.csv (5.3K)
- stores.csv (41), holidays.csv (12), inventory.csv (weekly snapshots)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from src.config import DATA_RAW

XLSX_PATH = DATA_RAW / "online_retail_ii" / "online_retail_II.xlsx"
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

COLUMN_MAP = {
    "Invoice": "invoice_no",
    "StockCode": "stock_code",
    "Description": "description",
    "Quantity": "quantity",
    "InvoiceDate": "invoice_date",
    "Price": "unit_price",
    "Customer ID": "customer_id",
    "Country": "country",
}

def load_and_combine():
    xl = pd.ExcelFile(XLSX_PATH)
    sheets = []
    for sheet in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=sheet)
        sheets.append(df)
    df = pd.concat(sheets, ignore_index=True)
    df = df.rename(columns=COLUMN_MAP)
    df["invoice_date"] = pd.to_datetime(df["invoice_date"])
    return df

def clean(df):
    before = len(df)
    cancelled = df["invoice_no"].astype(str).str.startswith("C")
    df = df[~cancelled].copy()
    print(f"  Removed cancelled: {cancelled.sum()} rows")
    df = df[df["quantity"] > 0].copy()
    df = df[df["unit_price"] > 0].copy()
    before_null = df["customer_id"].isnull().sum()
    df = df.dropna(subset=["customer_id"]).copy()
    print(f"  Dropped null customer_id: {before_null} rows")
    df["customer_id"] = df["customer_id"].astype(int)
    df = df.drop_duplicates()
    df = df.sort_values("invoice_date").reset_index(drop=True)
    df["total_amount"] = (df["quantity"] * df["unit_price"]).round(2)
    print(f"  After clean: {len(df)} rows (from {before})")
    return df

def build_sales(df):
    sales = df.rename(columns={
        "invoice_no": "transaction_id",
        "invoice_date": "date",
        "total_amount": "revenue",
    }).copy()
    sales["store_id"] = sales.groupby("country").ngroup() + 1
    sales["product_id"] = sales.groupby("stock_code").ngroup() + 1
    sales["is_promo"] = np.random.choice([0, 1], len(sales), p=[0.85, 0.15])
    sales["payment_method"] = np.random.choice(
        ["Cash", "Card", "Mobile", "Online"], len(sales),
        p=[0.25, 0.45, 0.15, 0.15]
    )
    sales = sales.sort_values("date").reset_index(drop=True)
    sales["transaction_id"] = range(1, len(sales) + 1)
    return sales[["transaction_id", "date", "store_id", "product_id",
                   "customer_id", "quantity", "unit_price", "revenue",
                   "is_promo", "payment_method"]]

def build_customers(df):
    cust = df.groupby("customer_id").agg(
        first_purchase=("invoice_date", "min"),
        country=("country", "first"),
    ).reset_index()
    region_map = {
        "United Kingdom": "North", "Germany": "Central",
        "France": "West", "EIRE": "North", "Spain": "South",
        "Netherlands": "Central", "Belgium": "Central",
        "Switzerland": "Central", "Portugal": "South",
        "Australia": "East", "Singapore": "East", "Japan": "East",
        "USA": "West", "Canada": "North",
    }
    cust["region"] = cust["country"].map(lambda x: region_map.get(x, "Other"))
    cust["age_group"] = np.random.choice(
        ["18-25", "26-35", "36-45", "46-55", "56-65", "65+"],
        len(cust), p=[0.12, 0.28, 0.25, 0.15, 0.12, 0.08]
    )
    cust["segment"] = np.random.choice(
        ["Premium", "Regular", "Budget", "Occasional"],
        len(cust), p=[0.15, 0.40, 0.25, 0.20]
    )
    cust["signup_date"] = cust["first_purchase"] - pd.to_timedelta(
        np.random.randint(0, 365, len(cust)), unit="D"
    )
    cust["email_optin"] = np.random.choice([True, False], len(cust), p=[0.7, 0.3])
    cust["app_user"] = np.random.choice([True, False], len(cust), p=[0.4, 0.6])
    return cust[["customer_id", "region", "age_group", "segment",
                  "signup_date", "email_optin", "app_user"]]

def build_products(df):
    prods = df.groupby(["stock_code", "description"]).agg(
        unit_price_mean=("unit_price", "mean"),
    ).reset_index()
    prods["product_id"] = range(1, len(prods) + 1)
    prods["category"] = "General"
    prods["subcategory"] = "Retail"
    prods["unit_cost"] = (
        prods["unit_price_mean"] * np.random.uniform(0.5, 0.85, len(prods))
    ).round(2)
    prods["unit_price"] = prods["unit_price_mean"].round(2)
    prods["brand_tier"] = np.random.choice(
        ["Premium", "Mainstream", "Value"], len(prods),
        p=[0.15, 0.6, 0.25]
    )
    return prods[["product_id", "category", "subcategory",
                   "unit_cost", "unit_price", "brand_tier"]]

def build_stores(df):
    countries = df["country"].unique()
    region_map = {
        "United Kingdom": "North", "Germany": "Central",
        "France": "West", "EIRE": "North", "Spain": "South",
        "Netherlands": "Central", "Belgium": "Central",
        "Switzerland": "Central", "Portugal": "South",
        "Australia": "East", "Singapore": "East", "Japan": "East",
        "USA": "West", "Canada": "North",
    }
    stores = pd.DataFrame({
        "store_id": range(1, len(countries) + 1),
        "country": list(countries),
        "region": [region_map.get(c, "Other") for c in countries],
        "store_type": ["Online"] * len(countries),
        "size_sqft": np.random.randint(500, 5000, len(countries)),
        "opening_date": pd.Timestamp("2009-01-01"),
    })
    return stores[["store_id", "region", "store_type", "size_sqft", "opening_date"]]

def build_holidays():
    years = [2009, 2010, 2011]
    holidays = []
    for y in years:
        holidays.extend([
            (pd.Timestamp(f"{y}-01-01"), "New Year"),
            (pd.Timestamp(f"{y}-12-25"), "Christmas"),
            (pd.Timestamp(f"{y}-11-24"), "Black Friday"),
            (pd.Timestamp(f"{y}-11-27"), "Cyber Monday"),
        ])
    return pd.DataFrame(holidays, columns=["date", "holiday_name"])

def build_inventory(sales, products, stores):
    daily_demand = sales.groupby(["date", "store_id", "product_id"])["quantity"].sum().reset_index()
    daily_demand.columns = ["date", "store_id", "product_id", "daily_demand"]

    active_combos = sales[["store_id", "product_id"]].drop_duplicates()
    n_combos = len(active_combos)
    print(f"  {n_combos:,} active store-product combinations")

    weekly_range = pd.date_range(
        sales["date"].min(), sales["date"].max(), freq="W-MON"
    )

    all_weeks = []
    chunk_size = 500
    for start in range(0, n_combos, chunk_size):
        chunk = active_combos.iloc[start:start + chunk_size]
        chunk_rows = []
        for _, row in chunk.iterrows():
            sid, pid = row["store_id"], row["product_id"]
            cd = daily_demand[
                (daily_demand["store_id"] == sid) &
                (daily_demand["product_id"] == pid)
            ]
            cd = cd.set_index("date")["daily_demand"].reindex(
                weekly_range, fill_value=0
            ).reset_index()
            cd.columns = ["date", "daily_demand"]
            cd["store_id"] = sid
            cd["product_id"] = pid
            initial_stock = np.random.poisson(lam=50) + 20
            stock = initial_stock
            levels = []
            for d in cd["daily_demand"].values:
                stock = max(0, stock - d)
                if stock < 10 and np.random.random() < 0.3:
                    stock += np.random.randint(30, 100)
                levels.append(stock)
            cd["stock_level"] = levels
            chunk_rows.append(cd)
        all_weeks.append(pd.concat(chunk_rows, ignore_index=True))

    inv = pd.concat(all_weeks, ignore_index=True)

    inv["reorder_point"] = inv.groupby(["store_id", "product_id"])["daily_demand"].transform(
        lambda x: max(10, x.rolling(4, min_periods=1).mean().iloc[-1] * 4)
    )
    inv["is_stockout"] = (inv["stock_level"] == 0).astype(int)
    return inv[["date", "store_id", "product_id", "stock_level",
                "daily_demand", "reorder_point", "is_stockout"]]

def main():
    print("Loading Online Retail II dataset...")
    df = load_and_combine()
    print(f"  Loaded: {len(df):,} rows, {df['invoice_no'].nunique():,} invoices, "
          f"{df['customer_id'].nunique():,} customers, "
          f"{df['country'].nunique()} countries")

    print("\nCleaning...")
    df = clean(df)

    print("\nBuilding sales...")
    sales = build_sales(df)
    print(f"  {len(sales):,} transactions")

    print("\nBuilding customers...")
    customers = build_customers(df)
    print(f"  {len(customers):,} customers")

    print("\nBuilding products...")
    products = build_products(df)
    print(f"  {len(products):,} products")

    print("\nBuilding stores...")
    stores = build_stores(df)
    print(f"  {len(stores):,} stores")

    print("\nBuilding holidays...")
    holidays = build_holidays()
    print(f"  {len(holidays):,} holidays")

    print("\nBuilding inventory...")
    inventory = build_inventory(sales, products, stores)
    print(f"  {len(inventory):,} inventory records")

    print(f"\nSaving to {DATA_RAW}...")
    sales.to_csv(DATA_RAW / "sales.csv", index=False)
    customers.to_csv(DATA_RAW / "customers.csv", index=False)
    products.to_csv(DATA_RAW / "products.csv", index=False)
    stores.to_csv(DATA_RAW / "stores.csv", index=False)
    holidays.to_csv(DATA_RAW / "holidays.csv", index=False)
    inventory.to_csv(DATA_RAW / "inventory.csv", index=False)

    print("\nDone! Adapted Online Retail II to internal schema.")

if __name__ == "__main__":
    main()
