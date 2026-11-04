import logging
from pathlib import Path

from dotenv import load_dotenv

from extract import extract
from load import connect, load
from transform import transform
from validate import validate

PROJECT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_DIR / ".env", override=False)


def main():
    (PROJECT_DIR / "logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(PROJECT_DIR / "logs/pipeline.log"),
            logging.StreamHandler(),
        ],
    )
    logging.info("Pipeline started")
    try:
        raw = extract(PROJECT_DIR / "data/raw")
        clean, report = transform(raw)
        for name, counts in report.items():
            logging.info(
                "%s: input=%s duplicates=%s rejected=%s excluded=%s cleaned=%s",
                name,
                counts["input"],
                counts["duplicates"],
                counts["rejected"],
                counts["excluded"],
                counts["cleaned"],
            )
        logging.info("Validation started")
        validate(clean)
        logging.info("Validation passed")

        inserted = load(clean)
        for table, count in inserted.items():
            source = {
                "dim_customers": "customers",
                "dim_products": "products",
                "dim_date": "dates",
                "fact_orders": "items",
                "fact_payments": "payments",
            }[table]
            logging.info(
                "%s: inserted=%s skipped_existing=%s",
                table,
                count,
                len(clean[source]) - count,
            )

        # Optional: Log quality checks to database for trend analysis.
        # Runs after load() has created the schema, and after validation passed.
        try:
            from quality_monitor import log_quality_checks_to_db

            with connect() as connection:
                log_quality_checks_to_db(clean, connection)
                connection.commit()
                logging.info("Quality checks logged to database")
        except Exception as e:
            # Quality monitoring is optional; don't fail the pipeline if DB logging fails
            logging.warning("Could not log quality checks to database: %s", e)

        logging.info("Pipeline completed")
    except Exception:
        logging.exception("Pipeline failed")
        raise


if __name__ == "__main__":
    main()
