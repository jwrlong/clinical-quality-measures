# Cleaning log

**Portfolio note.** Riverbend Community Health Network is fictional. The rows are synthetic Synthea patients. This log covers the study warehouse only.

**Measurement period.** 1 January 2026 through 13 October 2026. The end date is the Synthea reference date. Staging keeps the full history. `analytic.patient_period` is one row per patient who had not died before the period opened.

**What was not done.** No raw CSV was edited. No missing death date, name part, reason code, or payer address was imputed. Those nulls are real properties of the export. Official HEDIS value sets were not applied. Plausibility bounds below are study rules.

**Several observations.** Staging keeps every blood pressure and A1c. The analytic patient row stores how many eligible readings the patient has. The measure phase selects the most recent eligible reading. It does not average them.

**Cohort.** 2285 patients in the export, 277 removed from the analytic table because they died before 1 January 2026, 2008 patients in `analytic.patient_period`.

| Issue | How it was found | Rows affected | Decision | Reason |
| --- | --- | ---: | --- | --- |
| Duplicate primary keys on patients, organizations, providers, payers, and encounters | count(*) compared with count(DISTINCT id) in sql/process_staging.sql inputs | 0 | Retain every row | No duplicate identifiers. Encounter joins cannot multiply a patient through a repeated encounter id. |
| Foreign key present but unmatched | LEFT JOIN anti-joins in src/run_process.py | 0 | Retain every row | Every populated patient, encounter, organization, provider, and payer key finds its parent. |
| Death date before birth date | staging.patients.death_before_birth | 0 | Retain every row | No patient has a death date earlier than the birth date. |
| Patient died before the measurement period | staging.patients.died_before_period, death date before 2026-01-01 | 277 | Exclude from analytic.patient_period | The study window is 1 January 2026 through 13 October 2026. A person who died before it is not in the cohort. The row stays in staging.patients. |
| Patient died during the measurement period | staging.patients.died_during_period | 8 | Keep in analytic.patient_period | Death during the window is a measure-specific exclusion. Analyze applies it. Process only marks the row. |
| Encounter starts after the death date | staging.encounters.after_death, UTC start date after DEATHDATE | 276 | Flag and keep. Exclude from organization attribution and from analytic.observation_eligible | The gap is 1 to 14 days. The row may be a generator artifact. Deleting it would hide the defect. |
| Observation dated after the death date | staging.observations.after_death | 425 | Flag and keep. Exclude from analytic.observation_eligible | Same defect as encounters after death. The value remains available for audit. |
| Observation has no encounter id | staging.observations.encounter_missing | 62856 | Flag and keep. Exclude from analytic.observation_eligible | Category is blank on the same rows. Blood pressure and A1c codes account for 0 of them, so the two study measures do not lose a result here. |
| Medication stop timestamp is before the start | staging.medications.negative_duration, 48 to 144 hours | 97 | Flag and keep. Do not use STOP as the course end on these rows | A negative duration is not a real course length. The start timestamp is still a prescription date. |
| Systolic value outside 70 to 250 mmHg | staging.observations, LOINC 8480-6 | 30 | Flag implausible_value and exclude from analytic.observation_eligible | Study plausibility bound, not a HEDIS rule. The lowest value in the file is 40.5. |
| Diastolic value outside 40 to 150 mmHg | staging.observations, LOINC 8462-4 | 112 | Flag implausible_value and exclude from analytic.observation_eligible | Study plausibility bound. The lowest value in the file is 18. |
| Systolic lower than diastolic at the same timestamp | Pair of LOINC 8480-6 and 8462-4 grouped by patient and timestamp | 73 | Flag both readings implausible and exclude them from analytic.observation_eligible | An inverted pair cannot be a blood pressure. Rows already outside the numeric bounds are counted in the two rows above. |
| A1c below 3% | staging.observations, LOINC 4548-4 | 1697 | Flag implausible_value and exclude from analytic.observation_eligible | Study plausibility bound. No A1c in the file is above 20%. Values under 3% are not used as glycemic results. |
| Clinical timestamp after the generator reference date | UTC date after 2026-10-13 | 3 | Flag outside_window and exclude from the measurement period | Encounters dated after 13 October 2026: 2. Observations dated after that day: 1. The reference date remains the end of the window. |
| Several blood pressure readings for one patient in the window | analytic.patient_period.n_systolic | 270 | Keep every reading in staging. Do not collapse them in Process | The later measure query selects the most recent eligible reading with a window function. Collapsing now would hide the choice. |
| Patient seen at more than one organization in the window | analytic.patient_period.n_organizations | 1105 | Attribute the patient to the organization with the most in-window encounters, breaking ties with the latest encounter | The file is a statewide set of organizations, not a single clinic panel. The rule is explicit so a later clinic rate is not an accident of join order. |

Figures: `outputs/figures/missing_data_heatmap.png` and `outputs/figures/cleaning_waterfall.png`. Column-level null rates are in `outputs/null_rates.csv`. The SQL is `sql/process_staging.sql`.
