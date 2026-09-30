import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from extract import FILES, extract
from transform import transform
from validate import validate
from sample_data import raw_tables, source_id


class ExtractionTests(unittest.TestCase):
    def test_missing_files_list(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(FileNotFoundError, "olist_customers_dataset.csv"):
                extract(Path(directory))

    def test_csv_round_trip_preserves_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            for name, frame in raw_tables().items():
                frame.to_csv(Path(directory) / FILES[name], index=False, encoding="utf-8-sig")
            raw = extract(Path(directory))
            self.assertEqual(raw["customers"].iloc[0]["customer_id"], source_id(1))
            self.assertTrue(validate(transform(raw)[0]))

    def test_missing_column_names_source_file(self):
        raw = raw_tables()
        raw["customers"] = raw["customers"].drop(columns="customer_state")
        with tempfile.TemporaryDirectory() as directory:
            for name, frame in raw.items():
                frame.to_csv(Path(directory) / FILES[name], index=False)
            with self.assertRaisesRegex(ValueError, "olist_customers_dataset.csv: missing columns: customer_state"):
                extract(Path(directory))


class TransformationTests(unittest.TestCase):
    def test_grains_normalization_and_counts(self):
        raw = raw_tables()
        before = {name: frame.copy(deep=True) for name, frame in raw.items()}
        clean, report = transform(raw)
        self.assertTrue(validate(clean))
        self.assertEqual(len(clean["items"]), 2)
        self.assertEqual(len(clean["payments"]), 2)
        self.assertEqual(clean["items"]["total_amount"].sum(), 30.5)
        self.assertEqual(clean["customers"].iloc[0]["city"], "Sao Paulo")
        self.assertEqual(clean["customers"].iloc[0]["state"], "SP")
        self.assertEqual(clean["products"].iloc[0]["category"], "books")
        self.assertEqual(clean["payments"].iloc[0]["payment_type"], "credit_card")
        self.assertEqual(clean["dates"].iloc[0]["date_key"], 20180102)
        for name, counts in report.items():
            self.assertEqual(counts["input"], sum(counts[key] for key in ("duplicates", "rejected", "excluded", "cleaned")))
            pd.testing.assert_frame_equal(raw[name], before[name])
        for name in ("orders", "items", "payments"):
            self.assertEqual(report[name]["excluded"], 1)

    def test_exact_duplicates_removed_but_conflicting_keys_fail(self):
        raw = raw_tables()
        raw["items"] = pd.concat([raw["items"], raw["items"].iloc[[0]]], ignore_index=True)
        clean, report = transform(raw)
        self.assertTrue(validate(clean))
        self.assertEqual(report["items"]["duplicates"], 1)
        raw["items"].loc[3, "price"] = "11.50"
        with self.assertRaisesRegex(ValueError, "items: duplicate primary key"):
            validate(transform(raw)[0])

    def test_invalid_delivered_parent_rejects_children(self):
        raw = raw_tables()
        raw["orders"].loc[0, "order_purchase_timestamp"] = "not a date"
        clean, report = transform(raw)
        self.assertTrue(validate(clean))
        for name, rejected in (("orders", 1), ("items", 2), ("payments", 2)):
            self.assertEqual(report[name]["rejected"], rejected)
            self.assertEqual(report[name]["excluded"], 1)

    def test_unknown_source_reference_rejected(self):
        for name, column in (("orders", "customer_id"), ("items", "product_id"), ("payments", "order_id")):
            with self.subTest(name=name):
                raw = raw_tables()
                raw[name].loc[0, column] = source_id(999)
                clean, report = transform(raw)
                self.assertTrue(validate(clean))
                self.assertEqual(report[name]["rejected"], 1)

    def test_invalid_money_rejected(self):
        for name, column in (("items", "price"), ("payments", "payment_value")):
            for value in ("inf", "-inf", "NaN", "-1", "-0.001", "not money", "1000000000000"):
                with self.subTest(name=name, value=value):
                    raw = raw_tables()
                    raw[name].loc[0, column] = value
                    clean, report = transform(raw)
                    self.assertTrue(validate(clean))
                    self.assertEqual(report[name]["rejected"], 1)

    def test_invalid_sequence_rejected(self):
        for name, column in (("items", "order_item_id"), ("payments", "payment_sequential")):
            for value in ("0", "-1", "1.5", "inf", str(2**31)):
                with self.subTest(name=name, value=value):
                    raw = raw_tables()
                    raw[name].loc[0, column] = value
                    clean, report = transform(raw)
                    self.assertTrue(validate(clean))
                    self.assertEqual(report[name]["rejected"], 1)

    def test_missing_city_and_translation_fallback(self):
        raw = raw_tables()
        raw["customers"].loc[0, "customer_city"] = "  "
        raw["categories"].loc[0, "product_category_name_english"] = " "
        clean, report = transform(raw)
        self.assertEqual(clean["customers"].iloc[0]["city"], "Unknown")
        self.assertEqual(clean["products"].iloc[0]["category"], "Unknown")
        self.assertEqual(report["categories"]["rejected"], 1)
        self.assertEqual(report["categories"]["cleaned"], 0)

    def test_conflicting_translation_fails_clearly(self):
        raw = raw_tables()
        raw["categories"].loc[1] = ["livros", "different translation"]
        with self.assertRaisesRegex(ValueError, "categories: duplicate primary key"):
            transform(raw)

    def test_no_delivered_orders_is_valid_empty_batch(self):
        raw = raw_tables()
        raw["orders"]["order_status"] = "canceled"
        clean, _ = transform(raw)
        self.assertTrue(validate(clean))
        for name in ("orders", "items", "payments", "dates"):
            self.assertTrue(clean[name].empty)


class ValidationTests(unittest.TestCase):
    def test_nonfinite_and_out_of_range_amounts_fail(self):
        for name, column in (("items", "unit_price"), ("items", "total_amount"), ("payments", "payment_amount")):
            for value in (float("inf"), float("nan"), -1, 10**12):
                with self.subTest(name=name, column=column, value=value):
                    clean, _ = transform(raw_tables())
                    clean[name].loc[0, column] = value
                    with self.assertRaises(ValueError):
                        validate(clean)

    def test_inconsistent_item_total_fails(self):
        clean, _ = transform(raw_tables())
        clean["items"].loc[0, "total_amount"] = 99.0
        with self.assertRaisesRegex(ValueError, "total_amount does not match"):
            validate(clean)

    def test_missing_parent_fails(self):
        clean, _ = transform(raw_tables())
        clean["items"].loc[0, "product_id"] = source_id(999)
        with self.assertRaisesRegex(ValueError, "missing product_id references"):
            validate(clean)

    def test_null_key_fails(self):
        clean, _ = transform(raw_tables())
        clean["customers"].loc[0, "customer_id"] = None
        with self.assertRaisesRegex(ValueError, "null primary key"):
            validate(clean)
