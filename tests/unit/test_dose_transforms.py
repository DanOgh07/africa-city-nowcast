import numpy as np
import pandas as pd
import pytest

from nowcast.transforms.dose import add_growth, flag_rounded, sig_digits


@pytest.mark.parametrize("value, expected", [
    (9.92e11, 3),
    (1.30e12, 2),
    (1.0e12, 1),
    (1234567.0, 7),
    (0.0, 0),
    (float("nan"), 0),
])
def test_sig_digits(value, expected):
    assert sig_digits(value) == expected


def test_flag_rounded_ignores_nan_and_full_precision():
    df = pd.DataFrame({"grp_lcu": [9.92e11, 1234567.0, np.nan]})
    assert flag_rounded(df).tolist() == [True, False, False]


def _frame():
    return pd.DataFrame({
        "GID_0": ["ZAF"] * 4 + ["KEN"] * 4,
        "GID_1": ["ZAF.3_1"] * 4 + ["KEN.30_1"] * 4,
        "year": [2013, 2014, 2015, 2016, 2013, 2014, 2016, 2017],
        "grp_lcu": [9.92e11, 1.08e12, 1.30e12, 1.38e12, 1234567.0, 1234568.0, 1234569.0, 1234570.0],
        "grp_pc_lcu_2015": [100.0, 110.0, 111.0, 112.0, 50.0, 51.0, 52.0, 53.0],
        "StructChange": [0, 3, 0, 0, 3, 0, 0, 0],
    })


def test_growth_blanks_breaks_gaps_and_first_years():
    out = add_growth(_frame())
    g = out.set_index(["GID_1", "year"])["growth"]

    assert np.isnan(g[("ZAF.3_1", 2013)])                  # first year
    assert np.isnan(g[("ZAF.3_1", 2014)])                  # known break + StructChange=3
    assert g[("ZAF.3_1", 2015)] == pytest.approx(np.log(111 / 110))
    assert g[("ZAF.3_1", 2016)] == pytest.approx(np.log(112 / 111))

    assert np.isnan(g[("KEN.30_1", 2013)])                 # first year (flag 3 irrelevant)
    assert g[("KEN.30_1", 2014)] == pytest.approx(np.log(51 / 50))
    assert np.isnan(g[("KEN.30_1", 2016)])                 # 2015 missing -> gap
    assert g[("KEN.30_1", 2017)] == pytest.approx(np.log(53 / 52))


def test_is_rounded_added():
    out = add_growth(_frame())
    zaf = out[out["GID_0"] == "ZAF"]["is_rounded"]
    ken = out[out["GID_0"] == "KEN"]["is_rounded"]
    assert zaf.all() and not ken.any()