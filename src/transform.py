import pandas as pd


def valid_id(series):
    return series.fillna("").str.fullmatch(r"[0-9a-f]{32}")


def transform(raw):
    report = {}
    tables = {}
    for name, frame in raw.items():
        unique = frame.drop_duplicates().copy()
        report[name] = {
            "input": len(frame),
            "duplicates": len(frame) - len(unique),
            "rejected": 0,
            "excluded": 0,
        }
        tables[name] = unique

    customers = tables["customers"]
    customers["customer_city"] = customers["customer_city"].str.strip().str.title()
    customers["customer_state"] = customers["customer_state"].str.strip().str.upper()
    good = (
        valid_id(customers["customer_id"])
        & valid_id(customers["customer_unique_id"])
        & customers["customer_state"].fillna("").str.fullmatch(r"[A-Z]{2}")
    )
    report["customers"]["rejected"] = int((~good).sum())
    customers = customers.loc[good, ["customer_id", "customer_unique_id", "customer_city", "customer_state"]].copy()
    customers["customer_city"] = customers["customer_city"].fillna("Unknown")
    customers = customers.rename(columns={"customer_city": "city", "customer_state": "state"})

    categories = tables["categories"].dropna(subset=["product_category_name"])
    category_names = categories.set_index("product_category_name")["product_category_name_english"]
    products = tables["products"]
    good = valid_id(products["product_id"])
    report["products"]["rejected"] = int((~good).sum())
    products = products.loc[good, ["product_id", "product_category_name"]].copy()
    products["category"] = products["product_category_name"].map(category_names).fillna("Unknown")
    products = products[["product_id", "category"]]

    orders = tables["orders"]
    orders["order_status"] = orders["order_status"].str.strip().str.lower()
    delivered = orders["order_status"].eq("delivered")
    report["orders"]["excluded"] = int((~delivered).sum())
    orders = orders.loc[delivered, ["order_id", "customer_id", "order_purchase_timestamp"]].copy()
    orders["purchase_date"] = pd.to_datetime(orders["order_purchase_timestamp"], errors="coerce")
    good = valid_id(orders["order_id"]) & valid_id(orders["customer_id"]) & orders["purchase_date"].notna()
    report["orders"]["rejected"] = int((~good).sum())
    orders = orders.loc[good, ["order_id", "customer_id", "purchase_date"]].copy()
    good = orders["customer_id"].isin(customers["customer_id"])
    report["orders"]["rejected"] += int((~good).sum())
    orders = orders.loc[good].copy()
    orders["date_key"] = orders["purchase_date"].dt.strftime("%Y%m%d").astype(int)

    items = tables["items"]
    items["order_item_id"] = pd.to_numeric(items["order_item_id"], errors="coerce")
    items["price"] = pd.to_numeric(items["price"], errors="coerce")
    good = (
        valid_id(items["order_id"])
        & valid_id(items["product_id"])
        & items["order_item_id"].notna()
        & items["order_item_id"].gt(0)
        & items["order_item_id"].mod(1).eq(0)
        & items["price"].notna()
        & items["price"].ge(0)
    )
    report["items"]["rejected"] = int((~good).sum())
    items = items.loc[good, ["order_id", "order_item_id", "product_id", "price"]].copy()
    good = items["product_id"].isin(products["product_id"]) & items["order_id"].isin(tables["orders"]["order_id"])
    report["items"]["rejected"] += int((~good).sum())
    items = items.loc[good].copy()
    good = items["order_id"].isin(orders["order_id"])
    report["items"]["excluded"] = int((~good).sum())
    items = items.loc[good].copy()
    items["order_item_id"] = items["order_item_id"].astype(int)
    items["quantity"] = 1
    items = items.rename(columns={"price": "unit_price"})
    items["total_amount"] = items["unit_price"]

    payments = tables["payments"]
    payments["payment_sequential"] = pd.to_numeric(payments["payment_sequential"], errors="coerce")
    payments["payment_value"] = pd.to_numeric(payments["payment_value"], errors="coerce")
    payments["payment_type"] = payments["payment_type"].str.strip().str.lower()
    good = (
        valid_id(payments["order_id"])
        & payments["payment_sequential"].notna()
        & payments["payment_sequential"].gt(0)
        & payments["payment_sequential"].mod(1).eq(0)
        & payments["payment_value"].notna()
        & payments["payment_value"].ge(0)
        & payments["payment_type"].fillna("").ne("")
    )
    report["payments"]["rejected"] = int((~good).sum())
    payments = payments.loc[good, ["order_id", "payment_sequential", "payment_type", "payment_value"]].copy()
    good = payments["order_id"].isin(tables["orders"]["order_id"])
    report["payments"]["rejected"] += int((~good).sum())
    payments = payments.loc[good].copy()
    good = payments["order_id"].isin(orders["order_id"])
    report["payments"]["excluded"] = int((~good).sum())
    payments = payments.loc[good].copy()
    payments["payment_sequential"] = payments["payment_sequential"].astype(int)
    payments = payments.rename(columns={"payment_value": "payment_amount"})

    dates = orders[["date_key", "purchase_date"]].drop_duplicates(subset=["date_key"]).copy()
    dates["full_date"] = dates["purchase_date"].dt.date
    dates["year"] = dates["purchase_date"].dt.year
    dates["month"] = dates["purchase_date"].dt.month
    dates["day"] = dates["purchase_date"].dt.day
    dates = dates[["date_key", "full_date", "year", "month", "day"]]

    clean = {
        "customers": customers,
        "products": products,
        "orders": orders,
        "items": items,
        "payments": payments,
        "dates": dates,
    }
    return clean, report
