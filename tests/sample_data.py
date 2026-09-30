import pandas as pd


def source_id(number):
    return f"{number:032x}"


def raw_tables():
    """Synthetic source rows: two items and two payments on one delivered order."""
    return {
        "customers": pd.DataFrame([
            [source_id(1), source_id(2), " sao paulo ", " sp "],
        ], columns=["customer_id", "customer_unique_id", "customer_city", "customer_state"]),
        "products": pd.DataFrame([
            [source_id(3), "livros"],
        ], columns=["product_id", "product_category_name"]),
        "orders": pd.DataFrame([
            [source_id(4), source_id(1), "delivered", "2018-01-02 12:00:00"],
            [source_id(5), source_id(1), "canceled", "2018-01-03 12:00:00"],
        ], columns=["order_id", "customer_id", "order_status", "order_purchase_timestamp"]),
        "items": pd.DataFrame([
            [source_id(4), "1", source_id(3), "10.50"],
            [source_id(4), "2", source_id(3), "20.00"],
            [source_id(5), "1", source_id(3), "5.00"],
        ], columns=["order_id", "order_item_id", "product_id", "price"]),
        "payments": pd.DataFrame([
            [source_id(4), "1", " Credit_Card ", "25.50"],
            [source_id(4), "2", "voucher", "5.00"],
            [source_id(5), "1", "credit_card", "5.00"],
        ], columns=["order_id", "payment_sequential", "payment_type", "payment_value"]),
        "categories": pd.DataFrame([
            ["livros", "books"],
        ], columns=["product_category_name", "product_category_name_english"]),
    }
