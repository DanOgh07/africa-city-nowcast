# Data sources

## Ground truth (target variable)

| Source | Country | Unit | Cadence | Status | Notes |
|---|---|---|---|---|---|
| KNBS Gross County Product | Kenya | 47 counties | Annual | Confirmed | Reports 2019, 2021, 2023, 2024; verify exact year coverage per report |
| HCP regional accounts | Morocco | 12 regions | Annual | Confirmed | Latest release covers 2024; regions include rural areas |
| MPED GDP by governorate | Egypt | Governorates | Annual | Verify | Confirm number of years on the portal. DOSE: 27 governorates 1998-2015 (gaps; ends 2015, only 3 years overlap satellite data). MPED portal needed to extend |
| Stats SA provincial GDP | South Africa | 9 provinces | Annual | Confirmed | 2013-2023 seen; series paused ~2 years then re-released (check consistency) |
| NBS state GDP | Nigeria | States | Annual | Patchy | 22 states for 2013-2017 seen; sector-by-state tables exist for 2023, but unconfirmed whether they sum to total state GDP or how many years/what base year. See audit |
| NBS state IGR | Nigeria | 36 states + FCT | Annual | Confirmed (2021-2024) | Fiscal proxy, not GDP |
| Lagos Bureau of Statistics (LEDU) | Nigeria | Lagos only | Quarterly | Confirmed | State-government estimate; methodology differs from NBS |
| DOSE (Zenodo) | Global | Sub-national | Annual | Backup | Ends 2020. Nigeria: 22 states 2013-2017, no Lagos. Egypt: 27 governorates 1998-2015. Kenya: 47 counties 1966-2017. Morocco: 2013-2019 on current 12-region map (older 2007-2013 rows use the former 16-region map; do not pool). South Africa: 9 provinces 1996-2016. Use real per-capita columns, not nominal |
| Ghana GSS regional GDP | Ghana | Regions | -- | Excluded | Not published until after rebasing |

## Open questions (Phase 0)

- [ ] Nigeria: which states have a usable multi-year series? Any state-level proxy (IGR, electricity, VAT)?
- [ ] Egypt: year range on the MPED portal
- [x] DOSE: which of our units appear?
- [ ] Boundary source: GADM vs geoBoundaries (write ADR 0002)
- [ ] Nigeria: do 2023 NBS sector-by-state tables sum to total state GDP? Which base year? 2018-2022 available?
- [ ] Kenya/Egypt: which years are missing inside DOSE's ranges?

## Feature sources (Phase 1+)

VIIRS night lights, Open-Meteo weather, OSM/Overture, FX/commodities, GDELT.