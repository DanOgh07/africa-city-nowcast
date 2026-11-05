"""Build the DOSE silver table from the raw v2.14 CSV.

  raw  : data/raw/dose/v2.14/<hash>.csv
  out  : data/interim/dose_silver.csv

Steps
  1. keep only the countries in config/regions.yaml (all units, not just the focus
     cities, so the model can train on every county/state/province/governorate)
  2. assert every region's dose_name still matches its dose_gid1 in the data
  3. compute growth + is_rounded on the FULL history (so 2013 growth can use 2012),
     then keep year >= START_YEAR (the satellite era)
  4. tag focus units with their regions.yaml id

Usage:  python -m nowcast.transforms.dose_silver [--raw PATH] [--out PATH] [--regions PATH]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yaml

from .dose import add_growth

REPO_ROOT = Path(__file__).resolve().parents[3]
START_YEAR = 2013

KEEP_COLUMNS = [
    "region_id", "is_focus", "GID_0", "country", "GID_1", "region", "year",
    "grp_lcu", "pop", "grp_pc_lcu_2015", "deflator_2015", "StructChange",
    "is_rounded", "log_rgrp", "growth", "T_a", "P_a", "start_aggregation_period",
]


def load_regions(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))["regions"]


def check_region_keys(df, regions):
    # Fail loudly if a region's dose_name and dose_gid1 no longer agree with the data.
    problems = []
    for r in regions:
        gid, name = r.get("dose_gid1"), r.get("dose_name")
        if not gid:
            continue
        rows = df[df["GID_1"] == gid]
        if rows.empty:
            problems.append(f"{r['id']}: GID_1 {gid} not found")
        elif name and name not in set(rows["region"].str.strip()):
            problems.append(f"{r['id']}: GID_1 {gid} is {sorted(set(rows['region']))}, expected {name!r}")
    if problems:
        raise ValueError("DOSE key mismatch:\n  " + "\n  ".join(problems))


def build_silver(df, regions, start_year = START_YEAR):
    countries = {r["country_iso3"] for r in regions}
    df = df[df["GID_0"].isin(countries)].copy()
    df["year"] = df["year"].astype(int)

    check_region_keys(df, regions)

    out = add_growth(df)
    out = out[out["year"] >= start_year].copy()

    n_rows = out.groupby("GID_1")["year"].transform("size")
    out = out[n_rows >= 2].copy()   # drop retired-boundary units that only overlap 2013

    focus = {r["dose_gid1"]: r["id"] for r in regions if r.get("dose_gid1")}
    out["region_id"] = out["GID_1"].map(focus)
    out["is_focus"] = out["region_id"].notna()

    keep = [c for c in KEEP_COLUMNS if c in out.columns]
    return out[keep].reset_index(drop=True)


def latest_raw_csv(root):
    files = sorted(root.glob("*.csv"), key=lambda p: p.stat().st_mtime)
    if not files:
        raise FileNotFoundError(f"No raw DOSE CSV under {root}. Run: python -m nowcast.ingestion.dose")
    return files[-1]


def main():
    ap = argparse.ArgumentParser(description="Build DOSE silver table")
    ap.add_argument("--raw", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "data" / "interim" / "dose_silver.csv")
    ap.add_argument("--regions", type=Path, default=REPO_ROOT / "config" / "regions.yaml")
    args = ap.parse_args()

    raw = args.raw or latest_raw_csv(REPO_ROOT / "data" / "raw" / "dose" / "v2.14")
    df = pd.read_csv(raw, encoding="utf-8")
    silver = build_silver(df, load_regions(args.regions))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    silver.to_csv(args.out, index=False, encoding="utf-8")
    print(f"raw: {raw}")
    print(f"wrote {args.out}: {len(silver)} rows, {silver['GID_1'].nunique()} units "
          f"({int(silver.groupby('GID_1')['is_focus'].first().sum())} focus), "
          f"{int(silver['growth'].notna().sum())} usable growth observations")


if __name__ == "__main__":
    main()
