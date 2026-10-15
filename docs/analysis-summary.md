# Analysis summary

Riverbend Community Health Network. Measurement window 1 January 2026 through 13 October 2026, the last day this Synthea extract covers. Prepared 14 October 2026.

Portfolio note. Riverbend is an illustrative safety-net network. The rates in this note are a study definition applied to a public synthetic file. They are not HEDIS results, and they are not the hospital contract packet in `docs/leadership-dashboard.md`.

## What was measured

Blood pressure control follows the public structure of HEDIS Controlling High Blood Pressure: adults 18–85, essential hypertension, and a most recent blood pressure in the measurement year under 140 systolic and under 90 diastolic. A missing reading stays in the denominator and counts as not controlled.

Glycemic status follows the public structure of HEDIS Glycemic Status Assessment for Patients With Diabetes: adults 18–75 with diabetes, one denominator, and two results. Under 8% is the result where higher is better. Over 9% is the result where lower is better, and a missing A1c counts in the over-9 result. A result from 8.0% through 9.0% is in neither.

Both published denominators require two diagnosis dates of service, or, for glycemic status, one diagnosis date plus a dispensing event. This export stores each diagnosis once, at onset. Patients with the code on two different dates: **0** for essential hypertension (SNOMED 59621000) and **0** for type 2 diabetes (SNOMED 44054006). A literal published denominator cannot be formed.

The study denominator uses the problem list instead. Hypertension counts when the onset is on or before 30 June 2026 and the condition is still open on 1 January 2025. Diabetes counts when the onset is on or before 13 October 2026 and the condition is still open on 1 January 2025. Death during the window and a hospice encounter are removed. Pregnancy, end-stage renal disease, frailty, and institutional long-term care are not applied: this file has no value set for them and no institutional flag.

The numerator uses the most recent qualifying day. Blood pressure must fall on or after the hypertension onset, in an ambulatory, wellness, outpatient, virtual, or urgent-care encounter. Inpatient and emergency readings are left out. Home readings are left out because the file does not say whether the device was digital. When a day has more than one reading, the numerator uses the lower systolic and the lower diastolic. A1c uses the lower result when more than one falls on the same day. The window function that picks the latest day is in `sql/analyze_measures.sql`.

## Denominators

| Step | Blood pressure | Glycemic status |
| --- | ---: | ---: |
| Patients in the export | 2285 | 2285 |
| Died before 1 January 2026 | 277 | 277 |
| Outside the age range | 488 | 566 |
| No active condition on the problem list | 1137 | 1337 |
| Died during the window | 4 | 0 |
| Hospice encounter | 2 | 0 |
| Denominator | 377 | 105 |

The figure is `outputs/figures/cohort_flow.png`.

## Results

Blood pressure. Denominator 377. Controlled 222, 58.9% (53.9–63.7). Reading at or above the threshold 96. No usable reading 59. Those 59 patients stay in the denominator and count as not controlled.

Glycemic status. Denominator 105. A1c under 8% 87, 82.9% (74.5–88.9). A1c over 9% or no A1c 17, 16.2% (10.4–24.4). Of that over-9 result, 0 have an A1c over 9% and 17 have no A1c. A1c from 8% through 9%: 1, in neither result.

### Blood pressure by age and sex

| Group | Denominator | Controlled | Rate (95% interval) |
| --- | ---: | ---: | --- |
| 18–44 | 45 | 26 | 57.8% (43.3–71.0) |
| 45–64 | 204 | 114 | 55.9% (49.0–62.5) |
| 65 and older | 128 | 82 | 64.1% (55.5–71.9) |
| F | 182 | 109 | 59.9% (52.6–66.7) |
| M | 195 | 113 | 57.9% (50.9–64.7) |

### Glycemic status under 8% by age and sex

| Group | Denominator | Under 8% | Rate (95% interval) |
| --- | ---: | ---: | --- |
| 18–44 | 11 | 10 | 90.9% (62.3–98.4) |
| 45–64 | 61 | 51 | 83.6% (72.4–90.8) |
| 65 and older | 33 | 26 | 78.8% (62.2–89.3) |
| F | 48 | 39 | 81.2% (68.1–89.8) |
| M | 57 | 48 | 84.2% (72.6–91.5) |

