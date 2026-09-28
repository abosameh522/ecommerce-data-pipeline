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


def extract(raw_dir: Path):
    missing = [name for name in FILES.values() if not (raw_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing raw files in {raw_dir}: {', '.join(missing)}")

    tables = {}
    for name, filename in FILES.items():
        tables[name] = pd.read_csv(raw_dir / filename, dtype=str, encoding="utf-8-sig")
        logging.info("Loaded %s: %s rows", filename, len(tables[name]))
    return tables
