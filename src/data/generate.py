import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from src.config import (
    DATA_RAW, RANDOM_SEED, N_CUSTOMERS, N_PRODUCTS, N_STORES,
    START_DATE, END_DATE
)

np.random.seed(RANDOM_SEED)

START = pd.Timestamp(START_DATE)
END = pd.Timestamp(END_DATE)
DAYS = (END - START).days


def generate_stores(n=N_STORES):
    regions = ["North", "South", "East", "West", "Central"]
    store_types = ["Supermarket", "Convenience", "Hypermarket", "Online"]
    sizes = np.random.choice([2000, 5000, 10000, 20000, 50000], n, p=[0.2, 0.3, 0.25, 0.15, 0.1])

    df = pd.DataFrame({
        "store_id": range(1, n + 1),
        "region": np.random.choice(regions, n, p=[0.25, 0.2, 0.2, 0.2, 0.15]),
        "store_type": np.random.choice(store_types, n, p=[0.4, 0.2, 0.25, 0.15]),
        "size_sqft": sizes,
        "opening_date": START - pd.to_timedelta(np.random.randint(0, 1000, n), unit="D"),
    })
    return df


def generate_products(n=N_PRODUCTS):
    categories = {
        "Groceries": ["Dairy", "Bakery", "Produce", "Meat", "Pantry"],
        "Personal Care": ["Skincare", "Haircare", "Oral Care", "Fragrance"],
        "Household": ["Cleaning", "Laundry", "Paper Goods", "Kitchen"],
        "Electronics": ["Accessories", "Small Appliances", "Batteries"],
        "Apparel": ["Men", "Women", "Kids", "Accessories"],
    }

    rows = []
    for i in range(1, n + 1):
        cat = np.random.choice(list(categories.keys()), p=[0.35, 0.15, 0.2, 0.1, 0.2])
        subcat = np.random.choice(categories[cat])
        cost = np.random.lognormal(mean=2.0, sigma=0.8)
        margin = np.random.uniform(0.15, 0.55)
        price = cost * (1 + margin)

        rows.append({
            "product_id": i,
            "category": cat,
            "subcategory": subcat,
            "unit_cost": round(cost, 2),
            "unit_price": round(price, 2),
            "brand_tier": np.random.choice(["Premium", "Mainstream", "Value"], p=[0.15, 0.6, 0.25]),
        })
    return pd.DataFrame(rows)


def generate_customers(n=N_CUSTOMERS):
    regions = ["North", "South", "East", "West", "Central"]
    age_groups = ["18-25", "26-35", "36-45", "46-55", "56-65", "65+"]
    segments = ["Premium", "Regular", "Budget", "Occasional"]

    df = pd.DataFrame({
        "customer_id": range(1, n + 1),
        "region": np.random.choice(regions, n, p=[0.25, 0.2, 0.2, 0.2, 0.15]),
        "age_group": np.random.choice(age_groups, n, p=[0.15, 0.25, 0.25, 0.15, 0.1, 0.1]),
        "segment": np.random.choice(segments, n, p=[0.15, 0.4, 0.25, 0.2]),
        "signup_date": START + pd.to_timedelta(np.random.randint(0, DAYS, n), unit="D"),
        "email_optin": np.random.choice([True, False], n, p=[0.7, 0.3]),
        "app_user": np.random.choice([True, False], n, p=[0.4, 0.6]),
    })
    return df


def generate_sales(stores, products, customers):
    n_transactions = int(DAYS * N_STORES * 150)

    dates = START + pd.to_timedelta(np.random.randint(0, DAYS, n_transactions), unit="D")
    store_ids = np.random.choice(stores["store_id"], n_transactions, p=stores["size_sqft"] / stores["size_sqft"].sum())
    product_ids = np.random.choice(products["product_id"], n_transactions)
    customer_ids = np.random.choice(customers["customer_id"], n_transactions, p=np.random.dirichlet(np.ones(N_CUSTOMERS) * 0.1))

    promo_prob = 0.15
    is_promo = np.random.choice([0, 1], n_transactions, p=[1-promo_prob, promo_prob])

    quantity = np.random.poisson(lam=2, size=n_transactions) + 1
    product_prices = products.set_index("product_id").loc[product_ids, "unit_price"].values
    revenue = quantity * product_prices * (1 - is_promo * 0.15)

    df = pd.DataFrame({
        "transaction_id": range(1, n_transactions + 1),
        "date": dates,
        "store_id": store_ids,
        "product_id": product_ids,
        "customer_id": customer_ids,
        "quantity": quantity,
        "unit_price": product_prices,
        "revenue": np.round(revenue, 2),
        "is_promo": is_promo,
        "payment_method": np.random.choice(["Cash", "Card", "Mobile", "Online"], n_transactions, p=[0.3, 0.45, 0.15, 0.1]),
    })

    df = df.sort_values("date").reset_index(drop=True)
    return df


