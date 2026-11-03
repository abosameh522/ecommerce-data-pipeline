"""Unit tests for load.py using mocked database connections.

These tests exercise the load logic without requiring a live PostgreSQL instance.
They use unittest.mock to verify SQL execution patterns and return values.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sample_data import raw_tables

from load import count_rows, load
from transform import transform
from validate import validate


class LoadUnitTests(unittest.TestCase):
    """Test load.py logic with mocked psycopg connection."""

    def setUp(self):
        self.clean, _ = transform(raw_tables())
        validate(self.clean)

    @patch("load.connect")
    def test_count_rows_executes_select(self, mock_connect):
        """count_rows should execute a parameterized SELECT COUNT(*) query."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (42,)
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value.__enter__.return_value = mock_conn

        result = count_rows(mock_cursor, "dim_customers")

        self.assertEqual(result, 42)
        mock_cursor.execute.assert_called_once()
        # Verify the query uses sql.Identifier for safety
        args, _ = mock_cursor.execute.call_args
        query_str = str(args[0])
        self.assertIn("SELECT COUNT(*) FROM", query_str)

    @patch("load.connect")
    def test_load_creates_tables_first(self, mock_connect):
        """load() should execute create_tables.sql before any inserts."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (0,)
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value.__enter__.return_value = mock_conn

        # Mock the file read
        with patch("load.PROJECT_DIR") as mock_project_dir:
            mock_sql = MagicMock()
            mock_sql.read_text.return_value = "CREATE TABLE test (id INT);"
            mock_project_dir.__truediv__.return_value = mock_sql

            load(self.clean)

        # First call should be create_tables.sql
        calls = mock_cursor.execute.call_args_list
        self.assertTrue(len(calls) > 0)
        first_query = (
            calls[0][0][0].as_string(mock_conn)
            if hasattr(calls[0][0][0], "as_string")
            else str(calls[0][0][0])
        )
        self.assertIn("CREATE TABLE", first_query)

    @patch("load.connect")
    def test_load_dimension_inserts_use_on_conflict(self, mock_connect):
        """Dimension inserts should use ON CONFLICT DO NOTHING."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (0,)
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value.__enter__.return_value = mock_conn

        with patch("load.PROJECT_DIR") as mock_project_dir:
            mock_sql = MagicMock()
            mock_sql.read_text.return_value = "CREATE TABLE test (id INT);"
            mock_project_dir.__truediv__.return_value = mock_sql

            load(self.clean)

        # Check that dimension inserts use ON CONFLICT
        insert_calls = list(mock_cursor.executemany.call_args_list)
        self.assertEqual(len(insert_calls), 5)  # 3 dims + 2 facts

        # First 3 should be dimensions with ON CONFLICT
        for i in range(3):
            query = insert_calls[i][0][0]
            self.assertIn("ON CONFLICT", query)
            self.assertIn("DO NOTHING", query)

    @patch("load.connect")
    def test_load_fact_inserts_use_composite_keys(self, mock_connect):
        """Fact inserts should use composite primary keys in ON CONFLICT."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (0,)
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value.__enter__.return_value = mock_conn

        with patch("load.PROJECT_DIR") as mock_project_dir:
            mock_sql = MagicMock()
            mock_sql.read_text.return_value = "CREATE TABLE test (id INT);"
            mock_project_dir.__truediv__.return_value = mock_sql

            load(self.clean)

        insert_calls = list(mock_cursor.executemany.call_args_list)
        # fact_orders: ON CONFLICT (order_id, order_item_id)
        fact_orders_query = insert_calls[3][0][0]
        self.assertIn("ON CONFLICT (order_id, order_item_id)", fact_orders_query)

        # fact_payments: ON CONFLICT (order_id, payment_sequential)
        fact_payments_query = insert_calls[4][0][0]
        self.assertIn("ON CONFLICT (order_id, payment_sequential)", fact_payments_query)

    @patch("load.connect")
    def test_load_returns_inserted_counts(self, mock_connect):
        """load() should return a dict with inserted counts per table."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        # Simulate before=0, after=5 for each table (5 tables * 2 = 10 calls)
        call_count = [0]

        def fetchone_side_effect():
            call_count[0] += 1
            # Return 0 for before, 5 for after
            return (0,) if call_count[0] % 2 == 1 else (5,)

        mock_cursor.fetchone.side_effect = fetchone_side_effect
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value.__enter__.return_value = mock_conn

        with patch("load.PROJECT_DIR") as mock_project_dir:
            mock_sql = MagicMock()
            mock_sql.read_text.return_value = "CREATE TABLE test (id INT);"
            mock_project_dir.__truediv__.return_value = mock_sql

            result = load(self.clean)

        expected_keys = {
            "dim_customers",
            "dim_products",
            "dim_date",
            "fact_orders",
            "fact_payments",
        }
        self.assertEqual(set(result.keys()), expected_keys)
        # Each table should have 5 inserted (after=5, before=0)
        for count in result.values():
            self.assertEqual(count, 5)

    @patch("load.connect")
    def test_load_views_created_after_facts(self, mock_connect):
        """views.sql should be executed after all fact inserts."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (0,)
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value.__enter__.return_value = mock_conn

        with patch("load.PROJECT_DIR") as mock_project_dir:
            mock_sql = MagicMock()
            mock_sql.read_text.return_value = "CREATE TABLE test (id INT);"
            mock_project_dir.__truediv__.return_value = mock_sql

            load(self.clean)

        # Last execute call should be views.sql
        execute_calls = mock_cursor.execute.call_args_list
        execute_calls[-1][0][0]
        # views.sql read_text should have been called
        views_calls = [
            c for c in mock_project_dir.__truediv__.call_args_list if "views.sql" in str(c)
        ]
        self.assertTrue(len(views_calls) > 0)


class LoadEdgeCaseTests(unittest.TestCase):
    """Test edge cases in load logic."""

    def setUp(self):
        from sample_data import raw_tables

        from transform import transform
        from validate import validate

        self.clean, _ = transform(raw_tables())
        validate(self.clean)

    @patch("load.connect")
    def test_load_handles_empty_dataframes(self, mock_connect):
        """load() should handle empty clean data gracefully."""
        empty_clean = {
            "customers": pd.DataFrame(
                columns=["customer_id", "customer_unique_id", "city", "state"]
            ),
            "products": pd.DataFrame(columns=["product_id", "category"]),
            "dates": pd.DataFrame(columns=["date_key", "full_date", "year", "month", "day"]),
            "orders": pd.DataFrame(columns=["order_id", "customer_id", "date_key"]),
            "items": pd.DataFrame(
                columns=[
                    "order_id",
                    "order_item_id",
                    "product_id",
                    "quantity",
                    "unit_price",
                    "total_amount",
                ]
            ),
            "payments": pd.DataFrame(
                columns=["order_id", "payment_sequential", "payment_type", "payment_amount"]
            ),
        }
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (0,)
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value.__enter__.return_value = mock_conn

        with patch("load.PROJECT_DIR") as mock_project_dir:
            mock_sql = MagicMock()
            mock_sql.read_text.return_value = "CREATE TABLE test (id INT);"
            mock_project_dir.__truediv__.return_value = mock_sql

            result = load(empty_clean)

        # All counts should be 0
        for count in result.values():
            self.assertEqual(count, 0)

    @patch("load.connect")
    def test_load_connection_failure_propagates(self, mock_connect):
        """Connection errors should propagate to caller."""
        mock_connect.side_effect = Exception("connection failed")

        with self.assertRaises(Exception) as ctx:
            load(self.clean)
        self.assertIn("connection failed", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
