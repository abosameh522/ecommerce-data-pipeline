CREATE TABLE IF NOT EXISTS dim_customers (
    customer_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id TEXT NOT NULL UNIQUE,
    customer_unique_id TEXT NOT NULL,
    city TEXT NOT NULL,
    state CHAR(2) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dim_customers_unique_id ON dim_customers (customer_unique_id);

CREATE TABLE IF NOT EXISTS dim_products (
    product_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date DATE NOT NULL UNIQUE,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_orders (
    order_id TEXT NOT NULL,
    order_item_id INTEGER NOT NULL,
    customer_key BIGINT NOT NULL REFERENCES dim_customers(customer_key),
    product_key BIGINT NOT NULL REFERENCES dim_products(product_key),
    date_key INTEGER NOT NULL REFERENCES dim_date(date_key),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price >= 0),
    total_amount NUMERIC(14, 2) NOT NULL CHECK (total_amount >= 0),
    PRIMARY KEY (order_id, order_item_id)
);

CREATE INDEX IF NOT EXISTS idx_fact_orders_date ON fact_orders (date_key);
CREATE INDEX IF NOT EXISTS idx_fact_orders_customer ON fact_orders (customer_key);
CREATE INDEX IF NOT EXISTS idx_fact_orders_product ON fact_orders (product_key);

CREATE TABLE IF NOT EXISTS fact_payments (
    order_id TEXT NOT NULL,
    payment_sequential INTEGER NOT NULL,
    customer_key BIGINT NOT NULL REFERENCES dim_customers(customer_key),
    date_key INTEGER NOT NULL REFERENCES dim_date(date_key),
    payment_type TEXT NOT NULL,
    payment_amount NUMERIC(14, 2) NOT NULL CHECK (payment_amount >= 0),
    PRIMARY KEY (order_id, payment_sequential)
);
