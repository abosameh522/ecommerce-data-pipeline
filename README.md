# E-Commerce Data Pipeline & Warehouse

A Python ETL pipeline that cleans Olist e-commerce CSV files and loads a PostgreSQL warehouse for sales analysis. It keeps order items and payments in separate fact tables so multi-item orders do not inflate payment totals.

The full-data run loaded **110,197 order items** and **100,756 payment records** for delivered orders. SQL queries calculate item revenue, average order value, monthly sales, category sales, and repeat customers.

## Data flow

![Pipeline architecture](images/architecture.png)

1. **Extract:** check that the six source files and required columns exist, then read identifiers as strings.
2. **Transform:** remove exact duplicates, normalize text, parse dates and numbers, translate categories, and retain delivered orders.
3. **Validate:** check business-key uniqueness, parent references, integer ranges, finite amounts, and item-total consistency.
4. **Load:** insert dimensions and facts in one PostgreSQL transaction, then create the analytical views. A failed load rolls back the transaction.

The implementation uses Python, pandas, psycopg, and PostgreSQL. Matplotlib generates the diagrams and sales chart; it is not part of the ETL path.

## Source data

[Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), licensed [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). It contains anonymized orders from 2016–2018. Raw data are downloaded separately and ignored by Git.

| CSV | Source rows | Fields used |
| --- | ---: | --- |
| `olist_customers_dataset.csv` | 99,441 | Customer ID, unique customer ID, city, state |
| `olist_products_dataset.csv` | 32,951 | Product ID, category name |
| `olist_orders_dataset.csv` | 99,441 | Order ID, customer ID, status, purchase timestamp |
| `olist_order_items_dataset.csv` | 112,650 | Order ID, item sequence, product ID, price |
| `olist_order_payments_dataset.csv` | 103,886 | Order ID, payment sequence, type, value |
| `product_category_name_translation.csv` | 71 | Portuguese and English category names |

Only these six files are used. Reviews, sellers, and geolocation are outside the scope of this warehouse. The counts above were checked against the downloaded source; [run results](docs/run_results.md) record the verification details.

## Warehouse model

| Table | Grain | Key |
| --- | --- | --- |
| `dim_customers` | One source customer ID | Surrogate `customer_key`; unique `customer_id` |
| `dim_products` | One product ID | Surrogate `product_key`; unique `product_id` |
| `dim_date` | One purchase date present in delivered orders | `date_key` in YYYYMMDD form |
| `fact_orders` | One order item | `(order_id, order_item_id)` |
| `fact_payments` | One payment record | `(order_id, payment_sequential)` |

![Warehouse model](portfolio/data_model.png)

`fact_orders` references all three dimensions. `fact_payments` references customer and date. The customer dimension retains `customer_unique_id` to identify repeat customers across different source customer IDs.

An item row represents one unit, so `quantity = 1` and its amount equals its price. Revenue is the sum of item amounts in **BRL**, excluding freight. Payments are a separate measure and can include freight. Do not join the two facts directly on `order_id` to sum money: aggregate each to order grain first.

## Cleaning and load behavior

- Non-delivered orders and their otherwise valid items/payments are **excluded** by the business rule.
- Invalid IDs, dates, numeric values, and missing parent references are **rejected**. Children of a rejected delivered order are also rejected.
- Missing or blank cities and missing category translations become `Unknown`. Incomplete translation rows are rejected; conflicting translation keys stop the run.
- Exact source-row duplicates are removed. Remaining duplicate business keys stop validation rather than silently choosing one value.
- Each source report reconciles as `input = duplicates + rejected + excluded + cleaned`. Counts are logged before database loading, so they remain available if the connection or load fails.

Repeated runs use `ON CONFLICT DO NOTHING`: existing keys are skipped and new keys are inserted. This is **insert-only loading**, not change detection. Every run rereads the CSVs; changed prices, corrected customer details, deleted records, or changed order statuses do not update existing warehouse rows. Run one loader at a time; inserted counts are based on before/after table counts.

## Run locally

You need Python and a running PostgreSQL server, including the `createdb` and `psql` clients. The complete workflow was tested on Linux with Python 3.14.7 and PostgreSQL 18.6. Use a dedicated database and a login role allowed to create tables and views.

### 1. Install dependencies

```bash
git clone https://github.com/abosameh522/ecommerce-data-pipeline.git
cd ecommerce-data-pipeline
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 2. Download the CSVs

Download the dataset from its Kaggle page, or use the public archive endpoint:

```bash
curl --fail --location --retry 2 \
  https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce \
  --output olist.zip
