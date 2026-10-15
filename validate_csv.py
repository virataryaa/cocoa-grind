"""Sanity-check Database/cocoa_grind.csv before pushing. Exit code 1 = problems found."""
import sys
from pathlib import Path

import pandas as pd

CSV = Path(__file__).resolve().parent / "Database" / "cocoa_grind.csv"
EXPECTED = ["crop_year", "quarter", "ECA", "CAA", "NCA", "IVC", "BR", "Malaysia", "German"]
problems = []

try:
    d = pd.read_csv(CSV, dtype={"crop_year": str})
except Exception as e:
    print("Cannot read CSV:", e)
    sys.exit(1)

if list(d.columns) != EXPECTED:
    problems.append(f"Columns must be {','.join(EXPECTED)} - found {list(d.columns)}")
else:
    for i, r in d.iterrows():
        if not (isinstance(r.crop_year, str) and len(r.crop_year) == 5 and r.crop_year[2] == "/"):
            problems.append(f"Row {i + 2}: crop_year '{r.crop_year}' must look like 25/26")
        if r.quarter not in ("Q1", "Q2", "Q3", "Q4"):
            problems.append(f"Row {i + 2}: quarter '{r.quarter}' must be Q1..Q4")
    for k in d[d.duplicated(["crop_year", "quarter"])][["crop_year", "quarter"]].itertuples(index=False):
        problems.append(f"Duplicate quarter {k.quarter} | {k.crop_year}")
    for c in EXPECTED[2:]:
        v = pd.to_numeric(d[c], errors="coerce")
        for i in d.index[v.isna() & d[c].notna()]:
            problems.append(f"Row {i + 2}: {c} is not a number ('{d.loc[i, c]}')")
    d["_o"] = d.crop_year.str[:2].astype(int) * 10 + d.quarter.str[1].astype(int)
    d = d.sort_values("_o")
    for c in EXPECTED[2:]:
        s = pd.to_numeric(d[c], errors="coerce")
        jump = (s / s.shift(1) - 1).abs() > 0.25
        jump[jump.index[:-3]] = False                       # history has genuine big moves; check the newest quarters only
        for i in d.index[jump.fillna(False)]:
            problems.append(f"{c} {d.loc[i, 'quarter']} | {d.loc[i, 'crop_year']}: {s[i]:,.0f} moved >25% vs previous quarter")
    origins = d[["ECA", "CAA", "NCA", "IVC", "BR"]]
    part = origins.notna().any(axis=1) & ~origins.notna().all(axis=1)
    for i in d.index[part]:                                 # normal in release week (origins report on different days)
        print(f"Note: {d.loc[i, 'quarter']} | {d.loc[i, 'crop_year']} has only some of ECA/CAA/NCA/IVC/BR - Total shows once all five are in")

if problems:
    print("PROBLEMS FOUND:")
    for p in problems:
        print("  -", p)
    sys.exit(1)

last = d.iloc[-1]
print(f"OK: {len(d)} quarters, latest {last.quarter} | {last.crop_year}")
