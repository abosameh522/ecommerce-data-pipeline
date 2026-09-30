# Full-data verification

Run date: 2026-09-30. Source: the public Olist archive linked in the README.

Archive SHA-256:

```text
967e41e04fc306fe604e2a693f488995a8b41e5047418f8a5c8e4abd6deca784
```

## Environment

- Linux, Python 3.14.7
- PostgreSQL 18.6, isolated local database
- pandas 3.0.6, psycopg 3.3.6, Matplotlib 3.11.2
- Dependencies installed from `requirements.txt` in a new virtual environment

These are the versions used for this run, not a claim that all versions allowed by the dependency ranges have been tested.

## Source reconciliation

| Source | Input | Duplicates | Rejected | Excluded | Cleaned |
| --- | ---: | ---: | ---: | ---: | ---: |
| Customers | 99,441 | 0 | 0 | 0 | 99,441 |
| Products | 32,951 | 0 | 0 | 0 | 32,951 |
| Orders | 99,441 | 0 | 0 | 2,963 | 96,478 |
| Items | 112,650 | 0 | 0 | 2,453 | 110,197 |
| Payments | 103,886 | 0 | 0 | 3,130 | 100,756 |
| Category translations | 71 | 0 | 0 | 0 | 71 |

No rows were rejected by the implemented rules in this extract. That does not mean the source is complete or free of every possible data-quality issue. Missing categories are retained as `Unknown`, and non-delivered orders are excluded by design.

## Database output

| Table | First-run inserts | Second-run inserts |
| --- | ---: | ---: |
| `dim_customers` | 99,441 | 0 |
| `dim_products` | 32,951 | 0 |
| `dim_date` | 612 | 0 |
| `fact_orders` | 110,197 | 0 |
| `fact_payments` | 100,756 | 0 |

Customer and product dimensions contain all valid source rows, including those not referenced by delivered orders. The date dimension contains observed purchase dates rather than a continuous calendar.

All five tables were compared row-for-row with a separate full-data run of the original implementation at `1775795`. Their contents were identical. The changes affect malformed-input handling and diagnostics, without changing the results for this source snapshot.

## SQL results

All nine statements in `sql/analytics_queries.sql` executed with `psql -X -v ON_ERROR_STOP=1`.

| Metric | Value |
| --- | ---: |
| Distinct orders in `fact_orders` | 96,478 |
| Item revenue | BRL 13,221,498.11 |
| Average item value per order | BRL 137.04 |
| Highest-revenue category | `health_beauty` |
| Revenue for that category | BRL 1,233,131.72 |

| Payment type | Records | Payment total (BRL) |
| --- | ---: | ---: |
| `credit_card` | 74,586 | 12,101,094.88 |
| `boleto` | 19,191 | 2,769,932.58 |
| `voucher` | 5,493 | 343,013.19 |
| `debit_card` | 1,486 | 208,421.12 |

Payment totals and item revenue are different measures; item revenue excludes freight. The chart in `portfolio/sql_analytics.png` was regenerated from this database.

## Regression coverage

The 20 tests passed with PostgreSQL integration enabled. They cover schema errors, string ID preservation, exclusions versus rejections, duplicate/conflicting keys, missing translations, invalid numeric ranges, broken references, empty facts, repeated inserts, separate fact totals, unchanged existing values, and transaction rollback.

Without `TEST_DATABASE_URL`, the 16 non-database tests pass and the four integration tests are explicitly skipped. The suite uses Python's standard-library `unittest`; it needs no additional testing package.

## Verification limits

The run used a local Unix-socket PostgreSQL connection. Remote servers, password authentication, Windows/macOS setup, concurrent loaders, and other dependency versions were not tested. The pipeline is insert-only; repeat-load tests do not imply support for source corrections or deletions.
