CREATE OR REPLACE VIEW monthly_sales_summary AS
SELECT date_trunc('month', d.full_date)::date AS month,
       COUNT(DISTINCT f.order_id) AS orders,
       SUM(f.total_amount) AS item_revenue
FROM fact_orders f
JOIN dim_date d ON d.date_key = f.date_key
GROUP BY 1;

CREATE OR REPLACE VIEW customer_order_summary AS
SELECT c.customer_unique_id,
       COUNT(DISTINCT f.order_id) AS orders,
       SUM(f.total_amount) AS item_revenue
FROM fact_orders f
JOIN dim_customers c ON c.customer_key = f.customer_key
GROUP BY c.customer_unique_id;

CREATE OR REPLACE VIEW product_sales_summary AS
SELECT p.product_id, p.category,
       SUM(f.quantity) AS units_sold,
       SUM(f.total_amount) AS item_revenue
FROM fact_orders f
JOIN dim_products p ON p.product_key = f.product_key
GROUP BY p.product_id, p.category;
