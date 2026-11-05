# Data sources

## Ground truth (target variable)

| Source | Country | Unit | Cadence | Status | Notes |
|---|---|---|---|---|---|
| KNBS Gross County Product | Kenya | 47 counties | Annual | Confirmed | Reports 2019, 2021, 2023, 2024; verify exact year coverage per report |
| HCP regional accounts | Morocco | 12 regions | Annual | Confirmed | Latest release covers 2024; regions include rural areas |
| MPED GDP by governorate | Egypt | Governorates | Annual | Provisional (DOSE) | DOSE v2.14 gives 2013-2019 for all 27 governorates; MPED portal only needed for years after 2019. DOSE v2.14 years follow fiscal-year-ending convention (FY Jul-Jun labeled by end year, e.g. 2013 = Jul 2012-Jun 2013). Aggregate features over Jul-Jun for Egypt. |
| Stats SA provincial GDP | South Africa | 9 provinces | Annual | Confirmed | 2013-2023 seen; series paused ~2 years then re-released (check consistency) |
| NBS state GDP | Nigeria | States | Annual | Patchy | 22 states for 2013-2017 seen; sector-by-state tables exist for 2023, but unconfirmed whether they sum to total state GDP or how many years/what base year. See audit |
| NBS state IGR | Nigeria | 36 states + FCT | Annual | Confirmed (2021-2024) | Fiscal proxy, not GDP |
| Lagos Bureau of Statistics (LEDU) | Nigeria | Lagos only | Quarterly | Confirmed | State-government estimate; methodology differs from NBS |
| DOSE (Zenodo) | Global | Sub-national | Annual | Primary for Egypt/Nigeria, cross-check elsewhere | Version pinned: v2.14 (Zenodo 20035157, DOI 10.5281/zenodo.20035157, 1953-2019, 1,667 regions). Kenya: 47 counties 2013-2017 (the 48th region, "South Nyanza", is a retired district, 1966-1999: exclude); pre-2013 Kenya is a different measure (labor earnings), do not extend backward. Morocco: new 12-region map 2013-2019 (2013 = first year, StructChange=2); the former region map (2007-2013) has separate GID_1s, never pool; verify 2013 new-region values vs HCP (may be back-cast). Egypt: 27 governorates, 2013-2019, full precision. South Africa: 2013-2016; all provinces step up uniformly in 2014 (9-province total +19.6% vs +8.2/+6.4/+7.7% in neighboring years; provincial shares stable, so a level shift between source releases, not an allocation splice): growth into 2014 is a break. Nigeria: 22 states 2013-2017 (FCT and Rivers; no Lagos). Rounding varies by country: see Open questions. Use real per-capita columns (grp_pc_lcu_2015), not nominal. See "DOSE processing rules" below. T_a/P_a are area-weighted ERA5 annual values (Egypt: fiscal-year window; see start_aggregation_period). |
| Ghana GSS regional GDP | Ghana | Regions | -- | Excluded | Not published until after rebasing |

## Open questions (Phase 0)

- [ ] Nigeria: which states have a usable multi-year series? Any state-level proxy (IGR, electricity, VAT)?
- [ ] Egypt: year range on the MPED portal
- [x] DOSE: which of our units appear?
- [ ] Boundary source: GADM vs geoBoundaries (write ADR 0002). Note: the DOSE paper lists Morocco among countries whose regions do not match GADM 3.6; DOSE ships its own boundary file for them
- [ ] Nigeria: do 2023 NBS sector-by-state tables sum to total state GDP? Which base year? 2018-2022 available?
- [x] Kenya/Egypt: which years are missing inside DOSE's ranges? (v2.14: none missing from 2013 for our units; Kenya 2013-2017, Egypt 2013-2019)
- [x] Kenya: DOSE v2.14 has 48 regions; extra is "South Nyanza" (1966-1999), irrelevant
- [ ] Morocco: compare DOSE 2013 values for new regions against HCP.
- [x] Check StructChange rows within our units (Egypt=1 in 2013; Kenya=3 in 2013; Morocco=2 in 2013; South Africa=3 in 2014)
- [ ] Confirm KNBS/HCP/Stats SA reporting-year basis
- [ ] South Africa: compare 9-province total growth in 2014 with national nominal GDP growth; compare the Stats SA official series across 2013/2014
- [x] Rounding: Egypt full precision; Nigeria 100% and South Africa 89% of rows rounded to <=3 significant digits; Kenya 19% -> 60% (2013 -> 2017); Morocco 15-25%. Noise floor ~0.2-1 pt on growth
- [ ] Kenya: why does the rounded share rise from 2013 to 2017? Check county growth for 2016-2017 before relying on it
- [ ] Download official series (KNBS, HCP, Stats SA, MPED) and compare against DOSE on overlapping years

## DOSE processing rules

Implemented in `src/nowcast/transforms/dose.py`.

- Join on `GID_1`, not region name (Morocco's old and new region sets have separate IDs).
- Target: log growth of `grp_pc_lcu_2015` (real per-capita GRP), never nominal `grp_lcu`.
- Blank growth where the previous year is missing or `StructChange > 0`. `StructChange`: 1 = new raw data source, 2 = boundary change, 3 = series extended vs a prior DOSE version. A 3 coincided with a real break (South Africa 2014), so all non-zero values are treated as breaks.
- Hard-code `("ZAF", 2014)` as a break regardless of the flag.
- Add `is_rounded` (GRP has <= 3 significant digits) to every row, and read metrics against the noise floor.
- Use 2013 onward (satellite era). Monthly VIIRS composites are believed to start in 2012: verify when building the VIIRS ingestor.
- Egypt: aggregate features over Jul-Jun windows (fiscal-year-ending labels).

## Feature sources (Phase 1+)

VIIRS night lights, Open-Meteo weather, OSM/Overture, FX/commodities, GDELT.