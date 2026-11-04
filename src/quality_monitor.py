"""Data quality monitoring that logs validation results to quality_checks table."""

import json
import logging


class QualityMonitor:
    """Records data quality check results to the database for trend analysis."""

    def __init__(self, connection):
        self.connection = connection
        self.checks = []

    def log_check(
        self,
        check_name: str,
        check_status: str,
        records_checked: int,
        records_failed: int = 0,
        error_message: str | None = None,
        metadata: dict | None = None,
    ):
        """Record a single quality check result.

        Args:
            check_name: Descriptive name of the check (e.g. 'customers_unique_id')
            check_status: 'pass', 'fail', or 'warn'
            records_checked: Total number of records evaluated
            records_failed: Number of records that failed the check
            error_message: Optional error details for failed checks
            metadata: Optional JSON-serializable dict with check context
        """
        check = {
            "check_name": check_name,
            "check_status": check_status,
            "records_checked": records_checked,
            "records_failed": records_failed,
            "error_message": error_message,
            "check_metadata": json.dumps(metadata) if metadata else None,
        }
        self.checks.append(check)
        logging.debug(
            "Quality check: %s | status=%s checked=%d failed=%d",
            check_name,
            check_status,
            records_checked,
            records_failed,
        )

    def flush(self):
        """Write all accumulated checks to the database."""
        if not self.checks:
            return

        with self.connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO quality_checks
                (check_name, check_status, records_checked, records_failed, error_message, check_metadata)
                VALUES (%(check_name)s, %(check_status)s, %(records_checked)s,
                        %(records_failed)s, %(error_message)s, %(check_metadata)s::jsonb)
                """,
                self.checks,
            )
        logging.info("Logged %d quality checks to database", len(self.checks))
        self.checks.clear()


def log_quality_checks_to_db(clean, connection):
    """Log successful validation checks to quality_checks table.

    This is called AFTER validation passes, purely for database trend analysis.
    It re-runs all validation logic in try/except blocks to log individual check results.

    Args:
        clean: Dict of cleaned dataframes that already passed validate()
        connection: Database connection with quality_checks table

    Note:
        All checks here should pass since validate() already succeeded.
        Any failures logged here indicate a bug in this monitoring function.
    """
    from validate import (
        require_amount,
        require_positive_integer,
        require_references,
        require_unique,
    )

    monitor = QualityMonitor(connection)

    customers = clean["customers"]
    products = clean["products"]
    orders = clean["orders"]
    items = clean["items"]
    payments = clean["payments"]
    dates = clean["dates"]

    # Uniqueness checks
    for frame, columns, name in [
        (customers, ["customer_id"], "customers_unique_id"),
        (products, ["product_id"], "products_unique_id"),
        (orders, ["order_id"], "orders_unique_id"),
        (items, ["order_id", "order_item_id"], "items_unique_composite"),
        (payments, ["order_id", "payment_sequential"], "payments_unique_composite"),
        (dates, ["date_key"], "dates_unique_key"),
    ]:
        total = len(frame)
        try:
            require_unique(frame, columns, name)
            monitor.log_check(name, "pass", total, 0)
        except ValueError as e:
            monitor.log_check(name, "fail", total, 0, str(e))

    # Reference integrity checks
    for frame, column, parent, parent_column, name in [
        (orders, "customer_id", customers, "customer_id", "orders_customer_fk"),
        (items, "order_id", orders, "order_id", "items_order_fk"),
        (items, "product_id", products, "product_id", "items_product_fk"),
        (payments, "order_id", orders, "order_id", "payments_order_fk"),
        (orders, "date_key", dates, "date_key", "orders_date_fk"),
    ]:
        total = len(frame)
        try:
            require_references(frame, column, parent, parent_column, name)
            monitor.log_check(name, "pass", total, 0)
        except ValueError as e:
            missing = int((~frame[column].isin(parent[parent_column])).sum())
            monitor.log_check(name, "fail", total, missing, str(e))

    # Amount range checks
    for series, upper, name in [
        (items["unit_price"], 10**10, "items_unit_price_range"),
        (items["total_amount"], 10**12, "items_total_amount_range"),
        (payments["payment_amount"], 10**12, "payments_amount_range"),
    ]:
        total = len(series)
        try:
            require_amount(series, upper, name)
            monitor.log_check(name, "pass", total, 0)
        except ValueError as e:
            monitor.log_check(name, "fail", total, 0, str(e))

    # Integer checks
    for series, name in [
        (items["order_item_id"], "items_order_item_id_integer"),
        (items["quantity"], "items_quantity_integer"),
        (payments["payment_sequential"], "payments_sequential_integer"),
    ]:
        total = len(series)
        try:
            require_positive_integer(series, name)
            monitor.log_check(name, "pass", total, 0)
        except ValueError as e:
            monitor.log_check(name, "fail", total, 0, str(e))

    # Arithmetic check: total_amount == quantity * unit_price
    total = len(items)
    calculated = (items["quantity"] * items["unit_price"]).round(2)
    actual = items["total_amount"].round(2)
    mismatches = ~actual.eq(calculated)
    if mismatches.any():
        monitor.log_check(
            "items_amount_arithmetic",
            "fail",
            total,
            int(mismatches.sum()),
            "total_amount does not match quantity * unit_price",
        )
    else:
        monitor.log_check("items_amount_arithmetic", "pass", total, 0)

    # Date check
    total = len(orders)
    invalid_dates = orders["purchase_date"].isna()
    if invalid_dates.any():
        monitor.log_check(
            "orders_purchase_date_valid",
            "fail",
            total,
            int(invalid_dates.sum()),
            "invalid purchase_date",
        )
    else:
        monitor.log_check("orders_purchase_date_valid", "pass", total, 0)

    monitor.flush()
