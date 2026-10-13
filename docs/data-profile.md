# Data profile, measurement year 2026

**Portfolio note.** Independent demonstration. Every row in `data/synthetic/` is synthetic. The extract was built so the rules in `docs/measure-specifications.md` could be counted, including planted documentation failures. The percentages below are not a health system's performance and are not a prevalence estimate.

**How this was produced.** `python3 src/test_measures.py`, then `python3 src/generate_extract.py`, then `python3 src/profile_measures.py`. The calculator reads the CSV files. It does not read the scenario name when it decides a rate. The scenario name is used only to explain a row after the fact.

## What is in the file

The extract holds three cohorts in one set of tables, because that is how an analyst usually receives data: one patient file, one encounter file, and the clinical tables beside them.

| Table | Rows |
| --- | ---: |
| Patients | 1450 |
| Encounters | 2431 |
| Blood pressures | 700 |
| Glycemic results | 330 |
| Glucose results in the EHR extract | 512 |
| Glucose results held on the meter, not in the EHR extract | 1 |

`data/synthetic/data_dictionary.csv` defines the columns. `meter_held_glucose.csv` is not part of the EHR extract. The official CMS816v5 rate does not see it.

Starting a denominator from every patient in the file would be a mistake. Most of the file is in a different cohort and was never a candidate for that measure. Each waterfall below starts from its own cohort.

The failure rows are planted. A routine panel, with discrete results and complete enrollment, sits beside them so a clean record can be told from a capture failure. A rate that mixes the two describes this teaching file. It does not describe a clinic.

## Controlling High Blood Pressure

Cohort size: 640 patients.

| Step | Patients |
| --- | ---: |
| In the hypertension cohort | 640 |
| Age 18 through 85 on 31 December 2026 | 630 |
| Removed for age | 10 |
| Age in range but fewer than two qualifying hypertension encounters in the identification window | 30 |
| Removed by an exclusion after the encounter rule | 60 |
| EHR denominator | 540 |
| Also continuously enrolled: payer-aligned denominator | 510 |

EHR clinic rate: **360 / 540 (66.7%)** controlled. Higher is better.

Payer-aligned rate: **330 / 510 (64.7%)** controlled. The 30 patients in the EHR denominator and not in the payer denominator failed continuous enrollment. They are a real difference between an internal rate and a contract rate. They are not a capture gap.

Among the EHR denominator:

| Result | Patients |
| --- | ---: |
| Controlled | 360 |
| Not controlled, usable reading at or above 140/90 | 120 |
| Not controlled, blood pressure exists only as text | 30 |
| Not controlled, only reading is an ineligible home device | 30 |

The text readings are the capture gap. The ineligible home device is the specification working as written: a non-digital home reading does not count, and those patients have no other 2026 reading. Both groups sit inside "not controlled." The leadership page has to show them separately, or a device rule looks like missing data.

Clinic rates use the attributed clinic and the EHR denominator. Clinics 06 through 10 hold the planted text readings, and they are the five lowest rates.

| Clinic | Controlled | Rate | No usable reading |
| --- | ---: | ---: | ---: |
| Outpatient clinic 06 | 24 / 40 | 60.0% | 8 |
| Outpatient clinic 07 | 24 / 40 | 60.0% | 8 |
| Outpatient clinic 08 | 24 / 40 | 60.0% | 8 |
| Outpatient clinic 09 | 24 / 40 | 60.0% | 8 |
| Outpatient clinic 10 | 24 / 40 | 60.0% | 8 |
| Outpatient clinic 01 | 24 / 34 | 70.6% | 2 |
| Outpatient clinic 02 | 24 / 34 | 70.6% | 2 |
| Outpatient clinic 03 | 24 / 34 | 70.6% | 2 |
| Outpatient clinic 04 | 24 / 34 | 70.6% | 2 |
| Outpatient clinic 05 | 24 / 34 | 70.6% | 2 |
| Outpatient clinic 11 | 24 / 34 | 70.6% | 2 |
| Outpatient clinic 12 | 24 / 34 | 70.6% | 2 |
| Outpatient clinic 13 | 24 / 34 | 70.6% | 2 |
| Outpatient clinic 14 | 24 / 34 | 70.6% | 2 |
| Outpatient clinic 15 | 24 / 34 | 70.6% | 2 |

## Glycemic Status Assessment for Patients With Diabetes

Cohort size: 315 patients. EHR denominator: 270. Payer-aligned denominator: 255.

| EHR result | Patients | Share of EHR denominator |
| --- | ---: | ---: |
| Under 8.0% | 144 | 53.3% |
| 8.0% through 9.0% | 39 | 14.4% |
| Over 9.0%, numeric result | 42 | 15.6% |
| No usable result | 45 | 16.7% |

Over 9.0% rate, EHR: **87 / 270 (32.2%)**. Lower is better. This rate adds the numeric results over 9.0% and the patients with no usable result.

Of the 87 patients in that rate, 45 have no usable result (51.7% of the numerator). Those 45 split into 15 notes, 15 scanned documents, and 15 glucose-management indicators that have a number and no monitor date range.

