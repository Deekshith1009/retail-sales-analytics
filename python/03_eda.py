"""
03_eda.py
Purpose: Exploratory data analysis on the cleaned Superstore data.
Run from the project root:  python python/03_eda.py

Reads : data/processed/superstore_clean.csv
Writes: charts   -> screenshots/*.png
        tables   -> data/processed/eda_tables/*.csv
Nothing in the raw or cleaned data is modified.
"""

import logging
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # save charts to files instead of opening windows
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd
import seaborn as sns

# ---------------------------------------------------------------
# 1. SETTINGS
# ---------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLEAN_FILE = PROJECT_ROOT / "data" / "processed" / "superstore_clean.csv"
CHART_DIR = PROJECT_ROOT / "screenshots"
TABLE_DIR = PROJECT_ROOT / "data" / "processed" / "eda_tables"

BASELINE_SALES = 2297200.8603
BASELINE_PROFIT = 286397.0217

BAND_ORDER = ["No Discount", "Low (1-20%)", "Medium (21-40%)", "High (>40%)"]
SHIP_ORDER = ["Same Day", "First Class", "Second Class", "Standard Class"]

US_STATES_PLUS_DC = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "District of Columbia", "Florida", "Georgia",
    "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire",
    "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota",
    "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island",
    "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
    "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming",
]

BLUE, ORANGE, GREEN, RED = "#2e86c1", "#e67e22", "#27ae60", "#c0392b"
money = FuncFormatter(lambda x, _: f"${x / 1000:,.0f}K")

sns.set_theme(style="whitegrid", context="notebook")


