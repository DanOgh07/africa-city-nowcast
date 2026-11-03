# Data sources

## Ground truth (target variable)

| Source | Country | Unit | Cadence | Status | Notes |
|---|---|---|---|---|---|
| KNBS Gross County Product | Kenya | 47 counties | Annual | Confirmed | Reports 2019, 2021, 2023, 2024; verify exact year coverage per report |
| HCP regional accounts | Morocco | 12 regions | Annual | Confirmed | Latest release covers 2024; regions include rural areas |
| MPED GDP by governorate | Egypt | Governorates | Annual | Verify | Confirm number of years on the portal |
| Stats SA provincial GDP | South Africa | 9 provinces | Annual | Confirmed | 2013-2023 seen; series paused ~2 years then re-released (check consistency) |
| NBS state GDP | Nigeria | States | Annual | Patchy | 22 states for 2013-2017 seen; newer data mostly sector-specific. Audit first |
| DOSE (Zenodo) | Global | Sub-national | Annual | Backup | Ends 2020; check which African countries are present |
| Ghana GSS regional GDP | Ghana | Regions | -- | Excluded | Not published until after rebasing |

## Open questions (Phase 0)

- [ ] Nigeria: which states have a usable multi-year series? Any state-level proxy (IGR, electricity, VAT)?
- [ ] Egypt: year range on the MPED portal
- [ ] DOSE: which of our units appear?
- [ ] Boundary source: GADM vs geoBoundaries (write ADR 0002)

## Feature sources (Phase 1+)

VIIRS night lights, Open-Meteo weather, OSM/Overture, FX/commodities, GDELT.