unzip -j olist.zip -d data/raw
```

The archive also includes three unused CSVs. They can remain in `data/raw/`; extraction only reads the six files listed above. If the endpoint requires a login or returns a non-ZIP response, download through Kaggle and extract the CSVs manually.

### 3. Configure the database

The pipeline reads `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and optional `DB_PASSWORD` from the environment. It does **not** load `.env` automatically.

```bash
cp .env.example .env
# Edit .env with your PostgreSQL connection settings before continuing.
set -a
source .env
set +a

# PostgreSQL CLI tools use PG* variables, not the pipeline's DB* variables.
export PGHOST="$DB_HOST" PGPORT="$DB_PORT" PGUSER="$DB_USER"
export PGPASSWORD="${DB_PASSWORD:-}"
createdb "$DB_NAME"
```

`createdb` is a one-time step. If the database already exists, skip it. If your role cannot create databases, ask the local database administrator to create one owned by your role. Leave `DB_PASSWORD` empty only when your configured authentication allows it. `.env` is ignored by Git; quote values that contain shell-special characters.

### 4. Execute the pipeline and SQL

```bash
python src/pipeline.py
psql -X -v ON_ERROR_STOP=1 -d "$DB_NAME" -f sql/analytics_queries.sql
python src/pipeline.py
```

Tables and views are created automatically. The second run should log zero inserted rows for all five tables. Logs go to `logs/pipeline.log`. Python resolves data and SQL paths relative to the project, so it can also be invoked by absolute script path from another directory.

Generate the existing project visuals after loading:

```bash
python src/make_images.py
```

This overwrites the four PNGs in `images/` and `portfolio/` using the connected database. It requires at least one loaded order item.

## Results and SQL analysis

| Measure | Full-data result |
| --- | ---: |
| Delivered orders with loaded items | 96,478 |
| Order items | 110,197 |
| Payment records | 100,756 |
| Item revenue, excluding freight | BRL 13,221,498.11 |
| Average item value per order, excluding freight | BRL 137.04 |

![Sales analysis from PostgreSQL](portfolio/sql_analytics.png)

`sql/analytics_queries.sql` contains nine queries. The three views in `sql/views.sql` summarize monthly sales, customer orders, and product sales. Customer rankings and repeat-customer counts use the unique customer identifier rather than counting each order-specific customer ID as a different person.

In this extract, health and beauty has the highest delivered-item revenue at BRL 1,233,131.72. The monthly chart represents this historical sample, not the full market; missing months are not filled with zeros, and partial months should not be interpreted as complete trading periods.

## Tests

The tests use synthetic source rows, so the Kaggle download is not needed:

```bash
python -m unittest discover -s tests -v
```

This runs 16 extraction, transformation, and validation tests. Four PostgreSQL integration tests are skipped unless `TEST_DATABASE_URL` is set. To include them, use the connection settings exported above and a separate test database:

```bash
createdb ecommerce_pipeline_test
TEST_DATABASE_URL='dbname=ecommerce_pipeline_test' \
  python -m unittest discover -s tests -v
```

Each integration test creates a uniquely named schema and removes it afterward. They check first and repeated loads, new keys, unchanged existing values, empty facts, SQL views/queries, and rollback after a payment constraint failure. The test role needs permission to create schemas.

## Files worth reading

```text
src/extract.py          CSV loading and required-column checks
src/transform.py        Cleaning rules and per-source row counts
src/validate.py         Key, reference, and numeric checks
src/load.py             Transactional dimension and fact inserts
src/pipeline.py         Pipeline entry point and logging
src/make_images.py      Database-backed charts and model diagrams
sql/create_tables.sql  Five tables, constraints, and indexes
sql/views.sql          Three analytical views
sql/analytics_queries.sql
tests/                 Synthetic cases and PostgreSQL integration tests
docs/run_results.md    Measured results and verification environment
data/raw/              Downloaded CSVs (ignored)
logs/                  Pipeline logs (ignored)
```

## Technical lessons and next steps

The main modeling lesson is that item and payment facts need different grains. Business keys prevent duplicate inserts, but they do not handle source corrections. Separating rejected data from excluded order statuses also makes the quality counts easier to interpret.

Next improvements would be a defined update policy for corrected source records, a rejected-row file with reasons, and source-to-warehouse reconciliation for delivered orders missing items or payments. The current implementation loads data into memory and runs manually; it has no scheduler, streaming ingestion, or schema migration system.

## Author

[Ahmed Sameh](https://github.com/abosameh522)
