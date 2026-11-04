-- Intermediate SQL Analytics: Window Functions, CTEs, Self-Joins
-- Demonstrates data engineering SQL skills beyond simple aggregations

-- ====================
-- 1. RUNNING TOTAL & RANK: Monthly sales with cumulative revenue and month-over-month rank
-- ====================
-- Window functions: SUM() OVER (ORDER BY ...), RANK() OVER (ORDER BY ...)
-- Business use: Track growth trajectory and identify peak periods

WITH monthly_totals AS (
    SELECT
        d.year,
        d.month,
        SUM(f.total_amount) AS monthly_revenue,
        COUNT(DISTINCT f.order_id) AS monthly_orders
    FROM fact_orders f
    JOIN dim_date d ON d.date_key = f.date_key
    GROUP BY d.year, d.month
)
SELECT
    year,
    month,
    monthly_revenue,
    monthly_orders,
    SUM(monthly_revenue) OVER (ORDER BY year, month) AS cumulative_revenue,
    RANK() OVER (ORDER BY monthly_revenue DESC) AS revenue_rank
FROM monthly_totals
ORDER BY year, month;


-- ====================
-- 2. LEAD/LAG: Month-over-month growth rate
-- ====================
-- Window functions: LAG() to access previous row
-- Business use: Identify acceleration or slowdown in sales trends

WITH monthly_revenue AS (
    SELECT
        d.year * 100 + d.month AS year_month,
        SUM(f.total_amount) AS revenue
    FROM fact_orders f
    JOIN dim_date d ON d.date_key = f.date_key
    GROUP BY d.year, d.month
)
SELECT
    year_month,
    revenue,
    LAG(revenue) OVER (ORDER BY year_month) AS prev_month_revenue,
    ROUND(
        100.0 * (revenue - LAG(revenue) OVER (ORDER BY year_month)) /
        NULLIF(LAG(revenue) OVER (ORDER BY year_month), 0),
        2
    ) AS growth_rate_pct
FROM monthly_revenue
ORDER BY year_month;


-- ====================
-- 3. NTILE: Customer value quartiles (RFM-style segmentation)
-- ====================
-- Window function: NTILE() for percentile bucketing
-- Business use: Identify high-value vs low-value customers for retention targeting

WITH customer_lifetime AS (
    SELECT
        c.customer_unique_id,
        COUNT(DISTINCT f.order_id) AS total_orders,
        SUM(f.total_amount) AS lifetime_value,
        MAX(d.full_date) AS last_order_date
    FROM fact_orders f
    JOIN dim_customers c ON c.customer_key = f.customer_key
    JOIN dim_date d ON d.date_key = f.date_key
    GROUP BY c.customer_unique_id
)
SELECT
    customer_unique_id,
    total_orders,
    lifetime_value,
    last_order_date,
    NTILE(4) OVER (ORDER BY lifetime_value DESC) AS value_quartile
FROM customer_lifetime
ORDER BY lifetime_value DESC
LIMIT 20;


-- ====================
-- 4. SELF-JOIN: Repeat purchasers (customers who ordered the same product category twice)
-- ====================
-- Self-join on fact_orders to find repeat behavior
-- Business use: Identify product stickiness and cross-sell opportunities

WITH customer_category_orders AS (
    SELECT DISTINCT
        f.customer_key,
        p.category,
        f.order_id,
        f.date_key
    FROM fact_orders f
    JOIN dim_products p ON p.product_key = f.product_key
)
SELECT
    c.customer_unique_id,
    a.category,
    COUNT(DISTINCT a.order_id) AS times_purchased
FROM customer_category_orders a
JOIN customer_category_orders b
    ON a.customer_key = b.customer_key
    AND a.category = b.category
    AND a.order_id < b.order_id  -- Self-join: find repeat purchases
JOIN dim_customers c ON c.customer_key = a.customer_key
GROUP BY c.customer_unique_id, a.category
HAVING COUNT(DISTINCT a.order_id) >= 2
ORDER BY times_purchased DESC, c.customer_unique_id
LIMIT 15;


-- ====================
-- 5. COMPLEX CTE: Product affinity (frequently co-purchased categories)
-- ====================
-- Multi-level CTE with self-join
-- Business use: Product recommendation engine, bundle optimization

WITH order_categories AS (
    SELECT DISTINCT
        f.order_id,
        p.category
    FROM fact_orders f
    JOIN dim_products p ON p.product_key = f.product_key
),
category_pairs AS (
    SELECT
        a.category AS category_a,
        b.category AS category_b,
        COUNT(DISTINCT a.order_id) AS co_purchase_count
    FROM order_categories a
    JOIN order_categories b
        ON a.order_id = b.order_id
        AND a.category < b.category  -- Avoid duplicate pairs and self-pairs
    GROUP BY a.category, b.category
)
SELECT
    category_a,
    category_b,
    co_purchase_count,
    RANK() OVER (ORDER BY co_purchase_count DESC) AS affinity_rank
FROM category_pairs
WHERE co_purchase_count >= 10  -- Minimum support threshold
ORDER BY co_purchase_count DESC
LIMIT 10;


-- ====================
-- 6. WINDOW + FILTER: Top 3 products per category by revenue
-- ====================
-- Window function: ROW_NUMBER() partitioned by category
-- Business use: Category-level merchandising and inventory prioritization

WITH product_revenue AS (
    SELECT
        p.category,
        p.product_id,
        SUM(f.total_amount) AS total_revenue,
        SUM(f.quantity) AS units_sold,
        ROW_NUMBER() OVER (PARTITION BY p.category ORDER BY SUM(f.total_amount) DESC) AS category_rank
    FROM fact_orders f
    JOIN dim_products p ON p.product_key = f.product_key
    GROUP BY p.category, p.product_id
)
SELECT
    category,
    product_id,
    total_revenue,
    units_sold,
    category_rank
FROM product_revenue
WHERE category_rank <= 3
ORDER BY category, category_rank;