def generate_inventory(stores, products, sales):
    """Generate inventory data efficiently - only for store-product combos that have sales"""
    daily_demand = sales.groupby(["date", "store_id", "product_id"])["quantity"].sum().reset_index()
    daily_demand.columns = ["date", "store_id", "product_id", "daily_demand"]

    # Only generate inventory for store-product pairs that actually had sales
    active_combos = sales[["store_id", "product_id"]].drop_duplicates()
    n_active = len(active_combos)
    
    date_range = pd.date_range(START, END, freq="D")
    
    # Create inventory for active combos only
    rows = []
    for _, row in active_combos.iterrows():
        store_id = row["store_id"]
        product_id = row["product_id"]
        
        # Get demand for this combo
        combo_demand = daily_demand[
            (daily_demand["store_id"] == store_id) & 
            (daily_demand["product_id"] == product_id)
        ].set_index("date")["daily_demand"]
        
        # Reindex to full date range, fill missing with 0
        combo_demand = combo_demand.reindex(date_range, fill_value=0).reset_index()
        combo_demand.columns = ["date", "daily_demand"]
        combo_demand["store_id"] = store_id
        combo_demand["product_id"] = product_id
        
        # Simulate inventory levels vectorized
        initial_stock = np.random.poisson(lam=50) + 20
        stock = initial_stock
        stock_levels = []
        
        for demand in combo_demand["daily_demand"].values:
            stock = max(0, stock - demand)
            if stock < 10 and np.random.random() < 0.3:
                stock += np.random.randint(30, 100)
            stock_levels.append(stock)
        
        combo_demand["stock_level"] = stock_levels
        rows.append(combo_demand)
    
    inv = pd.concat(rows, ignore_index=True)
    
    # Add reorder point and stockout flag
    inv["reorder_point"] = inv.groupby(["store_id", "product_id"])["daily_demand"].transform(
        lambda x: max(10, x.rolling(7, min_periods=1).mean().iloc[-1] * 7)
    )
    inv["is_stockout"] = (inv["stock_level"] == 0).astype(int)

    return inv[["date", "store_id", "product_id", "stock_level", "daily_demand", "reorder_point", "is_stockout"]]


def generate_holidays():
    years = range(START.year, END.year + 1)
    holidays = []
    for y in years:
        holidays.extend([
            (pd.Timestamp(f"{y}-01-01"), "New Year"),
            (pd.Timestamp(f"{y}-12-25"), "Christmas"),
            (pd.Timestamp(f"{y}-11-24"), "Black Friday"),
            (pd.Timestamp(f"{y}-11-27"), "Cyber Monday"),
        ])
    return pd.DataFrame(holidays, columns=["date", "holiday_name"])


def main():
    print("Generating synthetic retail data...")
    print(f"Period: {START_DATE} to {END_DATE}")
    print(f"Stores: {N_STORES}, Products: {N_PRODUCTS}, Customers: {N_CUSTOMERS}")

    stores = generate_stores()
    products = generate_products()
    customers = generate_customers()
    sales = generate_sales(stores, products, customers)
    inventory = generate_inventory(stores, products, sales)
    holidays = generate_holidays()

    stores.to_csv(DATA_RAW / "stores.csv", index=False)
    products.to_csv(DATA_RAW / "products.csv", index=False)
    customers.to_csv(DATA_RAW / "customers.csv", index=False)
    sales.to_csv(DATA_RAW / "sales.csv", index=False)
    inventory.to_csv(DATA_RAW / "inventory.csv", index=False)
    holidays.to_csv(DATA_RAW / "holidays.csv", index=False)

    print("\nData generated successfully!")
    print(f"  stores.csv:       {len(stores):,} rows")
    print(f"  products.csv:     {len(products):,} rows")
    print(f"  customers.csv:    {len(customers):,} rows")
    print(f"  sales.csv:        {len(sales):,} rows")
    print(f"  inventory.csv:    {len(inventory):,} rows")
    print(f"  holidays.csv:     {len(holidays):,} rows")
    print(f"\nFiles saved to: {DATA_RAW}")


if __name__ == "__main__":
    main()