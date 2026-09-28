# E-Commerce Data Pipeline & Warehouse

## Overview

A Python and PostgreSQL pipeline that turns Olist e-commerce CSV files into a small warehouse for sales analysis. The main sales fact has one row per order item. Payments are stored separately so payment totals do not multiply when an order has several items.

## Architecture

![Pipeline architecture](images/architecture.png)

CSV files → Python ETL → validation → PostgreSQL → star schema → SQL analytics

## Dataset

The source is the [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), an anonymized sample of orders from 2016–2018. This project reads six of its nine CSV files: customers, products, orders, order items, payments, and product category translations. The source contains 99,441 orders, 112,650 order items, and 103,886 payment records. The download is about 43 MB; the full uncompressed dataset is about 126 MB.

The source license is [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). Raw files are excluded from Git. Download them from Kaggle before running the pipeline and follow the source license when reusing the data.

## Data Model

| Table | Grain | Main columns |
| --- | --- | --- |
| `dim_customers` | One source customer ID | Surrogate key, unique customer ID, city, state |
| `dim_products` | One product ID | Surrogate key, translated category |
| `dim_date` | One purchase date | Date key, date, year, month, day |
| `fact_orders` | One order item | Order ID + item ID, dimension keys, quantity, unit price, item amount |
| `fact_payments` | One payment record | Order ID + payment sequence, customer/date keys, payment type and amount |

`fact_orders` joins to the three dimensions. `fact_payments` joins to customer and date. The original `customer_unique_id` remains in `dim_customers` so repeat customers can be counted across orders.

![Warehouse model](portfolio/data_model.png)

## ETL Workflow

The extractor checks for all six files and logs their row counts. Pandas removes exact duplicates, parses purchase dates and numeric fields, normalizes state and payment text, and translates product categories. Missing product categories become `Unknown`; missing customer cities become `Unknown`.

Only delivered orders are loaded into the sales warehouse. Other order statuses, and their items and payments, are counted as excluded in the quality report. Invalid IDs, dates, item numbers, prices, payment numbers, and broken source references are rejected. Validation then checks primary-key uniqueness, references, dates, prices, and quantities before loading.

Dimensions load first, followed by both facts in one PostgreSQL transaction. Each table has a business key or composite primary key. `INSERT ... ON CONFLICT DO NOTHING` makes repeated runs incremental: existing rows are skipped, while new keys are inserted. Existing records are not updated if their source values change.

## SQL Analysis

`sql/analytics_queries.sql` covers item revenue, delivered order count, average order value, monthly sales, top products and customers, category sales, repeat customers, and payment types. The three views summarize monthly sales, customer orders, and product sales. Revenue uses item prices and excludes freight and payment totals.

## Project Structure

```text
data/raw/             Downloaded source CSVs (ignored by Git)
src/                  Extraction, cleaning, validation, loading, pipeline, images
sql/                  Tables, views, and analytics queries
images/architecture.png
portfolio/            Three project images
logs/                 Run logs (ignored by Git)
```

## Technologies

Python, Pandas, psycopg, PostgreSQL, SQL, and Matplotlib.

## How to Run

1. Create a PostgreSQL database named `ecommerce_warehouse` and a login role with access to it.
2. Create a Python environment and install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Download the [Olist dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) and place these files in `data/raw/`: `olist_customers_dataset.csv`, `olist_products_dataset.csv`, `olist_orders_dataset.csv`, `olist_order_items_dataset.csv`, `olist_order_payments_dataset.csv`, and `product_category_name_translation.csv`. One way to download the public archive is:

   ```bash
   curl -L https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce -o olist.zip
   unzip -j olist.zip -d data/raw
   ```

4. Set the connection variables from `.env.example` in your shell. `DB_PASSWORD` is optional if your local PostgreSQL authentication does not use a password. Run:

   ```bash
   python src/pipeline.py
   psql -d ecommerce_warehouse -f sql/analytics_queries.sql
   python src/make_images.py
   ```

The pipeline creates the tables and views automatically. It prints and logs input, duplicate, rejected, excluded, inserted, and skipped counts. Run it a second time to check that all insert counts are zero. Logs are written to `logs/pipeline.log`.

## Key Learnings

The item and payment facts need separate grains to keep sales totals accurate. Business keys plus database constraints make repeated loads safe. A quality report should distinguish bad records from orders excluded by the delivered-order rule.

## Author

[Ahmed Sameh](https://github.com/abosameh522)
