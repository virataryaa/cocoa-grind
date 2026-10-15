"""One-off history load: Raw/Cocoa Grindings Outlook (Crop Year).xlsx -> Database/cocoa_grind.csv.

Sheets used: TOTAL (ECA, CAA, NCA, IVC, BR), Malaysia, German. Quarters are Oct-Sep crop years (Q1 = Oct-Dec).
After this, new quarters are entered in the dashboard (Entry page), which writes the CSV on GitHub.
Refuses to overwrite an existing CSV unless --force (that would drop dashboard entries).
"""
import re
import shutil
import sys
import tempfile
import warnings
from pathlib import Path

import openpyxl
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
XLSX = ROOT / "Raw" / "Cocoa Grindings Outlook (Crop Year).xlsx"
OUT = ROOT / "Database" / "cocoa_grind.csv"
COLS = ["ECA", "CAA", "NCA", "IVC", "BR", "Malaysia", "German"]


def qkey(label):
    m = re.match(r"\s*Q([1-4])\s*\|\s*(\d\d/\d\d)\s*$", str(label or ""))    # 'Q2 |24/25' and 'Q4| 24/25' also occur
    return (m.group(2), f"Q{m.group(1)}") if m else None


def main():
    if OUT.exists() and "--force" not in sys.argv:
        sys.exit(f"{OUT.name} already exists - not overwriting (use --force to rebuild from Excel).")
    tmp = Path(tempfile.mkdtemp()) / "cg.xlsx"
    shutil.copy2(XLSX, tmp)                                  # the workbook is often open/locked
    wb = openpyxl.load_workbook(tmp, data_only=True)
    rows = {}

    def put(sheet, names, first_col):
        for r in wb[sheet].iter_rows(values_only=True):
            k = qkey(r[1])
            if not k:
                continue
            for i, n in enumerate(names):
                v = r[first_col + i]
                if isinstance(v, (int, float)):
                    rows.setdefault(k, {})[n] = round(v)

    put("TOTAL", ["ECA", "CAA", "NCA", "IVC", "BR"], 3)      # B=Quarter, C=Total (recomputed), D..H = origins
    put("Malaysia", ["Malaysia"], 2)
    put("German", ["German"], 2)

    df = pd.DataFrame([{"crop_year": k[0], "quarter": k[1], **v} for k, v in rows.items()])
    df["_o"] = df.crop_year.str[:2].astype(int) * 10 + df.quarter.str[1].astype(int)
    df = df.sort_values("_o").drop(columns="_o").reindex(columns=["crop_year", "quarter", *COLS])
    df[COLS] = df[COLS].astype("Int64")
    df.to_csv(OUT, index=False, lineterminator="\n")
    print(f"Wrote {len(df)} rows -> {OUT}")


if __name__ == "__main__":
    main()
