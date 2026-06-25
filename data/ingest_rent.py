"""Build data/rent.db: NSW median rents + postcode centroids (for the map).

Sources (both CC-BY):
  - NSW DCJ Rent and Sales Report  -> median rent by postcode/dwelling/bedrooms
  - matthewproctor/australianpostcodes -> postcode -> lat/lon centroid

Run:  python data/ingest_rent.py
"""
import io
import sqlite3
from pathlib import Path

import pandas as pd
import requests

# DCJ blocks urllib's default agent (403); a browser UA fetches fine.
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

RENT_URL = (
    "https://dcj.nsw.gov.au/documents/about-us/families-and-communities-statistics/"
    "housing-and-rent-sales/rent-tables-march-2026-quarter.xlsx"
)
QUARTER = "2026-Q1"  # Jan-Mar 2026 (stated in the file's header text, not a column)
CENTROID_URL = (
    "https://raw.githubusercontent.com/matthewproctor/australianpostcodes/master/"
    "australian_postcodes.csv"
)
DB = Path(__file__).resolve().parent / "rent.db"


def _col(df, needle):
    """First column whose header contains needle (column order disambiguates)."""
    return next(c for c in df.columns if needle.lower() in str(c).lower())


def build_rent(con):
    print(f"Downloading rent data ...")
    resp = requests.get(RENT_URL, headers=_HEADERS, timeout=60)
    resp.raise_for_status()
    df = pd.read_excel(io.BytesIO(resp.content), sheet_name="Postcode", header=8, engine="openpyxl")

    rename = {
        _col(df, "postcode"): "postcode",
        _col(df, "dwelling types"): "dwelling_type",
        _col(df, "number of bedrooms"): "bedrooms",
        _col(df, "first quartile"): "q1_rent",
        _col(df, "median weekly rent"): "median_rent",   # col E precedes the "change" cols
        _col(df, "third quartile"): "q3_rent",
        _col(df, "new bonds lodged"): "new_bonds",        # col G precedes "change in new bonds"
    }
    df = df.rename(columns=rename)[list(rename.values())]

    df = df[df["postcode"].astype(str).str.match(r"^\d{4}")].copy()
    df["postcode"] = df["postcode"].astype(float).astype(int)
    df["dwelling_type"] = df["dwelling_type"].astype(str).str.strip()
    df["bedrooms"] = df["bedrooms"].astype(str).str.strip()
    for c in ["q1_rent", "median_rent", "q3_rent", "new_bonds"]:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", "", regex=False), errors="coerce")
    df["quarter"] = QUARTER

    con.execute("DROP TABLE IF EXISTS median_rent")
    df.to_sql("median_rent", con, if_exists="append", index=False)
    con.execute("CREATE INDEX ix_lookup ON median_rent(postcode, bedrooms, dwelling_type, quarter)")
    con.commit()
    n = con.execute("SELECT COUNT(*) FROM median_rent WHERE median_rent IS NOT NULL").fetchone()[0]
    pcs = con.execute("SELECT COUNT(DISTINCT postcode) FROM median_rent").fetchone()[0]
    print(f"  -> median_rent: {n} priced rows across {pcs} postcodes ({QUARTER})")


def build_centroids(con):
    print("Downloading postcode centroids ...")
    resp = requests.get(CENTROID_URL, headers=_HEADERS, timeout=120)
    resp.raise_for_status()
    df = pd.read_csv(io.BytesIO(resp.content), dtype={"postcode": str}, low_memory=False)

    nsw = df[df["state"] == "NSW"].copy()
    nsw["lat"] = pd.to_numeric(nsw["lat"], errors="coerce")
    nsw["long"] = pd.to_numeric(nsw["long"], errors="coerce")
    nsw = nsw[nsw["lat"].notna() & nsw["long"].notna() & (nsw["lat"] != 0) & (nsw["long"] != 0)]

    cen = nsw.groupby("postcode").agg(lat=("lat", "mean"), lon=("long", "mean")).reset_index()
    cen["postcode"] = pd.to_numeric(cen["postcode"], errors="coerce")
    cen = cen.dropna(subset=["postcode"])
    cen["postcode"] = cen["postcode"].astype(int)

    con.execute("DROP TABLE IF EXISTS postcode_centroid")
    cen[["postcode", "lat", "lon"]].to_sql("postcode_centroid", con, if_exists="append", index=False)
    con.execute("CREATE INDEX ix_centroid ON postcode_centroid(postcode)")
    con.commit()
    print(f"  -> postcode_centroid: {len(cen)} NSW postcodes")


def main():
    con = sqlite3.connect(DB)
    try:
        build_rent(con)
        build_centroids(con)
    finally:
        con.close()
    print(f"Done -> {DB}")


if __name__ == "__main__":
    main()
