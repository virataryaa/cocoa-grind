"""One-off history load: Raw/Cocoa Grindings Outlook (Crop Year).xlsx -> Database/cocoa_grind.csv.

Sheets used: ECA, CAA, NCA, IVC, BR, German (column C) and MCB (Malaysia). Quarters are Oct-Sep crop years (Q1 = Oct-Dec).
Only reported figures are loaded; the workbook's estimates and placeholders are skipped (see reported()).
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
    wf = openpyxl.load_workbook(tmp, data_only=False)          # formulas + fonts, to tell reported figures from estimates
    rows = {}

    def reported(cell, value):
        """Reported figure: a typed number, a pure cell reference, or constant-only arithmetic (manual adjustment).
        Not: red font (placeholder, e.g. Q1 16/17 copied from Q2) or formulas on other cells (=R15*(1+C4): estimates)."""
        f, col = cell.value, cell.font.color if cell.font else None
        if col is not None and col.type == "rgb" and col.rgb == "FFC00000":
            return False
        if isinstance(f, str):
            return bool(re.fullmatch(r"=('?[\w ]+'?!)?\$?[A-Z]+\$?\d+", f) or re.fullmatch(r"=[\d+\-*/. ()]+", f))
        return isinstance(value, (int, float))

    def put(sheet, name, label_col=2, value_col=3):            # 1-based columns; region sheets: B = quarter, C = grind
        vs, fs = wb[sheet], wf[sheet]
        for r in range(1, vs.max_row + 1):
            k = qkey(vs.cell(r, label_col).value)
            v = vs.cell(r, value_col).value
            if k and isinstance(v, (int, float)) and reported(fs.cell(r, value_col), v):
                rows.setdefault(k, {}).setdefault(name, round(v))

    for o in ["ECA", "CAA", "NCA", "IVC", "BR", "German"]:
        put(o, o)
    put("Malaysia", "Malaysia")                                # MCB figures as linked/typed in the sheet (incl. revisions)
    for c, v in wb["MCB"].iter_rows(min_col=3, max_col=4, values_only=True):   # raw MCB list, calendar 'Q4-16' labels
        m = re.fullmatch(r"Q([1-4])-(\d\d)", str(c or "").strip())
        if m and isinstance(v, (int, float)):
            q, y = int(m.group(1)), int(m.group(2))
            k = (f"{y:02d}/{y + 1:02d}", "Q1") if q == 4 else (f"{y - 1:02d}/{y:02d}", f"Q{q + 1}")
            if k[0] >= "16/17":
                rows.setdefault(k, {}).setdefault("Malaysia", round(v))   # fills quarters the sheet only estimates

    df = pd.DataFrame([{"crop_year": k[0], "quarter": k[1], **v} for k, v in rows.items()])
    df["_o"] = df.crop_year.str[:2].astype(int) * 10 + df.quarter.str[1].astype(int)
    df = df.sort_values("_o").drop(columns="_o").reindex(columns=["crop_year", "quarter", *COLS])
    df[COLS] = df[COLS].astype("Int64")
    df.to_csv(OUT, index=False, lineterminator="\n")
    print(f"Wrote {len(df)} rows -> {OUT}")


if __name__ == "__main__":
    main()
