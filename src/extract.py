import logging
from pathlib import Path

import pandas as pd


FILES = {
    "customers": "olist_customers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "categories": "product_category_name_translation.csv",
}

REQUIRED_COLUMNS = {
    "customers": {"customer_id", "customer_unique_id", "customer_city", "customer_state"},
    "products": {"product_id", "product_category_name"},
    "orders": {"order_id", "customer_id", "order_status", "order_purchase_timestamp"},
    "items": {"order_id", "order_item_id", "product_id", "price"},
    "payments": {"order_id", "payment_sequential", "payment_type", "payment_value"},
    "categories": {"product_category_name", "product_category_name_english"},
}


def extract(raw_dir: Path):
    missing = [name for name in FILES.values() if not (raw_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing raw files in {raw_dir}: {', '.join(missing)}")

    tables = {}
    for name, filename in FILES.items():
        tables[name] = pd.read_csv(raw_dir / filename, dtype=str, encoding="utf-8-sig")
        missing_columns = REQUIRED_COLUMNS[name] - set(tables[name].columns)
        if missing_columns:
            raise ValueError(f"{filename}: missing columns: {', '.join(sorted(missing_columns))}")
        logging.info("Loaded %s: %s rows", filename, len(tables[name]))
    return tables
