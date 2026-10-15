# Clinical quality measures

Independent demonstration in two parts. The organizations are illustrative. The patients are synthetic. Nothing here is a health system's performance, a payer submission, or a CMS submission.

## Riverbend Community Health Network

A research-data case: build an analysis-ready patient file and two study rates before a quality-improvement study starts. The audience is a quality director, a research operations manager, and clinic managers. The source is a Synthea CSV extract (Massachusetts, seed 2026, reference date 13 October 2026).

The decision the file supports is whether the team has a defendable base: a known population, a known window, and rates whose uncertainty is visible when a clinic is small. The answer is in `docs/recommendations.md`. The network study rates are blood pressure control **58.9%** (53.9–63.7) among 377 patients, and A1c under 8% **82.9%** (74.5–88.9) among 105. Control means systolic under 140 and diastolic under 90. These are problem-list study rates. Zero patients have the diagnosis on two dates, so the published denominator is empty.

### Ask

The business task, the stakeholders, and the boundary with the contract packet: `docs/business-task.md`.

### Prepare

Source, license, privacy, the comparison with an Epic Clarity model, and the entity diagram: `docs/data-sources.md`. Column dictionary: `docs/synthea-data-dictionary.csv`. The untouched extract is `data_raw/synthea/`, with checksums in `data_raw/MANIFEST.sha256`. Study tables were loaded to local DuckDB because a BigQuery client was not available.

### Process

Checks, staging, the one-row-per-patient table, and the cleaning log: `sql/process_staging.sql`, `src/run_process.py`, `docs/cleaning-log.md`. The cohort is 2,285 patients in the export, 277 removed for death before 1 January 2026, 2,008 remaining. Missingness: `outputs/figures/missing_data_heatmap.png`. Cleaning attrition: `outputs/figures/cleaning_waterfall.png`.

### Analyze

Definitions, where they follow a public specification, and where they simplify one. Denominators and numerators in `sql/analyze_measures.sql`, including the latest result per patient. Rates by clinic and demographic group with Wilson intervals. One age model, because a clinic model needs two sites with at least 30 patients and this file has none. One sensitivity check on the lookback window. Cohort flow: `outputs/figures/cohort_flow.png`. Write-up: `docs/analysis-summary.md`.

### Share

The note for clinic managers, with the clinic charts and the trend lines: `docs/clinic-manager-report.md`.

- Blood pressure by clinic: `outputs/figures/bp_clinic_forest.png`
- Diabetes by clinic: `outputs/figures/gsd_clinic_forest.png`
- Blood pressure across the window: `outputs/figures/bp_trend.png`
- A1c across the window: `outputs/figures/gsd_trend.png`

### Act

Three recommendations, three limitations, the next study, and what a production run needs: `docs/recommendations.md`.

1. Show the network rate and its range. Withhold a clinic ranking below 30 denominator patients.
2. Work the list of patients with no result before reading the rate as control. That list is 59 missing blood pressures and 17 missing A1c tests.
3. Record the diagnosis on the visit before anyone uses these rates as the published measure.

## Contract and hospital measures

A separate assignment, for an illustrative regional system with 3 hospitals and about 15 clinics. Payers score the system on HEDIS Controlling High Blood Pressure and Glycemic Status Assessment. The hospital measure is CMS816v5, Hospital Harm — Severe Hypoglycemia. Specifications: `docs/measure-specifications.md`. What this Synthea extract can and cannot score: `docs/data-profile.md`. The leadership page and the data-gap memo: `docs/leadership-dashboard.md`, `docs/data-gap-memo.md`.

Those documents and the Riverbend rates answer different questions. The Riverbend percentages do not belong on the contract tiles.

## Rebuild the Riverbend rates

From the repository root, after the Synthea CSVs exist. Generation settings are in `data/synthea/README.md`. `src/load_study_warehouse.py` replaces `warehouse/riverbend.duckdb`, so the process step has to run immediately after it.

```
python3 src/load_study_warehouse.py
python3 src/run_process.py
python3 src/run_analyze.py
```

`src/test_measures.py` checks the rule functions used by the contract profile. It does not compute the Riverbend rates.

Large CSVs, the Synthea jar, and the DuckDB file are gitignored. The warehouse is rebuilt from the scripts above.
