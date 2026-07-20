"""Data validation module.

Runs quality checks on cleaned datasets (sales, customers, products)
to ensure schema compliance and business rule adherence before use.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
import json

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.config import DATA_PROCESSED, DATA_RAW, N_STORES, N_PRODUCTS, N_CUSTOMERS

def validate_sales(df: pd.DataFrame) -> dict:
    results = {"table": "sales", "row_count": len(df), "checks": {}}
    key_cols = ["transaction_id", "date", "store_id", "product_id", "customer_id", "quantity", "revenue"]
    for col in key_cols:
        null_count = int(df[col].isnull().sum())
        results["checks"][f"{col}_not_null"] = {"passed": null_count == 0, "null_count": null_count}
    neg_qty = int((df["quantity"] <= 0).sum())
    results["checks"]["quantity_positive"] = {"passed": neg_qty == 0, "negative_count": neg_qty}
    neg_rev = int((df["revenue"] < 0).sum())
    results["checks"]["revenue_non_negative"] = {"passed": neg_rev == 0, "negative_count": neg_rev}
    min_date, max_date = str(df["date"].min()), str(df["date"].max())
    results["checks"]["date_range"] = {"passed": True, "min_date": min_date, "max_date": max_date}
    return results

def validate_customers(df: pd.DataFrame) -> dict:
    results = {"table": "customers", "row_count": len(df), "checks": {}}
    dup_ids = int(df["customer_id"].duplicated().sum())
    results["checks"]["unique_customer_ids"] = {"passed": dup_ids == 0, "duplicate_count": dup_ids}
    valid_ages = {"18-25", "26-35", "36-45", "46-55", "56-65", "65+"}
    invalid_ages = list(set(df["age_group"].unique()) - valid_ages)
    results["checks"]["age_group_valid"] = {"passed": len(invalid_ages) == 0, "invalid_ages": invalid_ages}
    return results

def validate_products(df: pd.DataFrame) -> dict:
    results = {"table": "products", "row_count": len(df), "checks": {}}
    dup_ids = int(df["product_id"].duplicated().sum())
    results["checks"]["unique_product_ids"] = {"passed": dup_ids == 0, "duplicate_count": dup_ids}
    invalid_margin = int((df["unit_price"] <= df["unit_cost"]).sum())
    results["checks"]["price_gt_cost"] = {"passed": invalid_margin == 0, "invalid_count": invalid_margin}
    return results

def run_all_validations():
    print("Running data validation...")
    files = {
        "sales": ("sales_clean.parquet", validate_sales),
        "customers": ("customers_clean.parquet", validate_customers),
        "products": ("products_clean.parquet", validate_products),
    }
    all_results = {}
    total_checks = 0
    passed_checks = 0
    for table, (filename, validator) in files.items():
        path = DATA_PROCESSED / filename
        if not path.exists():
            print(f"  SKIP: {table} — file not found")
            continue
        df = pd.read_parquet(path)
        result = validator(df)
        all_results[table] = result
        for check_name, check_result in result["checks"].items():
            total_checks += 1
            if check_result["passed"]:
                passed_checks += 1
            else:
                print(f"  FAIL: {table}.{check_name} - {check_result}")
    print(f"\nValidation Summary: {passed_checks}/{total_checks} checks passed")
    report_path = DATA_PROCESSED / "validation_report.json"
    with open(report_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"Report saved to: {report_path}")
    return passed_checks == total_checks

if __name__ == "__main__":
    success = run_all_validations()
    sys.exit(0 if success else 1)
