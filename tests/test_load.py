import os
import sys
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import psycopg
from psycopg import sql

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from load import load
from transform import transform
from validate import validate
from sample_data import raw_tables, source_id


@unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "Set TEST_DATABASE_URL to a disposable PostgreSQL database")
class LoadTests(unittest.TestCase):
    def setUp(self):
        self.schema = "test_" + uuid4().hex
        self.admin = psycopg.connect(os.environ["TEST_DATABASE_URL"], autocommit=True)
        self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        self.addCleanup(self.cleanup_schema)
        self.admin.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(self.schema)))
        self.connection_patch = patch("load.connect", self.connect)
        self.connection_patch.start()
        self.addCleanup(self.connection_patch.stop)
        self.clean, _ = transform(raw_tables())
        validate(self.clean)

    def connect(self):
        return psycopg.connect(os.environ["TEST_DATABASE_URL"], options=f"-c search_path={self.schema}")

    def cleanup_schema(self):
        self.admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))
        self.admin.close()

    def test_load_repeat_and_fact_grains(self):
        inserted = load(self.clean)
        self.assertEqual(inserted, {"dim_customers": 1, "dim_products": 1, "dim_date": 1, "fact_orders": 2, "fact_payments": 2})
        self.assertTrue(all(count == 0 for count in load(self.clean).values()))
        self.assertEqual(self.admin.execute("SELECT orders, item_revenue FROM monthly_sales_summary").fetchone(), (1, Decimal("30.50")))
        self.assertEqual(self.admin.execute("SELECT SUM(payment_amount) FROM fact_payments").fetchone()[0], Decimal("30.50"))
        self.assertEqual(self.admin.execute("SELECT orders, item_revenue FROM customer_order_summary").fetchone(), (1, Decimal("30.50")))
        self.assertEqual(self.admin.execute("SELECT units_sold, item_revenue FROM product_sales_summary").fetchone(), (2, Decimal("30.50")))
        queries = Path(__file__).resolve().parents[1] / "sql/analytics_queries.sql"
        with self.admin.cursor() as cursor:
            cursor.execute(queries.read_text())
            while cursor.nextset():
                pass

    def test_new_keys_insert_and_existing_values_stay(self):
        load(self.clean)
        raw = raw_tables()
        raw["customers"].loc[0, "customer_city"] = "changed city"
        raw["orders"].loc[0, "order_id"] = source_id(6)
        raw["items"].loc[:1, "order_id"] = source_id(6)
        raw["payments"].loc[:1, "order_id"] = source_id(6)
        clean, _ = transform(raw)
        inserted = load(clean)
        self.assertEqual(inserted["fact_orders"], 2)
        self.assertEqual(inserted["fact_payments"], 2)
        self.assertEqual(inserted["dim_customers"], 0)
        self.assertEqual(self.admin.execute("SELECT city FROM dim_customers").fetchone()[0], "Sao Paulo")

    def test_failed_payment_rolls_back_whole_load(self):
        # Fail after dimensions and order items have been inserted.
        self.clean["payments"].loc[0, "payment_amount"] = -1.0
        with self.assertRaises(psycopg.errors.CheckViolation):
            load(self.clean)
        self.assertIsNone(self.admin.execute("SELECT to_regclass('fact_orders')").fetchone()[0])
        self.assertEqual(load(transform(raw_tables())[0])["fact_orders"], 2)

    def test_empty_facts_load(self):
        raw = raw_tables()
        raw["orders"]["order_status"] = "canceled"
        clean, _ = transform(raw)
        inserted = load(clean)
        self.assertEqual(inserted["fact_orders"], 0)
        self.assertEqual(inserted["fact_payments"], 0)
        self.assertEqual(inserted["dim_date"], 0)
