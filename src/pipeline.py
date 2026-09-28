import logging
from pathlib import Path

from extract import extract
from load import load
from transform import transform
from validate import validate


PROJECT_DIR = Path(__file__).resolve().parents[1]


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
        logging.info("Validation started")
        validate(clean)
        logging.info("Validation passed")
        inserted = load(clean)
        for name, counts in report.items():
            cleaned = len(clean[name]) if name in clean else counts["input"] - counts["duplicates"]
            logging.info(
                "%s: input=%s duplicates=%s rejected=%s excluded=%s cleaned=%s",
                name, counts["input"], counts["duplicates"], counts["rejected"], counts["excluded"], cleaned,
            )
        for table, count in inserted.items():
            source = {"dim_customers": "customers", "dim_products": "products", "dim_date": "dates", "fact_orders": "items", "fact_payments": "payments"}[table]
            logging.info("%s: inserted=%s skipped_existing=%s", table, count, len(clean[source]) - count)
        logging.info("Pipeline completed")
    except Exception:
        logging.exception("Pipeline failed")
        raise


if __name__ == "__main__":
    main()
