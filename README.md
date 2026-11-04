# E-commerce Data Pipeline

A batch ETL pipeline that extracts Olist Brazilian e-commerce CSVs, validates and transforms them, and loads a PostgreSQL star schema with idempotent inserts, analytical views, and verified SQL queries — built to demonstrate core Data Engineering skills for junior roles.

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![PostgreSQL](https://img.shields.io/badge/postgresql-16%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-28%20passed-brightgreen)
![Lint](https://img.shields.io/badge/lint-ruff-success)

## Why This Exists

Most portfolio projects stop at a Jupyter notebook. Hiring managers for Junior Data Engineer and Analytics Engineer roles want to see: reproducible pipelines, idempotent warehouse loads, data quality gates, dimensional modeling, and SQL that answers business questions. This project delivers all of that in a single, runnable codebase — no cloud account required.

## What It Does

- **Extracts** 6 Olist CSV files with required-column contracts
- **Transforms** with per-source quality counts (duplicates, rejected, excluded, cleaned)
- **Validates** keys, references, ranges, and item-total arithmetic before any DB write
- **Loads** a star schema (`dim_customers`, `dim_products`, `dim_date`, `fact_orders`, `fact_payments`) in one transaction using `INSERT ... ON CONFLICT DO NOTHING` for idempotency
- **Logs quality checks** to database table for validation trend analysis (optional, doesn't block pipeline)
- **Exposes** 3 analytical views + 15 SQL queries (9 basic aggregations + 6 intermediate queries with window functions, CTEs, self-joins)
- **Generates** portfolio diagrams from the loaded warehouse

```mermaid
flowchart LR
    A[Raw CSVs\nOlist dataset] --> B[Extract\nsrc/extract.py]
    B --> C[Transform\nsrc/transform.py]
    C --> D[Validate\nsrc/validate.py]
    D --> E[Load\nsrc/load.py]
    E --> F[(PostgreSQL\nStar Schema)]
    F --> G[Views + Queries\nsql/]
    F --> H[Portfolio Images\nmake_images.py]
```

## Data

| Source | Files | License | Grain |
|--------|-------|---------|-------|
| Olist Brazilian E-Commerce (Kaggle) | 6 CSVs | CC BY-NC-SA 4.0 | Order item / payment |

**Key quality rules** (enforced in `src/validate.py`):
- Business keys are 32-char hex; duplicates → rejected
- `total_amount == quantity * unit_price` per item
- Facts reference existing dimension keys (FK integrity)
- Non-delivered orders + children → excluded (not rejected)
- Every source logs: `input = duplicates + rejected + excluded + cleaned`

## Stack

| Layer | Technology | Why |
|-------|------------|-----|
| Language | Python 3.11+ | Standard for DE/ML, rich data ecosystem |
| Dataframes | pandas | In-memory transforms, CSV handling |
| Database | PostgreSQL 16+ via psycopg 3 | Production-grade, native `ON CONFLICT`, arrays, JSON |
| Quality Monitoring | Custom quality_checks table | Tracks validation trends over time, no external dependencies |
| Orchestration | None (manual batch) | Keeps focus on pipeline mechanics; Airflow/Dagster noted in roadmap |
| Testing | unittest + pytest | Zero extra deps for core tests; pytest for CI |
| Lint/Format | Ruff | Fast, replaces flake8+isort+black |
| Pre-commit | ruff + standard hooks | Enforces style before commit |
| Diagrams | matplotlib (Agg backend) | Generates portfolio images from live DB |

## Project Tree

```text
ecommerce-data-pipeline/
├── src/
│   ├── extract.py            # CSV loading & column contracts
│   ├── transform.py          # Cleaning, normalization, quality counts
│   ├── validate.py           # Key/ref/range checks + reconciliation
│   ├── quality_monitor.py    # Optional quality checks logger (writes to quality_checks table)
│   ├── load.py               # Transactional idempotent inserts
│   ├── pipeline.py           # Entrypoint, logging, .env loading
│   └── make_images.py        # DB-backed portfolio charts
├── sql/
│   ├── create_tables.sql     # Tables (dims, facts, quality_checks), PK/FK, indexes, checks
│   ├── views.sql             # monthly_sales_summary, customer_order_summary, product_sales_summary
│   ├── analytics_queries.sql # 9 basic business queries
│   └── intermediate_analytics.sql # 6 intermediate SQL queries (window functions, CTEs, self-joins)
├── tests/
│   ├── sample_data.py        # Synthetic rows for unit tests
│   ├── test_pipeline.py      # Extract/transform/validate (20 tests)
│   ├── test_load_unit.py     # Load module unit tests (8 tests)
│   └── test_load.py          # PG integration (4 tests, needs TEST_DATABASE_URL)
├── docs/
│   └── run_results.md        # Verified full-run numbers and SQL outputs
├── data/raw/                 # Downloaded CSVs (gitignored)
├── images/                   # Architecture diagram
├── portfolio/                # Pipeline overview, data model, SQL analytics
├── logs/                     # Run logs (gitignored)
├── .env.example              # DB_* template
├── requirements.txt
├── pyproject.toml            # Ruff, pytest, coverage config
├── .pre-commit-config.yaml
├── LICENSE
└── README.md
```

## Run

**Prereqs:** Python 3.11+, PostgreSQL 16+ (local or Docker), `createdb`/`psql` in PATH.

```bash
# 1. Clone & venv
git clone https://github.com/abosameh522/ecommerce-data-pipeline.git
cd ecommerce-data-pipeline
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download dataset (requires Kaggle API)
mkdir -p data/raw
kaggle datasets download -d olistbr/brazilian-ecommerce -p data/raw --unzip

# 4. Configure database
cp .env.example .env
# Edit .env with your PostgreSQL connection: DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
export DB_NAME="ecommerce_dw"
createdb "$DB_NAME"

# 5. Run pipeline
python src/pipeline.py

# 6. Query (basic analytics)
psql -X -v ON_ERROR_STOP=1 -d "$DB_NAME" -f sql/analytics_queries.sql

# 7. Query (intermediate SQL - window functions, CTEs, self-joins)
psql -X -v ON_ERROR_STOP=1 -d "$DB_NAME" -f sql/intermediate_analytics.sql

# 8. Idempotency check (should insert 0 rows)
python src/pipeline.py

# 9. Inspect quality check logs (if database was available during validation)
psql -d "$DB_NAME" -c "SELECT check_name, check_status, records_checked, records_failed FROM quality_checks ORDER BY run_timestamp DESC LIMIT 10;"

# 10. Regenerate portfolio images
python src/make_images.py
```

## Test

```bash
# Unit tests (no database required)
python -m unittest discover -s tests -v

# Integration tests (requires TEST_DATABASE_URL)
export TEST_DATABASE_URL="postgresql://user:pass@localhost/test_db"
createdb test_db
python -m unittest discover -s tests -p "test_load.py" -v

# Linting
python -m ruff check src tests

# Pre-commit hooks
pre-commit install
pre-commit run --all-files
```

## What You Learn

- **Idempotent warehouse loads** are non-negotiable: `ON CONFLICT DO NOTHING` on natural keys + surrogate PKs makes reruns safe and auditable.
- **Validation before load** catches garbage early and keeps DB errors out of the critical path — distinguish *rejected* (bad data) from *excluded* (out of scope).
- **Quality monitoring as data** turns validation from pass/fail to a time-series that reveals data drift, source degradation, and anomaly trends.
- **Intermediate SQL** (window functions, CTEs, self-joins) differentiates junior-level data engineering from basic analytics: customer segmentation, cohort analysis, time-series comparisons, and graph-like queries.
- **Separate fact grains** prevent double-counting: items and payments at different grains must be aggregated to order grain before joining on money.
- **Reconciled counts** (`input = dup + rej + exc + clean`) survive partial failures and make data quality visible.
- **Integer date keys** (`YYYYMMDD`) simplify partitioning and range scans vs. `DATE` foreign keys.

## Limitations

- **Insert-only**: no upsert for corrected source rows; repeat load skips known keys.
- **Full-load only**: no incremental extraction; every run processes all CSVs.
- **Sparse date dimension**: only observed dates exist, so monthly trends have gaps.
- **No orchestration**: manual run; Airflow/Dagster DAGs are roadmap items.
- **Single-writer insert counts**: before/after table counts assume no concurrent loads.
- **In-memory pandas**: not suited for >100M rows without chunking or Polars/DuckDB.
- **Quality monitoring requires database**: if database is unavailable during validation, quality checks are not logged (but validation still works).

## Roadmap

- [ ] Incremental extract via `max(date_key)` watermark + `updated_at` on source
- [ ] Upsert path with `updated_at` so corrected rows propagate
- [ ] Rejected-rows report (CSV/Parquet) with per-record reason codes
- [ ] Continuous date dimension for gap-free trend reporting
- [ ] Airflow DAG with task dependencies, retries, and data freshness sensors
- [ ] dbt models to replace raw SQL views (snapshots, tests, documentation)
- [ ] duckdb/Polars path for 100M+ row datasets

## Why This Structure

This isn't production code — it's a **teaching artifact** for portfolio and interviews. The goal is to show:

1. **Engineering basics**: error handling, logging, transactions, idempotency
2. **Data thinking**: grain, cardinality, reconciliation, exclusion vs rejection
3. **SQL fluency**: star schemas, window functions, CTEs, analytical queries
4. **Process clarity**: each stage is a pure function with clear inputs/outputs
5. **Testability**: unit tests for logic, integration tests for database behavior

Junior DE roles don't expect distributed systems or real-time streaming. They expect **working batch pipelines** that handle bad data gracefully and produce correct star schemas. This project delivers exactly that.

## License

MIT — free to use, modify, and share. Dataset is CC BY-NC-SA 4.0 (Olist/Kaggle).

## Feedback

Issues and suggestions welcome. This is a living portfolio project — if you see a better pattern or missed edge case, please open an issue.
