"""Silver-layer helpers for DOSE v2.14 ground truth.

Rules encoded here (see docs/data_sources.md, "DOSE processing rules"):
  * join on GID_1, never on region name
  * target = log growth of real per-capita GRP (grp_pc_lcu_2015), never nominal
  * growth is blank where the previous year is missing, where StructChange > 0
    (1 = new source, 2 = boundary change, 3 = extended vs prior DOSE version;
    a 3 coincided with a real break in South Africa 2014, so all are treated as
    breaks), and for hard-coded known breaks
  * rows whose GRP has <= 3 significant digits are flagged `is_rounded`
"""
from __future__ import annotations

import numpy as np
import pandas as pd

#: (GID_0, year) pairs where growth INTO that year is invalid regardless of flags.
KNOWN_BREAKS: set[tuple[str, int]] = {("ZAF", 2014)}

ROUNDED_MAX_SIG_DIGITS = 3


def sig_digits(value):
    # Significant digits in a number, ignoring trailing zeros. NaN/0 -> 0.
    if value is None or not np.isfinite(value) or value == 0:
        return 0
    mantissa = f"{abs(value):.6e}".split("e")[0]
    return len(mantissa.replace(".", "").rstrip("0")) or 1


def flag_rounded(df, col = "grp_lcu"):
    # True where the value has at most ROUNDED_MAX_SIG_DIGITS significant digits.
    s = df[col].map(sig_digits)
    return (s > 0) & (s <= ROUNDED_MAX_SIG_DIGITS)


def add_growth(df, key = "GID_1", level_col = "grp_pc_lcu_2015"):
    # Return a copy sorted by (key, year) with `is_rounded`, `log_rgrp`, `growth`.
    out = df.sort_values([key, "year"]).copy()
    out["is_rounded"] = flag_rounded(out)
    out["log_rgrp"] = np.log(out[level_col].where(out[level_col] > 0))

    grouped = out.groupby(key)
    out["growth"] = grouped["log_rgrp"].diff()

    gap = grouped["year"].diff() != 1                      # first row or skipped year
    broken = out["StructChange"].fillna(0) > 0
    known = pd.Series(
        [(c, int(y)) in KNOWN_BREAKS for c, y in zip(out["GID_0"], out["year"])],
        index=out.index,
    )
    out.loc[gap | broken | known, "growth"] = np.nan
    return out
