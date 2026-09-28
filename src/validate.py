def require_unique(frame, columns, name):
    if frame[columns].isna().any().any():
        raise ValueError(f"{name}: null primary key in {columns}")
    if frame.duplicated(subset=columns).any():
        raise ValueError(f"{name}: duplicate primary key in {columns}")


def require_references(frame, column, parent, parent_column, name):
    missing = ~frame[column].isin(parent[parent_column])
    if missing.any():
        raise ValueError(f"{name}: {int(missing.sum())} missing {parent_column} references")


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

    if items["unit_price"].isna().any() or items["unit_price"].lt(0).any():
        raise ValueError("items: unit_price must be non-negative")
    if items["quantity"].le(0).any():
        raise ValueError("items: quantity must be positive")
    if payments["payment_amount"].isna().any() or payments["payment_amount"].lt(0).any():
        raise ValueError("payments: payment_amount must be non-negative")
    if orders["purchase_date"].isna().any():
        raise ValueError("orders: invalid purchase_date")
    return True
