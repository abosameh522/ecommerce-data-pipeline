import os
from pathlib import Path

import psycopg


PROJECT_DIR = Path(__file__).resolve().parents[1]


def connect():
    options = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
        "dbname": os.getenv("DB_NAME", "ecommerce_warehouse"),
        "user": os.getenv("DB_USER", os.getenv("USER", "postgres")),
        "connect_timeout": 10,
    }
    if os.getenv("DB_PASSWORD"):
        options["password"] = os.environ["DB_PASSWORD"]
    return psycopg.connect(**options)


def count_rows(cursor, table):
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    return cursor.fetchone()[0]


def load(clean):
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute((PROJECT_DIR / "sql/create_tables.sql").read_text())
            inserted = {}

            before = count_rows(cursor, "dim_customers")
            cursor.executemany(
                """INSERT INTO dim_customers (customer_id, customer_unique_id, city, state)
                   VALUES (%s, %s, %s, %s) ON CONFLICT (customer_id) DO NOTHING""",
                clean["customers"].itertuples(index=False, name=None),
            )
            inserted["dim_customers"] = count_rows(cursor, "dim_customers") - before

            before = count_rows(cursor, "dim_products")
            cursor.executemany(
                """INSERT INTO dim_products (product_id, category)
                   VALUES (%s, %s) ON CONFLICT (product_id) DO NOTHING""",
                clean["products"].itertuples(index=False, name=None),
            )
            inserted["dim_products"] = count_rows(cursor, "dim_products") - before

            before = count_rows(cursor, "dim_date")
            cursor.executemany(
                """INSERT INTO dim_date (date_key, full_date, year, month, day)
                   VALUES (%s, %s, %s, %s, %s) ON CONFLICT (date_key) DO NOTHING""",
                clean["dates"].itertuples(index=False, name=None),
            )
            inserted["dim_date"] = count_rows(cursor, "dim_date") - before

            cursor.execute("SELECT customer_id, customer_key FROM dim_customers")
            customer_keys = dict(cursor.fetchall())
            cursor.execute("SELECT product_id, product_key FROM dim_products")
            product_keys = dict(cursor.fetchall())
            order_details = clean["orders"].set_index("order_id")[["customer_id", "date_key"]].to_dict("index")

            order_rows = (
                (
                    row.order_id,
                    row.order_item_id,
                    customer_keys[order_details[row.order_id]["customer_id"]],
                    product_keys[row.product_id],
                    int(order_details[row.order_id]["date_key"]),
                    row.quantity,
                    round(row.unit_price, 2),
                    round(row.total_amount, 2),
                )
                for row in clean["items"].itertuples(index=False)
            )
            before = count_rows(cursor, "fact_orders")
            cursor.executemany(
                """INSERT INTO fact_orders
                   (order_id, order_item_id, customer_key, product_key, date_key, quantity, unit_price, total_amount)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (order_id, order_item_id) DO NOTHING""",
                order_rows,
            )
            inserted["fact_orders"] = count_rows(cursor, "fact_orders") - before

            payment_rows = (
                (
                    row.order_id,
                    row.payment_sequential,
                    customer_keys[order_details[row.order_id]["customer_id"]],
                    int(order_details[row.order_id]["date_key"]),
                    row.payment_type,
                    round(row.payment_amount, 2),
                )
                for row in clean["payments"].itertuples(index=False)
            )
            before = count_rows(cursor, "fact_payments")
            cursor.executemany(
                """INSERT INTO fact_payments
                   (order_id, payment_sequential, customer_key, date_key, payment_type, payment_amount)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (order_id, payment_sequential) DO NOTHING""",
                payment_rows,
            )
            inserted["fact_payments"] = count_rows(cursor, "fact_payments") - before

            cursor.execute((PROJECT_DIR / "sql/views.sql").read_text())
    return inserted
