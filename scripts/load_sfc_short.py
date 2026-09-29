"""Download SFC aggregated reportable short position CSVs and combine them into one dataset.

Usage (from the project folder):
    py scripts\\load_sfc_short.py              # fetch any missing weeks, rebuild data\\sfc_short_positions.csv
    py scripts\\load_sfc_short.py --latest     # fetch only the newest week
    py scripts\\load_sfc_short.py --since 2024-01-01
    py scripts\\load_sfc_short.py --no-fetch   # rebuild from data\\raw only

Raw weekly files go to data\\raw (SFC filenames, never modified). Output columns:
    date (YYYY-MM-DD), stock_code (5-digit, zero-padded), stock_name, short_shares, short_value_hkd
(short_value_hkd is blank where the SFC reports 'n.a.')
Other scripts can import load() to get the rows as dicts. Stdlib only.
"""
import argparse
import csv
import datetime as dt
import re
import sys
import time
from pathlib import Path

from fetch_sfc_short import BASE, LISTING, get

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
OUT = DATA_DIR / "sfc_short_positions.csv"
FILENAME = "Short_Position_Reporting_Aggregated_Data_{d:%Y%m%d}.csv"
PATTERN = BASE + "/-/media/EN/pdf/spr/{d:%Y}/{d:%m}/{d:%d}/" + FILENAME
SFC_HEADER = ["Date", "Stock Code", "Stock Name",
              "Aggregated Reportable Short Positions (Shares)",
              "Aggregated Reportable Short Positions (HK$)"]
FIELDS = ["date", "stock_code", "stock_name", "short_shares", "short_value_hkd"]


def available():
    """Return {date: url} for every CSV linked from the SFC page (falls back to recent Fridays)."""
    try:
        html = get(LISTING)[0].decode("utf-8", "ignore")
        links = re.findall(r'href="([^"]*Short_Position_Reporting_Aggregated_Data_(\d{8})\.csv[^"]*)"', html)
        if links:
            return {dt.datetime.strptime(ymd, "%Y%m%d").date():
                    (href if href.startswith("http") else BASE + href).replace("&amp;", "&")
                    for href, ymd in links}
    except Exception as e:
        print(f"Listing page failed ({e}); trying recent Fridays by URL pattern...")
    today = dt.date.today()
    friday = today - dt.timedelta(days=(today.weekday() - 4) % 7)
    return {d: PATTERN.format(d=d) for d in (friday - dt.timedelta(weeks=i) for i in range(10))}


def fetch(since=None, latest=False, pause=0.3):
    """Download CSVs not already in data/raw. Returns the number of new files."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    urls = available()
    dates = sorted(d for d in urls if since is None or d >= since)
    if latest:
        dates = dates[-1:]
    new = 0
    for d in dates:
        path = RAW_DIR / FILENAME.format(d=d)
        if path.exists():
            continue
        try:
            body = get(urls[d])[0]
        except Exception as e:
            print(f"  {d}: failed ({e})")
            continue
        if not body.lstrip(b"\xef\xbb\xbf").startswith(b"Date,"):
            print(f"  {d}: not a CSV, skipped")  # e.g. HTML 'not found' page for an unpublished week
            continue
        path.write_bytes(body)
        new += 1
        print(f"  {d}: saved {path.name}")
        time.sleep(pause)
    return new


def to_int(s):
    """'1,234' -> 1234; '$ 5' -> 5; 'n.a.' -> None. A few SFC files have Excel-mangled values
    like '1.18734E+11' (only 6 significant figures survive); those are rounded to an int."""
    s = s.replace(",", "").replace("$", "").strip()
    if s.lower() in ("", "n.a.", "n/a", "na", "-"):
        return None
    return int(s) if s.isdigit() else round(float(s))


def parse(path):
    """Yield clean rows from one SFC weekly CSV."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = [h.strip() for h in next(reader)]
        if header != SFC_HEADER:
            raise ValueError(f"{path.name}: unexpected header {header}")
        for rec in reader:
            if not any(c.strip() for c in rec):
                continue
            date, code, name, shares, value = (c.strip() for c in rec)
            yield {
                "date": dt.datetime.strptime(date, "%d/%m/%Y").date().isoformat(),
                "stock_code": code.zfill(5),
                "stock_name": name,
                "short_shares": to_int(shares),
                "short_value_hkd": to_int(value),
            }


def load(since=None):
    """Return all rows from data/raw, sorted by date then stock code."""
    rows = []
    for path in sorted(RAW_DIR.glob("Short_Position_Reporting_Aggregated_Data_*.csv")):
        rows.extend(r for r in parse(path) if since is None or r["date"] >= since.isoformat())
    return sorted(rows, key=lambda r: (r["date"], r["stock_code"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", type=dt.date.fromisoformat, help="only weeks on/after this date (YYYY-MM-DD)")
    ap.add_argument("--latest", action="store_true", help="fetch only the newest week")
    ap.add_argument("--no-fetch", action="store_true", help="skip downloading; rebuild from data/raw")
    args = ap.parse_args()

    if not args.no_fetch:
        print(f"Fetched {fetch(args.since, args.latest)} new file(s) into {RAW_DIR}")
    rows = load(args.since)
    if not rows:
        sys.exit("No data in " + str(RAW_DIR))
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    weeks = sorted({r["date"] for r in rows})
    print(f"Wrote {len(rows):,} rows, {len(weeks)} weeks ({weeks[0]} to {weeks[-1]}) to {OUT}")


if __name__ == "__main__":
    main()
