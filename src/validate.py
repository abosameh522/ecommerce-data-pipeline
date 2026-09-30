from math import isfinite


def require_unique(frame, columns, name):
    if frame[columns].isna().any().any():
        raise ValueError(f"{name}: null primary key in {columns}")
    if frame.duplicated(subset=columns).any():
        raise ValueError(f"{name}: duplicate primary key in {columns}")


def require_references(frame, column, parent, parent_column, name):
    missing = ~frame[column].isin(parent[parent_column])
    if missing.any():
        raise ValueError(f"{name}: {int(missing.sum())} missing {parent_column} references")


def require_amount(series, upper_bound, name):
    if not (series.map(isfinite) & series.ge(0) & series.round(2).lt(upper_bound)).all():
        raise ValueError(f"{name}: must be finite, non-negative and fit the database column")


def require_positive_integer(series, name):
    if not (series.ge(1) & series.lt(2**31) & series.mod(1).eq(0)).all():
        raise ValueError(f"{name}: must be a positive PostgreSQL INTEGER")


def validate(clean):
    customers = clean["customers"]
    products = clean["products"]
    orders = clean["orders"]
    items = clean["items"]
    payments = clean["payments"]
    dates = clean["dates"]

    require_unique(customers, ["customer_id"], "customers")
    require_unique(products, ["product_id"], "products")
    require_unique(orders, ["order_id"], "orders")
    require_unique(items, ["order_id", "order_item_id"], "items")
    require_unique(payments, ["order_id", "payment_sequential"], "payments")
    require_unique(dates, ["date_key"], "dates")

    require_references(orders, "customer_id", customers, "customer_id", "orders")
    require_references(items, "order_id", orders, "order_id", "items")
    require_references(items, "product_id", products, "product_id", "items")
    require_references(payments, "order_id", orders, "order_id", "payments")
    require_references(orders, "date_key", dates, "date_key", "orders")

    require_amount(items["unit_price"], 10**10, "items.unit_price")
    require_amount(items["total_amount"], 10**12, "items.total_amount")
    require_amount(payments["payment_amount"], 10**12, "payments.payment_amount")
    require_positive_integer(items["order_item_id"], "items.order_item_id")
    require_positive_integer(items["quantity"], "items.quantity")
    require_positive_integer(payments["payment_sequential"], "payments.payment_sequential")
    if not items["total_amount"].round(2).eq((items["quantity"] * items["unit_price"]).round(2)).all():
        raise ValueError("items: total_amount does not match quantity times unit_price")
    if orders["purchase_date"].isna().any():
        raise ValueError("orders: invalid purchase_date")
    return True
