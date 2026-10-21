"""
01_data_quality.py
Purpose: Inspect the raw Superstore CSV (13-column version) without modifying it.
Run from the project root:  python python\01_data_quality.py
"""

from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_FILE = PROJECT_ROOT / "data" / "raw" / "superstore.csv"


def section(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def load_csv(path: Path) -> pd.DataFrame:
    """Try common encodings, since some Superstore files are not UTF-8."""
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            df = pd.read_csv(path, encoding=enc)
            print(f"Loaded successfully with encoding: {enc}")
            return df
        except UnicodeDecodeError:
            print(f"Encoding {enc} failed, trying next...")
    raise ValueError("Could not read the file with any common encoding.")


def main() -> None:
    if not RAW_FILE.exists():
        print(f"ERROR: File not found: {RAW_FILE}")
        return

    df = load_csv(RAW_FILE)

    section("SHAPE (rows, columns)")
    print(df.shape)

    section("DATA TYPES AS LOADED")
    print(df.dtypes.to_string())

    section("MISSING VALUES PER COLUMN")
    print(df.isna().sum().to_string())

    section("DUPLICATE ROWS")
    dup_mask = df.duplicated(keep=False)
    print(f"Rows involved in exact duplication (all copies): {dup_mask.sum()}")
    print(f"Extra copies (rows that repeat an earlier row): {df.duplicated().sum()}")
    print("\nSample of duplicated rows:")
    with pd.option_context("display.max_columns", None, "display.width", 200):
        print(df[dup_mask].sort_values(list(df.columns)).head(10).to_string())
    print("\nNOTE: There is no Order ID, so identical rows may be genuine "
          "repeat sales. We keep them and document this decision.")

    section("NUMERIC COLUMNS")
    num_cols = ["Sales", "Quantity", "Discount", "Profit"]
    for col in num_cols:
        s = df[col]
        print(f"{col:<9} min={s.min():>12,.4f}  max={s.max():>12,.4f}  "
              f"zeros={(s == 0).sum():>5}  negatives={(s < 0).sum():>5}")

    section("DISCOUNT: DISTINCT VALUES")
    print(df["Discount"].value_counts().sort_index().to_string())

    section("POSTAL CODE CHECK")
    pc = df["Postal Code"].astype(str)
    print(f"Dtype as loaded: {df['Postal Code'].dtype}")
    print(f"Codes with fewer than 5 digits (lost leading zero): {(pc.str.len() < 5).sum()}")

    section("CATEGORICAL COLUMNS: UNIQUE COUNTS")
    text_cols = df.select_dtypes(include=["object", "string"]).columns
    for col in text_cols:
        print(f"{col}: {df[col].nunique()} unique")

    section("VALUES OF LOW-CARDINALITY COLUMNS (<= 20 unique)")
    for col in text_cols:
        if df[col].nunique() <= 20:
            print(f"\n{col}:")
            print(df[col].value_counts(dropna=False).to_string())

    section("WHITESPACE / CASING CHECK ON TEXT COLUMNS")
    for col in text_cols:
        stripped = df[col].str.strip()
        n_ws = (df[col] != stripped).sum()
        print(f"{col}: {n_ws} values with leading/trailing spaces")

    section("RAW TOTALS (to reconcile with Excel, SQL and Power BI later)")
    print(f"Row count:      {len(df):,}")
    print(f"Sum of Sales:   {df['Sales'].sum():,.4f}")
    print(f"Sum of Profit:  {df['Profit'].sum():,.4f}")
    print(f"Sum of Quantity:{df['Quantity'].sum():,}")

    print("\nInspection finished. No data was modified.")


if __name__ == "__main__":
    main()