Race and ethnicity rates are in `outputs/analysis_rates.csv`. Several race groups have denominators under 30, and those intervals are wide enough that a ranking would overstate a difference.

## Clinics

The 377 blood-pressure patients are attributed to 165 organizations. Another 31 have no encounter in the window, so they have no clinic and no reading, and they count as not controlled. No organization reaches 30 patients. 2 have at least 10 patients, and 13 have at least 5. The largest blood-pressure clinic denominator is 11.

One blood-pressure clinic interval excludes the network rate, and that clinic has 3 patients. The 2 clinics with 10 or more patients have intervals that include the network rate. A ranking of sites would treat noise as a difference.

Glycemic patients are attributed to 71 organizations, plus 4 with no encounter in the window. The largest glycemic clinic denominator is 4. No glycemic clinic reaches 10 patients. 7 have at least 3 patients.

Clinic rates with intervals are in `outputs/bp_clinic_rates.csv` and `outputs/gsd_clinic_rates.csv`. The forest plots are `outputs/figures/bp_clinic_forest.png` (clinics with at least 5 patients) and `outputs/figures/gsd_clinic_forest.png` (clinics with at least 3).

## One test

Fewer than two clinics have 30 or more patients in the blood-pressure denominator (largest clinic n = 11). A clinic comparison after age adjustment is not estimable. An age-only model on the 377 denominator patients gives an odds ratio of 1.016 per year of age (p = 0.080).

## Sensitivity

The study denominator counts a condition that started years ago if it is still on the problem list. Restricting the denominator to an onset inside the identification window is the check on that choice.

| Rule | Blood pressure denominator | Controlled | Glycemic denominator | Under 8% | Over 9% or missing |
| --- | ---: | ---: | ---: | ---: | ---: |
| Active problem list | 377 | 222 (58.9%) | 105 | 87 (82.9%) | 17 (16.2%) |
| Onset inside the identification window | 19 | 12 (63.2%) | 12 | 11 (91.7%) | 1 (8.3%) |

The identification window is 1 January 2025 through 30 June 2026 for hypertension, and 1 January 2025 through 13 October 2026 for diabetes. 19 of the 377 blood-pressure patients, and 12 of the 105 diabetes patients, have an onset inside that window. The study rates are carried by conditions that began before 2025.

## Direction across the window

The trend uses the same blood-pressure denominator and asks, at each quarter end, what share of patients who already have a reading are controlled. The interval is a Wilson interval on that measured group. Patients with no reading yet are not in the line. They remain in the denominator of the full-window rate above.

| Point | Patients with a reading | Controlled | Rate (95% interval) |
| --- | ---: | ---: | --- |
| Through 31 Mar | 134 of 377 | 99 | 73.9% (65.9–80.6) |
| Through 30 Jun | 231 of 377 | 162 | 70.1% (63.9–75.7) |
| Through 30 Sep | 307 of 377 | 212 | 69.1% (63.7–74.0) |
| Through 13 Oct | 318 of 377 | 222 | 69.8% (64.6–74.6) |

The figure is `outputs/figures/bp_trend.png`.

The glycemic trend uses the same rule on the diabetes denominator: at each quarter end, the share under 8% among patients who already have an A1c. Patients with no result yet are outside the line and remain in the full-window denominator.

| Point | Patients with an A1c | Under 8% | Rate (95% interval) |
| --- | ---: | ---: | --- |
| Through 31 Mar | 37 of 105 | 37 | 100.0% (90.6–100.0) |
| Through 30 Jun | 66 of 105 | 66 | 100.0% (94.5–100.0) |
| Through 30 Sep | 84 of 105 | 83 | 98.8% (93.6–99.8) |
| Through 13 Oct | 88 of 105 | 87 | 98.9% (93.8–99.8) |

The figure is `outputs/figures/gsd_trend.png`.

## Where these rates belong

These percentages stay in this study note. The contract dashboard still has no rate: 0 patients have two hypertension diagnosis dates, and 0 have two diabetes diagnosis dates. The rates above describe the active problem list and the readings in this file under a public-style numerator.
