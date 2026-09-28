from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from load import connect


ROOT = Path(__file__).resolve().parents[1]
NAVY = "#14233b"
BLUE = "#2a6fdb"
PALE = "#e9f1ff"
TEXT = "#24354d"


def canvas(width=16, height=9):
    figure, axis = plt.subplots(figsize=(width, height), dpi=120)
    figure.patch.set_facecolor("#f8fafc")
    axis.set_facecolor("#f8fafc")
    axis.set_xlim(0, 100)
    axis.set_ylim(0, 100)
    axis.axis("off")
    return figure, axis


def box(axis, x, y, width, height, title, detail="", color=PALE):
    shape = FancyBboxPatch((x, y), width, height, boxstyle="round,pad=0.015,rounding_size=2", facecolor=color, edgecolor="#c5d5ec", linewidth=1.5)
    axis.add_patch(shape)
    axis.text(x + width / 2, y + height * 0.60, title, ha="center", va="center", fontsize=16, weight="bold", color=NAVY)
    if detail:
        axis.text(x + width / 2, y + height * 0.31, detail, ha="center", va="center", fontsize=10.5, color=TEXT)


def arrow(axis, start, end):
    axis.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=18, linewidth=2, color=BLUE))


def save(figure, path):
    path.parent.mkdir(exist_ok=True)
    figure.savefig(path, bbox_inches="tight", facecolor=figure.get_facecolor())
    plt.close(figure)


with connect() as connection:
    with connection.cursor() as cursor:
        cursor.execute("SELECT SUM(total_amount), COUNT(DISTINCT order_id), COUNT(*) FROM fact_orders")
        revenue, order_count, item_count = cursor.fetchone()
        cursor.execute("SELECT COUNT(*) FROM fact_payments")
        payment_count = cursor.fetchone()[0]
        cursor.execute("SELECT category, item_revenue FROM (SELECT p.category, SUM(f.total_amount) AS item_revenue FROM fact_orders f JOIN dim_products p ON p.product_key = f.product_key GROUP BY p.category) x ORDER BY item_revenue DESC LIMIT 5")
        categories = cursor.fetchall()
        cursor.execute("SELECT month, item_revenue FROM monthly_sales_summary ORDER BY month")
        monthly = cursor.fetchall()

figure, axis = canvas(16, 4.5)
axis.text(3, 88, "E-Commerce Data Pipeline & Warehouse", fontsize=24, weight="bold", color=NAVY)
stages = [
    ("CSV files", "Olist source data"),
    ("Python ETL", "Pandas cleaning"),
    ("Validation", "Keys and values"),
    ("PostgreSQL", "Transactional load"),
    ("Star schema", "Facts + dimensions"),
    ("SQL analytics", "Views and queries"),
]
for index, (title, detail) in enumerate(stages):
    x = 2 + index * 16.5
    box(axis, x, 40, 14, 27, title, detail)
    if index < len(stages) - 1:
        arrow(axis, (x + 14, 53.5), (x + 16.3, 53.5))
axis.text(3, 20, "Source: Olist Brazilian E-Commerce dataset  |  Delivered orders  |  Item revenue excludes freight", fontsize=12, color=TEXT)
save(figure, ROOT / "images/architecture.png")

figure, axis = canvas()
axis.text(4, 91, "Pipeline overview", fontsize=28, weight="bold", color=NAVY)
axis.text(4, 84, "E-Commerce Data Pipeline & Warehouse", fontsize=16, color=TEXT)
for index, (title, detail) in enumerate(stages):
    x = 4 + (index % 3) * 32
    y = 59 if index < 3 else 25
    box(axis, x, y, 27, 19, title, detail)
    if index in (0, 1, 3, 4):
        arrow(axis, (x + 27, y + 9.5), (x + 31, y + 9.5))
arrow(axis, (82, 58), (18, 45))
axis.text(4, 10, f"{order_count:,} delivered orders   •   {item_count:,} order items   •   {payment_count:,} payments", fontsize=15, color=BLUE, weight="bold")
save(figure, ROOT / "portfolio/pipeline_overview.png")

figure, axis = canvas()
axis.text(4, 91, "Data model", fontsize=28, weight="bold", color=NAVY)
axis.text(4, 84, "Order item grain, with a separate payment fact", fontsize=15, color=TEXT)
box(axis, 39, 39, 25, 25, "fact_orders", "order_id + order_item_id\nquantity, price, amount", "#d9e8ff")
box(axis, 4, 44, 25, 20, "dim_customers", "customer_key • customer_id\ncustomer_unique_id")
box(axis, 71, 44, 25, 20, "dim_products", "product_key • product_id\ncategory")
box(axis, 39, 8, 25, 18, "dim_date", "date_key • full_date\nyear, month, day")
box(axis, 4, 8, 25, 18, "fact_payments", "order_id + sequence\npayment type, amount")
arrow(axis, (39, 54), (29, 54))
arrow(axis, (64, 54), (71, 54))
arrow(axis, (51.5, 39), (51.5, 26))
arrow(axis, (29, 18), (39, 18))
arrow(axis, (16.5, 26), (16.5, 44))
axis.text(70, 20, "Payment fact also references\ncustomer and date dimensions", fontsize=12, color=TEXT)
save(figure, ROOT / "portfolio/data_model.png")

figure = plt.figure(figsize=(16, 9), dpi=120, facecolor="#f8fafc")
figure.text(0.05, 0.92, "SQL analytics", fontsize=28, weight="bold", color=NAVY)
figure.text(0.05, 0.865, "Delivered orders • item revenue excludes freight", fontsize=14, color=TEXT)
metrics = [
    ("Item revenue", f"{revenue:,.2f}"),
    ("Orders", f"{order_count:,}"),
    ("Average order value", f"{revenue / order_count:,.2f}"),
    ("Items sold", f"{item_count:,}"),
]
for index, (label, value) in enumerate(metrics):
    x = 0.05 + index * 0.24
    figure.text(x, 0.76, label, fontsize=12, color=TEXT)
    figure.text(x, 0.70, value, fontsize=24, weight="bold", color=BLUE)

left = figure.add_axes((0.07, 0.13, 0.42, 0.42), facecolor="#f8fafc")
labels = [row[0].replace("_", " ") for row in categories][::-1]
values = [float(row[1]) / 1_000_000 for row in categories][::-1]
left.barh(labels, values, color=BLUE)
left.set_title("Top categories by item revenue", color=NAVY, loc="left", fontsize=15)
left.set_xlabel("Millions", color=TEXT)
left.spines[["top", "right"]].set_visible(False)

right = figure.add_axes((0.57, 0.13, 0.38, 0.42), facecolor="#f8fafc")
right.plot([row[0] for row in monthly], [float(row[1]) / 1_000_000 for row in monthly], color=BLUE, linewidth=2.5)
right.set_title("Monthly item revenue", color=NAVY, loc="left", fontsize=15)
right.set_ylabel("Millions", color=TEXT)
right.tick_params(axis="x", rotation=35)
right.spines[["top", "right"]].set_visible(False)
save(figure, ROOT / "portfolio/sql_analytics.png")
