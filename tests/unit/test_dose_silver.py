import numpy as np
import pandas as pd
import pytest

from nowcast.transforms.dose_silver import build_silver, check_region_keys

REGIONS = [
    {"id": "KEN-nairobi", "country_iso3": "KEN", "dose_name": "Nairobi", "dose_gid1": "KEN.30_1"},
    {"id": "NGA-lagos", "country_iso3": "NGA", "dose_name": None, "dose_gid1": None},
]


def raw_frame():
    rows = []
    for gid, name, iso, country in [
        ("KEN.30_1", "Nairobi", "KEN", "Kenya"),
        ("KEN.1_1", "Baringo", "KEN", "Kenya"),
        ("NGA.33_1", "Rivers", "NGA", "Nigeria"),
        ("BRA.1_1", "Acre", "BRA", "Brazil"),
    ]:
        for year, level in [(2012, 100.0), (2013, 102.0), (2014, 104.0)]:
            rows.append({
                "GID_0": iso, "country": country, "GID_1": gid, "region": name,
                "year": year, "grp_lcu": 1234567.0, "pop": 1000.0,
                "grp_pc_lcu_2015": level, "deflator_2015": 100.0,
                "StructChange": 3.0 if (gid == "KEN.30_1" and year == 2013) else 0.0,
            })
    return pd.DataFrame(rows)


def test_filters_countries_years_and_tags_focus():
    out = build_silver(raw_frame(), REGIONS)
    assert set(out["GID_0"]) == {"KEN", "NGA"}               # Brazil dropped
    assert out["year"].min() == 2013                          # 2012 dropped
    focus = out[out["is_focus"]]
    assert set(focus["region_id"]) == {"KEN-nairobi"}
    assert set(out[~out["is_focus"]]["region_id"].dropna()) == set()


def test_growth_uses_2012_but_blanks_flagged_year():
    out = build_silver(raw_frame(), REGIONS).set_index(["GID_1", "year"])["growth"]
    assert out[("NGA.33_1", 2013)] == pytest.approx(np.log(102 / 100))   # 2012 available
    assert np.isnan(out[("KEN.30_1", 2013)])                             # StructChange=3
    assert out[("KEN.30_1", 2014)] == pytest.approx(np.log(104 / 102))


def test_key_mismatch_raises():
    bad = [{"id": "KEN-nairobi", "country_iso3": "KEN", "dose_name": "Mombasa", "dose_gid1": "KEN.30_1"}]
    with pytest.raises(ValueError, match="KEN.30_1"):
        check_region_keys(raw_frame(), bad)


def test_missing_gid_raises():
    bad = [{"id": "KEN-x", "country_iso3": "KEN", "dose_name": "X", "dose_gid1": "KEN.99_1"}]
    with pytest.raises(ValueError, match="not found"):
        check_region_keys(raw_frame(), bad)


def test_null_gid_regions_are_skipped():
    check_region_keys(raw_frame(), [REGIONS[1]])             # Lagos has no DOSE id: no error


def test_single_row_units_dropped():
    df = raw_frame()
    extra = {"GID_0": "KEN", "country": "Kenya", "GID_1": "KEN.99_1", "region": "Old",
             "year": 2013, "grp_lcu": 1234567.0, "pop": 1000.0,
             "grp_pc_lcu_2015": 100.0, "deflator_2015": 100.0, "StructChange": 0.0}
    out = build_silver(pd.concat([df, pd.DataFrame([extra])], ignore_index=True), REGIONS)
    assert "KEN.99_1" not in set(out["GID_1"])