-- Item revenue excludes freight. Only delivered orders are loaded.
SELECT SUM(total_amount) AS total_item_revenue FROM fact_orders;

SELECT COUNT(DISTINCT order_id) AS total_orders FROM fact_orders;

WITH order_totals AS (
    SELECT order_id, SUM(total_amount) AS order_amount
    FROM fact_orders
    GROUP BY order_id
)
SELECT ROUND(AVG(order_amount), 2) AS average_order_value FROM order_totals;

SELECT month, orders, item_revenue
FROM monthly_sales_summary
ORDER BY month;

SELECT product_id, category, units_sold, item_revenue
FROM product_sales_summary
ORDER BY units_sold DESC, product_id
LIMIT 10;

SELECT customer_unique_id, orders, item_revenue
FROM customer_order_summary
ORDER BY item_revenue DESC, customer_unique_id
LIMIT 10;

SELECT p.category, SUM(f.total_amount) AS item_revenue
FROM fact_orders f
JOIN dim_products p ON p.product_key = f.product_key
GROUP BY p.category
ORDER BY item_revenue DESC;

SELECT customer_unique_id, orders, item_revenue
FROM customer_order_summary
WHERE orders > 1
ORDER BY orders DESC, item_revenue DESC
LIMIT 10;

SELECT payment_type, COUNT(*) AS payments, SUM(payment_amount) AS payment_total
FROM fact_payments
GROUP BY payment_type
ORDER BY payment_total DESC;