# ---------------------------------------------------------------
# 2. HELPER FUNCTIONS
# ---------------------------------------------------------------
def section(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def show(title: str, table: pd.DataFrame) -> None:
    print(f"\n--- {title} ---")
    print(table.to_string(index=False, float_format=lambda x: f"{x:,.2f}"))


def save_table(table: pd.DataFrame, name: str) -> None:
    table.to_csv(TABLE_DIR / name, index=False)


def save_chart(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(CHART_DIR / name, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logging.info("Saved chart: %s", name)


def load_clean() -> pd.DataFrame:
    if not CLEAN_FILE.exists():
        raise FileNotFoundError(f"Run 02_data_cleaning.py first. Missing: {CLEAN_FILE}")
    df = pd.read_csv(CLEAN_FILE, dtype={"postal_code": str})
    needed = ["line_id", "ship_mode", "segment", "state", "region", "category",
              "sub_category", "sales", "quantity", "discount", "profit",
              "loss_flag", "discount_band", "profit_margin"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(f"Cleaned file is missing columns: {missing}")
    df["discount_band"] = pd.Categorical(df["discount_band"], categories=BAND_ORDER, ordered=True)
    logging.info("Loaded cleaned data: %d rows, %d columns", *df.shape)
    return df


def summarise(df: pd.DataFrame, by) -> pd.DataFrame:
    """One summary table per grouping. Margin = total profit / total sales."""
    g = df.groupby(by, observed=True).agg(
        lines=("line_id", "count"),
        sales=("sales", "sum"),
        profit=("profit", "sum"),
        quantity=("quantity", "sum"),
        loss_lines=("loss_flag", "sum"),
        avg_discount=("discount", "mean"),
    )
    g["margin_pct"] = g["profit"] / g["sales"] * 100
    g["loss_line_pct"] = g["loss_lines"] / g["lines"] * 100
    g["avg_discount_pct"] = g["avg_discount"] * 100
    return g.drop(columns="avg_discount").reset_index()


def check_totals(table: pd.DataFrame, name: str) -> bool:
    """Every summary table must add back to the Phase 1 baseline."""
    ok = (math.isclose(table["sales"].sum(), BASELINE_SALES, abs_tol=0.01)
          and math.isclose(table["profit"].sum(), BASELINE_PROFIT, abs_tol=0.01))
    logging.info("Reconciliation [%s]: sales=%s profit=%s -> %s", name,
                 f"{table['sales'].sum():,.2f}", f"{table['profit'].sum():,.2f}",
                 "PASS" if ok else "FAIL")
    return ok


# ---------------------------------------------------------------
# 3. REUSABLE CHARTS
# ---------------------------------------------------------------
def chart_sales_and_margin(table, label_col, label, filename, rotation=0):
    """Left: sales vs profit bars. Right: margin % per group."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    data = table.set_index(label_col)[["sales", "profit"]]
    data.index = data.index.astype(str)
    data.plot(kind="bar", ax=axes[0], color=[BLUE, ORANGE])
    axes[0].set_title(f"Sales and profit by {label}")
    axes[0].set_xlabel("")
    axes[0].set_ylabel("USD")
    axes[0].yaxis.set_major_formatter(money)
    axes[0].tick_params(axis="x", rotation=rotation)
    axes[0].legend(["Sales", "Profit"])

    margin = table.set_index(label_col)["margin_pct"]
    labels = margin.index.astype(str)
    axes[1].bar(labels, margin.values, color=[RED if v < 0 else GREEN for v in margin.values])
    axes[1].axhline(0, color="black", linewidth=0.8)
    axes[1].set_title(f"Profit margin % by {label}")
    axes[1].set_ylabel("Profit margin (%)")
    axes[1].tick_params(axis="x", rotation=rotation)
    for i, v in enumerate(margin.values):
        axes[1].text(i, v, f"{v:.1f}%", ha="center", va="bottom" if v >= 0 else "top")
    save_chart(fig, filename)


def chart_profit_bars(table, label_col, title, filename, height=7):
    """Horizontal bars of total profit; losses shown in red."""
    t = table.sort_values("profit")
    fig, ax = plt.subplots(figsize=(10, height))
    ax.barh(t[label_col].astype(str), t["profit"],
            color=[RED if v < 0 else BLUE for v in t["profit"]])
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_title(title)
    ax.set_xlabel("Total profit (USD)")
    save_chart(fig, filename)


def analyse_dimension(df, col, label, filename, order=None, rotation=0):
    t = summarise(df, col)
    if order:
        t = t.set_index(col).loc[order].reset_index()
    else:
        t = t.sort_values("profit", ascending=False)
    show(f"PERFORMANCE BY {label.upper()}", t)
    ok = check_totals(t, label)
    chart_sales_and_margin(t, col, label, filename, rotation)
    save_table(t, f"{col}_summary.csv")
    return t, ok


# ---------------------------------------------------------------
# 4. ANALYSES
# ---------------------------------------------------------------
def analyse_overall(df: pd.DataFrame) -> None:
    section("1. OVERALL SALES AND PROFITABILITY")
    total_sales, total_profit = df["sales"].sum(), df["profit"].sum()
    gains = df.loc[df["profit"] > 0, "profit"].sum()
    losses = df.loc[df["profit"] < 0, "profit"].sum()
    rows = [
        ("Sales lines (rows)", f"{len(df):,}"),
        ("Total sales", f"{total_sales:,.2f}"),
        ("Total profit", f"{total_profit:,.2f}"),
        ("Overall profit margin", f"{total_profit / total_sales * 100:.2f}%"),
        ("Total quantity", f"{int(df['quantity'].sum()):,}"),
        ("Loss-making lines", f"{int(df['loss_flag'].sum()):,} ({df['loss_flag'].mean() * 100:.2f}% of lines)"),
        ("Profit from profitable lines", f"{gains:,.2f}"),
        ("Loss from loss-making lines", f"{losses:,.2f}"),
        ("Losses as % of profitable-line profit", f"{abs(losses) / gains * 100:.2f}%"),
        ("Average sales per line", f"{df['sales'].mean():,.2f}"),
        ("Median sales per line", f"{df['sales'].median():,.2f}"),
        ("Median profit per line", f"{df['profit'].median():,.2f}"),
    ]
    for name, value in rows:
        print(f"{name:<42}{value}")


def analyse_subcategory(df: pd.DataFrame) -> bool:
    t = summarise(df, "sub_category").sort_values("profit")
    show("PERFORMANCE BY SUB-CATEGORY (lowest profit first)", t)
    ok = check_totals(t, "sub_category")
    chart_profit_bars(t, "sub_category", "Total profit by sub-category", "03_subcategory_profit.png")
    save_table(t, "sub_category_summary.csv")
    negatives = t[t["profit"] < 0]
    print(f"\nSub-categories with NEGATIVE total profit: {len(negatives)}")
    if len(negatives):
        print(negatives[["sub_category", "sales", "profit", "margin_pct"]].to_string(
            index=False, float_format=lambda x: f"{x:,.2f}"))
    return ok


def analyse_state(df: pd.DataFrame) -> bool:
    t = summarise(df, "state").sort_values("profit")
    ok = check_totals(t, "state")
    save_table(t, "state_summary.csv")
    show("10 LOWEST-PROFIT STATES", t.head(10))
    show("10 HIGHEST-PROFIT STATES", t.tail(10).iloc[::-1])
    extremes = pd.concat([t.head(10), t.tail(10)])
    chart_profit_bars(extremes, "state", "Total profit: 10 lowest and 10 highest states",
                      "05_state_profit_extremes.png", height=8)
    present = set(df["state"].unique())
    expected = set(US_STATES_PLUS_DC)
    print(f"\nDistinct states in data: {len(present)}")
    print(f"Expected (50 states + DC): {len(expected)}")
    print(f"In the standard list but NOT in the data: {sorted(expected - present) or 'none'}")
    print(f"In the data but NOT in the standard list: {sorted(present - expected) or 'none'}")
    return ok


def analyse_discounts(df: pd.DataFrame) -> bool:
    section("6. DISCOUNTS AND PROFITABILITY")
    ok = True

    # 6a. by discount band
    by_band = summarise(df, "discount_band").set_index("discount_band").loc[BAND_ORDER].reset_index()
    show("BY DISCOUNT BAND", by_band)
    ok &= check_totals(by_band, "discount_band")
    chart_sales_and_margin(by_band, "discount_band", "discount band", "06_discount_band.png", rotation=15)
    save_table(by_band, "discount_band_summary.csv")

    # 6b. by exact discount level
    by_level = summarise(df, "discount")
    show("BY EXACT DISCOUNT LEVEL", by_level)
    ok &= check_totals(by_level, "discount_level")
    save_table(by_level, "discount_level_summary.csv")
    fig, ax = plt.subplots(figsize=(11, 5))
    labels = [f"{d * 100:.0f}%" for d in by_level["discount"]]
    ax.bar(labels, by_level["margin_pct"], color=[RED if v < 0 else GREEN for v in by_level["margin_pct"]])
    ax.axhline(0, color="black", linewidth=0.8)
    for i, (m, n) in enumerate(zip(by_level["margin_pct"], by_level["lines"])):
        ax.text(i, m, f"{m:.0f}%\nn={n}", ha="center", va="bottom" if m >= 0 else "top", fontsize=8)
    ax.set_title("Profit margin % at each discount level (n = number of sales lines)")
    ax.set_xlabel("Discount level")
    ax.set_ylabel("Profit margin (%)")
    save_chart(fig, "07_discount_level_margin.png")

    # 6c. distribution of line-level margin per discount level
    fig, ax = plt.subplots(figsize=(11, 5))
    order = [f"{d * 100:.0f}%" for d in sorted(df["discount"].unique())]
    sns.boxplot(x=df["discount"].map(lambda d: f"{d * 100:.0f}%"), y=df["profit_margin"] * 100,
                order=order, showfliers=False, color="#85c1e9", ax=ax)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("Distribution of line-level profit margin by discount level (outliers hidden)")
    ax.set_xlabel("Discount level")
    ax.set_ylabel("Line-level profit margin (%)")
    save_chart(fig, "08_discount_margin_boxplot.png")

    # 6d. correlation (descriptive only)
    print("\n--- CORRELATION BETWEEN DISCOUNT AND LINE-LEVEL MARGIN ---")
    print(f"Pearson : {df['discount'].corr(df['profit_margin']):.3f}")
    print(f"Spearman: {df['discount'].rank().corr(df['profit_margin'].rank()):.3f}")
    for cat in sorted(df["category"].unique()):
        sub = df[df["category"] == cat]
        print(f"  within {cat:<16} Pearson = {sub['discount'].corr(sub['profit_margin']):.3f}")
    print("A correlation describes a pattern. It does not prove that discounts CAUSE the margin change.")

    # 6e. category x discount band margin heatmap
    grid = df.groupby(["category", "discount_band"], observed=True)[["sales", "profit"]].sum()
    grid["margin_pct"] = grid["profit"] / grid["sales"] * 100
    heat = grid["margin_pct"].unstack("discount_band").reindex(columns=BAND_ORDER)
    counts = (df.groupby(["category", "discount_band"], observed=True).size()
              .unstack("discount_band").reindex(columns=BAND_ORDER))
    print("\n--- PROFIT MARGIN % BY CATEGORY x DISCOUNT BAND ---")
    print(heat.to_string(float_format=lambda x: f"{x:,.1f}"))
    print("\n--- NUMBER OF SALES LINES IN EACH CELL ---")
    print(counts.to_string())
    fig, ax = plt.subplots(figsize=(9, 4))
    sns.heatmap(heat, annot=True, fmt=".1f", cmap="RdYlGn", center=0, linewidths=0.5, ax=ax,
                cbar_kws={"label": "Profit margin (%)"})
    ax.set_title("Profit margin % by category and discount band")
    ax.set_xlabel("")
    ax.set_ylabel("")
    save_chart(fig, "09_category_discount_heatmap.png")
    heat.reset_index().to_csv(TABLE_DIR / "category_discount_margin.csv", index=False)
    return ok


def analyse_losses(df: pd.DataFrame) -> None:
    section("7. LOSS-MAKING LINES AND PRODUCTS")
    losses = df[df["profit"] < 0]

    by_sub = summarise(df, "sub_category")[["sub_category", "lines", "loss_lines", "loss_line_pct", "profit", "margin_pct"]]
    gross = losses.groupby("sub_category")["profit"].sum().rename("gross_loss").reset_index()
    by_sub = by_sub.merge(gross, on="sub_category", how="left").fillna({"gross_loss": 0})
    by_sub = by_sub.sort_values("gross_loss")
    show("LOSSES BY SUB-CATEGORY (gross_loss = sum of all negative profits)", by_sub)
    save_table(by_sub, "losses_by_sub_category.csv")

    top = by_sub.head(10).iloc[::-1]
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(top["sub_category"], top["gross_loss"].abs(), color=RED)
    ax.set_title("Top 10 sub-categories by money lost on loss-making lines")
    ax.set_xlabel("Total loss from loss-making lines (USD)")
    save_chart(fig, "10_gross_loss_by_subcategory.png")

    band = summarise(df, "discount_band").set_index("discount_band").loc[BAND_ORDER].reset_index()
    loss_by_band = losses.groupby("discount_band", observed=True)["profit"].sum().reindex(BAND_ORDER).fillna(0)
    band["share_of_gross_loss_pct"] = (loss_by_band.values / losses["profit"].sum() * 100)
    show("LOSS-MAKING LINES BY DISCOUNT BAND", band[["discount_band", "lines", "loss_lines",
                                                     "loss_line_pct", "share_of_gross_loss_pct"]])
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(band["discount_band"].astype(str), band["loss_line_pct"], color=ORANGE)
    for i, v in enumerate(band["loss_line_pct"]):
        ax.text(i, v, f"{v:.1f}%", ha="center", va="bottom")
    ax.set_title("Share of sales lines that lose money, by discount band")
    ax.set_ylabel("Loss-making lines (%)")
    ax.tick_params(axis="x", rotation=15)
    save_chart(fig, "11_loss_line_share_by_band.png")

    worst = df.nsmallest(10, "profit")[["line_id", "sub_category", "state", "discount",
                                        "sales", "quantity", "profit"]]
    show("10 LARGEST SINGLE-LINE LOSSES", worst)

def analyse_region_by_band(df: pd.DataFrame) -> None:
    section("9. EXTRA: REGION x DISCOUNT BAND")
    grid = df.groupby(["region", "discount_band"], observed=True)[["sales", "profit"]].sum()
    grid["margin_pct"] = grid["profit"] / grid["sales"] * 100
    margin = grid["margin_pct"].unstack("discount_band").reindex(columns=BAND_ORDER)

    counts = (df.groupby(["region", "discount_band"], observed=True).size()
              .unstack("discount_band").reindex(columns=BAND_ORDER))
    share = counts.div(counts.sum(axis=1), axis=0) * 100

    print("\n--- PROFIT MARGIN % BY REGION x DISCOUNT BAND ---")
    print(margin.to_string(float_format=lambda x: f"{x:,.1f}"))
    print("\n--- NUMBER OF LINES ---")
    print(counts.to_string())
    print("\n--- SHARE OF EACH REGION'S LINES IN EACH BAND (%) ---")
    print(share.to_string(float_format=lambda x: f"{x:,.1f}"))
    margin.reset_index().to_csv(TABLE_DIR / "region_discount_margin.csv", index=False)



# ---------------------------------------------------------------
# 5. MAIN
# ---------------------------------------------------------------
def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s", stream=sys.stdout)
    CHART_DIR.mkdir(exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        df = load_clean()
        results = []

        analyse_overall(df)

        section("2. CATEGORY PERFORMANCE")
        results.append(analyse_dimension(df, "category", "category", "01_category.png")[1])

        section("3. SUB-CATEGORY PERFORMANCE")
        results.append(analyse_subcategory(df))

        section("4. REGIONAL AND STATE PERFORMANCE")
        results.append(analyse_dimension(df, "region", "region", "02_region.png")[1])
        results.append(analyse_state(df))

        section("5. CUSTOMER SEGMENTS")
        results.append(analyse_dimension(df, "segment", "segment", "04_segment.png")[1])

        results.append(analyse_discounts(df))
        analyse_region_by_band(df)
        analyse_losses(df)

        section("8. SHIP MODES (modes only: the data has no dates, so no delivery times)")
        results.append(analyse_dimension(df, "ship_mode", "ship mode", "12_ship_mode.png", order=SHIP_ORDER)[1])

        section("SUMMARY")
        logging.info("Reconciliation checks passed: %d of %d", sum(results), len(results))
        logging.info("Charts saved in: %s", CHART_DIR)
        logging.info("Tables saved in: %s", TABLE_DIR)
        return 0 if all(results) else 1
    except Exception:
        logging.exception("EDA failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())