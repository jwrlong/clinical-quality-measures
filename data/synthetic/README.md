# Hand-built extract

This folder is not the analysis dataset. The profile, dashboard, and memo use the Synthea extract described in `data/synthea/README.md`. Counts in this folder were built to exercise `src/measures.py`. They are not evidence about a health system, and they are not the figures in `docs/data-profile.md`.

The files are invented data for the measurement year 1 January 2026 through 31 December 2026. Every patient identifier is synthetic. Nothing here came from an EHR, a payer, or a hospital.

The extract is a teaching sample with three cohorts in one set of files: hypertension (CBP), diabetes (GSD), and inpatient stays (CMS816v5). Documentation failures are planted so they can be counted. Rates from this folder are not prevalence and are not a health system's performance. `src/profile_measures.py` writes `outputs/hand_built_profile.md` and does not replace `docs/data-profile.md`.

`meter_held_glucose.csv` is not part of the EHR extract. It is the bedside file the EHR did not receive. The official CMS816v5 rate ignores it.

Rebuild from the repository root:

```
python3 src/test_measures.py
python3 src/generate_extract.py
python3 src/profile_measures.py
```

Row counts in this build: 1450 patients, 2431 encounters, 700 blood pressures, 330 glycemic results, 512 glucose results, 1 meter-held glucose results.
