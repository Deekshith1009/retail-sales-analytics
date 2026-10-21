"""
02_data_cleaning.py
Purpose: Clean the raw Superstore CSV and save a processed copy.
Run from the project root:  python python\\02_data_cleaning.py

The raw file in data/raw is NEVER modified.
Output: data/processed/superstore_clean.csv and data/processed/cleaning_log.txt
"""

import logging
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------
# 1. SETTINGS: file locations and the baseline from Phase 1
# ---------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_FILE = PROJECT_ROOT / "data" / "raw" / "superstore.csv"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CLEAN_FILE = PROCESSED_DIR / "superstore_clean.csv"
LOG_FILE = PROCESSED_DIR / "cleaning_log.txt"

# Numbers recorded in Phase 1 (and matched in Excel).
BASELINE = {
    "rows": 9994,
    "sales": 2297200.8603,
    "profit": 286397.0217,
    "quantity": 37873,
    "loss_lines": 1871,
}

EXPECTED_COLUMNS = [
    "Ship Mode", "Segment", "Country", "City", "State", "Postal Code",
    "Region", "Category", "Sub-Category", "Sales", "Quantity",
    "Discount", "Profit",
]


def setup_logging() -> None:
    """Send log messages to both the screen and a text file."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


# ---------------------------------------------------------------
# 2. LOAD the raw file (read-only)
# ---------------------------------------------------------------
def load_raw() -> pd.DataFrame:
    if not RAW_FILE.exists():
        raise FileNotFoundError(f"Raw file not found: {RAW_FILE}")

    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            # Postal Code is read as TEXT so no digits are lost or changed.
            df = pd.read_csv(RAW_FILE, encoding=enc, dtype={"Postal Code": str})
            logging.info("Loaded raw file with encoding %s: %d rows, %d columns",
                         enc, df.shape[0], df.shape[1])
            break
        except UnicodeDecodeError:
            logging.warning("Encoding %s failed, trying the next one", enc)
    else:
        raise ValueError("Could not read the file with any common encoding.")

    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Expected columns are missing from the file: {missing}")
    return df


# ---------------------------------------------------------------
# 3. CLEAN
# ---------------------------------------------------------------
def standardise_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """'Sub-Category' -> 'sub_category', 'Postal Code' -> 'postal_code'."""
    df = df.copy()
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(r"[\s\-]+", "_", regex=True)
    )
    logging.info("Column names standardised: %s", list(df.columns))
    return df


def strip_text_whitespace(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    text_cols = df.select_dtypes(include=["object", "string"]).columns
    for col in text_cols:
        cleaned = df[col].str.strip()
        n_changed = int((df[col] != cleaned).sum())
        if n_changed:
            logging.info("Stripped spaces in %s: %d values changed", col, n_changed)
        df[col] = cleaned
    return df


def fix_postal_codes(df: pd.DataFrame) -> pd.DataFrame:
    """Pad postal codes to 5 digits (e.g. 1040 -> 01040)."""
    df = df.copy()
    short_before = int((df["postal_code"].str.len() < 5).sum())
    df["postal_code"] = df["postal_code"].str.zfill(5)
    bad = int((~df["postal_code"].str.fullmatch(r"\d{5}")).sum())
    logging.info("Postal codes padded to 5 digits: %d fixed, %d still invalid",
                 short_before, bad)
    if bad:
        logging.warning("Some postal codes are not 5 digits. Inspect them manually.")
    return df


def convert_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ["sales", "quantity", "discount", "profit"]:
        converted = pd.to_numeric(df[col], errors="coerce")
        new_nulls = int(converted.isna().sum() - df[col].isna().sum())
        if new_nulls:
            raise ValueError(f"{col}: {new_nulls} values could not be read as numbers.")
        df[col] = converted
    df["quantity"] = df["quantity"].astype(int)
    logging.info("Numeric columns converted. dtypes: %s",
                 df[["sales", "quantity", "discount", "profit"]].dtypes.astype(str).to_dict())
    return df


def validate_values(df: pd.DataFrame) -> None:
    """Report impossible values. This only checks; it never deletes rows."""
    logging.info("Missing values in the whole table: %d", int(df.isna().sum().sum()))
    logging.info("Rows with Sales <= 0: %d", int((df["sales"] <= 0).sum()))
    logging.info("Rows with Quantity < 1: %d", int((df["quantity"] < 1).sum()))
    logging.info("Rows with Discount outside 0 to 1: %d",
                 int(((df["discount"] < 0) | (df["discount"] > 1)).sum()))
    logging.info("Negative-profit rows (KEPT, real losses): %d", int((df["profit"] < 0).sum()))
    logging.info("Zero-profit rows (KEPT): %d", int((df["profit"] == 0).sum()))
    states = sorted(df["state"].unique())
    logging.info("Distinct states: %d -> %s", len(states), states)


def document_duplicates(df: pd.DataFrame) -> None:
    """Count identical rows but do NOT remove them."""
    extra = int(df.duplicated().sum())
    dup_sales = df.loc[df.duplicated(), "sales"].sum()
    share = dup_sales / df["sales"].sum()
    logging.info("Identical rows (extra copies): %d. KEPT because there is no Order ID.", extra)
    logging.info("Sales in those extra copies: %.2f (%.3f%% of total sales)", dup_sales, share * 100)


# ---------------------------------------------------------------
# 4. ADD helper columns (same logic as the Excel columns)
# ---------------------------------------------------------------
def add_helper_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Unique row number based on original file order (NOT an Order ID).
    df.insert(0, "line_id", np.arange(1, len(df) + 1))

    df["loss_flag"] = (df["profit"] < 0).astype(int)

    conditions = [
        df["discount"] == 0,
        df["discount"] <= 0.20,
        df["discount"] <= 0.40,
    ]
    labels = ["No Discount", "Low (1-20%)", "Medium (21-40%)"]
    df["discount_band"] = np.select(conditions, labels, default="High (>40%)")

    # Row-level margin. For group margins ALWAYS use sum(profit) / sum(sales).
    df["profit_margin"] = (df["profit"] / df["sales"]).round(4)

    logging.info("Helper columns added: line_id, loss_flag, discount_band, profit_margin")
    logging.info("Discount band counts: %s", df["discount_band"].value_counts().to_dict())
    return df


# ---------------------------------------------------------------
# 5. RECONCILE with the Phase 1 baseline
# ---------------------------------------------------------------
def run_baseline_checks(df: pd.DataFrame) -> bool:
    checks = [
        ("Row count", len(df), BASELINE["rows"]),
        ("Total Sales", df["sales"].sum(), BASELINE["sales"]),
        ("Total Profit", df["profit"].sum(), BASELINE["profit"]),
        ("Total Quantity", int(df["quantity"].sum()), BASELINE["quantity"]),
        ("Loss-making lines", int(df["loss_flag"].sum()), BASELINE["loss_lines"]),
    ]
    all_ok = True
    for name, actual, expected in checks:
        ok = math.isclose(actual, expected, abs_tol=0.01)
        logging.info("%-18s actual=%-16s expected=%-16s %s",
                     name, f"{actual:,.4f}", f"{expected:,.4f}", "PASS" if ok else "FAIL")
        all_ok = all_ok and ok
    return all_ok


# ---------------------------------------------------------------
# 6. SAVE and verify the saved file
# ---------------------------------------------------------------
def save_and_verify(df: pd.DataFrame) -> bool:
    df.to_csv(CLEAN_FILE, index=False, encoding="utf-8")
    logging.info("Saved cleaned file: %s", CLEAN_FILE)

    reloaded = pd.read_csv(CLEAN_FILE, dtype={"postal_code": str})
    ok = (
        reloaded.shape == df.shape
        and math.isclose(reloaded["sales"].sum(), df["sales"].sum(), abs_tol=0.01)
        and math.isclose(reloaded["profit"].sum(), df["profit"].sum(), abs_tol=0.01)
        and bool(reloaded["postal_code"].str.fullmatch(r"\d{5}").all())
    )
    logging.info("Reload check (shape, totals, postal codes): %s", "PASS" if ok else "FAIL")
    return ok


def main() -> int:
    setup_logging()
    logging.info("=== Cleaning started ===")
    try:
        df = load_raw()
        df = standardise_column_names(df)
        df = strip_text_whitespace(df)
        df = fix_postal_codes(df)
        df = convert_numeric_columns(df)
        validate_values(df)
        document_duplicates(df)
        df = add_helper_columns(df)

        baseline_ok = run_baseline_checks(df)
        if not baseline_ok:
            logging.error("Baseline mismatch. The cleaned file was NOT saved.")
            return 1

        if not save_and_verify(df):
            logging.error("Saved file failed verification.")
            return 1
    except Exception:
        logging.exception("Cleaning failed")
        return 1

    logging.info("=== Cleaning finished successfully ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())