15 other patients are in the numeric over-9.0% group because the most recent usable lab is over 9.0%, while a later result sits in a note. The measure cannot use the note. The chart and the rate disagree.

Payer-aligned over 9.0% rate: **87 / 255 (34.1%)**. Under 8.0%, payer-aligned: **129 / 255 (50.6%)**.

Clinic rates below use the EHR denominator. A higher over-9.0% rate is worse. Clinics 06 through 10 again carry the planted notes and scans.

| Clinic | Over 9.0% | Rate | No usable result |
| --- | ---: | ---: | ---: |
| Outpatient clinic 06 | 10 / 22 | 45.5% | 7 |
| Outpatient clinic 07 | 10 / 22 | 45.5% | 7 |
| Outpatient clinic 08 | 10 / 22 | 45.5% | 7 |
| Outpatient clinic 09 | 10 / 22 | 45.5% | 7 |
| Outpatient clinic 10 | 10 / 22 | 45.5% | 7 |
| Outpatient clinic 04 | 4 / 16 | 25.0% | 1 |
| Outpatient clinic 05 | 4 / 16 | 25.0% | 1 |
| Outpatient clinic 11 | 4 / 16 | 25.0% | 1 |
| Outpatient clinic 12 | 4 / 16 | 25.0% | 1 |
| Outpatient clinic 13 | 4 / 16 | 25.0% | 1 |
| Outpatient clinic 14 | 4 / 16 | 25.0% | 1 |
| Outpatient clinic 15 | 4 / 16 | 25.0% | 1 |
| Outpatient clinic 01 | 3 / 16 | 18.8% | 1 |
| Outpatient clinic 02 | 3 / 16 | 18.8% | 1 |
| Outpatient clinic 03 | 3 / 16 | 18.8% | 1 |

## Hospital Harm — Severe Hypoglycemia

Inpatient encounters evaluated: 495. Denominator: 486. Numerator: 20.

Pooled rate: **20 / 486 (4.1%)**. Lower is better. The denominator is dominated by 450 background stays with a glucose of 142 mg/dL after insulin, so the planted harm cases do not become the whole rate. Even so, harm cases were inserted on purpose. This is not a hospital's expected rate.

| Hospital | Numerator stays | Rate | Stays that a meter export would remove | Stays whose repeat was documented after five minutes |
| --- | ---: | ---: | ---: | ---: |
| Hospital A | 6 / 162 | 3.7% | 0 | 1 |
| Hospital B | 7 / 162 | 4.3% | 1 | 1 |
| Hospital C | 7 / 162 | 4.3% | 0 | 2 |

Hospital denominators in this file are equal, so a pooled rate and an unweighted average of the three rates match. In a live file they will not. The dashboard pools hospitalizations.

The same clinical event was written three ways:

| Hospital | Official numerator | Why |
| --- | --- | --- |
| Hospital A | No | A repeat of 110 mg/dL three minutes later is in the extract, so the low is cleared. |
| Hospital B | Yes | The same repeat exists only in `meter_held_glucose.csv`. The official rate counts the stay. |
| Hospital C | Yes | A repeat of 110 mg/dL is in the extract six minutes later. The five-minute rule does not clear it. This is not a missing interface. |

One stay, at Hospital B, is in the CMS816v5 numerator only because the bedside repeat never reached the EHR. Hospital C looks similar on the rate and has a different problem.

## What the gap looks like in this file

The gap named in the memo is visible, and it is not the whole story of "not controlled."

- CBP: 30 denominator patients have a 2026 blood pressure only as text. They count as not controlled. Another 30 are not controlled because the only reading is from a non-digital home device.
- GSD: 45 denominator patients have no usable A1c or GMI, so they sit in the over-9.0% rate. 15 more are scored on an older lab because a later result is stuck in a note.
- CMS816v5: 1 stay in the numerator would leave it if the meter file were part of the extract.

## Worked rows

**Blood pressure as text.** Patient P1061, Outpatient clinic 06. Two hypertension encounters fall in the identification window, so the patient is in the EHR denominator. The only 2026 reading has blank systolic and diastolic and the note "BP 132/78 today." Result: not controlled, no usable reading.

**Later result trapped in a note.** Patient P2076. A discrete A1c of 9.4% on 1 March 2026 is the most recent usable result. A 1 November 2026 note says "A1c 7.1 at retail clinic" and stores no number. The over-9.0% rate uses 9.4%.

**False low, three hospitals.** Encounters E01933, E01950, and E01967. Each has a capillary glucose of 28 mg/dL after insulin. Hospital A clears it with a repeat in the extract. Hospital B does not, because that repeat is only on the meter. Hospital C does not, because its repeat is at six minutes.

## What this file cannot tell us

It cannot estimate how often a real clinic loses a blood pressure to free text. Those rows were inserted. It has no time zone and no clock drift, so it cannot show a glucometer clock pushing a repeat past five minutes. It uses demonstration concepts in place of the HEDIS value sets and the CMS value set OIDs. A production extract would be scored with those code lists, and the counts would move.
