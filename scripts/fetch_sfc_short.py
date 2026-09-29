"""Download the most recent SFC aggregated reportable short positions PDF into ../data.

Usage (from the project folder):  py scripts\\fetch_sfc_short.py
Stdlib only. Positions are as at each Friday; the SFC publishes them about a week later.
"""
import datetime as dt
import re
import sys
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
BASE = "https://www.sfc.hk"
LISTING = (BASE + "/en/Regulatory-functions/Market/Short-position-reporting/"
           "Aggregated-reportable-short-positions-of-specified-shares")
PATTERN = BASE + "/-/media/EN/pdf/spr/{d:%Y}/{d:%m}/{d:%d}/Short_Position_Reporting_Aggregated_Data_Eng_{d:%Y%m%d}.pdf"
HEADERS = {"User-Agent": "Mozilla/5.0 (hk-short-tracker)"}


def get(url, timeout=30):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers.get("Content-Type", "")


def from_listing():
    """Scrape the SFC page for PDF links; return (date, url) of the newest."""
    html, _ = get(LISTING)
    links = set(re.findall(r'href="([^"]*Short_Position_Reporting_Aggregated_Data_Eng_(\d{8})\.pdf[^"]*)"',
                           html.decode("utf-8", "ignore"), re.I))
    if not links:
        return None
    href, ymd = max(links, key=lambda x: x[1])
    href = href.replace("&amp;", "&")
    return dt.datetime.strptime(ymd, "%Y%m%d").date(), (href if href.startswith("http") else BASE + href)


def from_pattern(weeks=10):
    """Walk back through recent Fridays and try the known URL pattern."""
    today = dt.date.today()
    friday = today - dt.timedelta(days=(today.weekday() - 4) % 7)
    for i in range(weeks):
        d = friday - dt.timedelta(weeks=i)
        url = PATTERN.format(d=d)
        try:
            body, ctype = get(url)
            if body[:4] == b"%PDF":
                return d, url, body
        except Exception:
            pass
    return None


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    body = None
    try:
        found = from_listing()
        if found:
            d, url = found
            body, _ = get(url)
            if body[:4] != b"%PDF":
                body = None
    except Exception as e:
        print(f"Listing page failed ({e}); trying URL pattern...")
    if body is None:
        found = from_pattern()
        if not found:
            sys.exit("No PDF found in the last 10 weeks. Check " + LISTING)
        d, url, body = found
    out = DATA_DIR / f"Short_Position_Reporting_Aggregated_Data_{d:%Y%m%d}.pdf"
    if out.exists() and out.stat().st_size == len(body):
        print(f"Already have {out.name}")
    else:
        out.write_bytes(body)
        print(f"Saved {out.name} ({len(body)/1024:.0f} KB) from {url}")


if __name__ == "__main__":
    main()
