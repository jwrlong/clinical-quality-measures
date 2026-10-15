# Data profile, Synthea extract

**Portfolio note.** Independent demonstration. The rows are synthetic patients produced by Synthea, not records from a health system, a payer, or CMS. The counts below describe this file only.

**Source.** Synthea version `d9d07a6`, state Massachusetts, seed 2026, clinician seed 2026, reference date 20261013. The run asked for 2,000 living patients. The patient file contains 2285 people, living and deceased. Clinical history in the files runs through 2026-10-13. Measurement year 2026 is therefore incomplete: November and December are not in the extract.

**How to regenerate.** From the repository root, with Java 17 or newer:

```
java -jar tools/synthea-with-dependencies.jar -s 2026 -cs 2026 -r 20261013 -p 2000 --exporter.csv.export=true --exporter.fhir.export=false --exporter.ccda.export=false --exporter.baseDirectory=data/synthea --exporter.years_of_history=10 --generate.thread_pool_size=1 Massachusetts
python3 src/profile_synthea.py
```

The CSV files are produced locally and are not committed. They are larger than the repository should carry, and the seed above is what makes the run repeatable.

## What was asked of this file

The specifications ask for dated diagnosis evidence, a numeric blood pressure or A1c, and, for the hospital measure, a medication administration time and a glucose draw time. This section records what Synthea actually stored.

For blood pressure, a qualifying visit is Synthea's ambulatory, wellness, outpatient, or virtual class. Those stand in for outpatient, telephone, and online visits. Urgent care, emergency, and inpatient encounters are not used for that count. This is a class map for this file. It is not the HEDIS value set. For diabetes, a diagnosis date in any encounter class counts, except a laboratory encounter. Synthea has no place-of-service field, so that class exclusion is the stand-in for a laboratory claim.

| Table fact | Count |
| --- | ---: |
| Patients in the file | 2285 |
| Essential hypertension (SNOMED 59621000) active in the identification window | 514 |
| Type 2 diabetes (SNOMED 44054006) active in 2025 or 2026 | 163 |
| Inpatient encounters that end in 2026 | 61 |
| Glucose-management indicator rows (LOINC 97506-0) | 0 |
| Urine glucose strip results in 2026, ignored by CMS816v5 | 833 |
| Provider organizations in the file | 946 |

The file is a Massachusetts population. It is not a 15-clinic health system, and the organizations are not rolled into that shape.

## How the event rule was checked

The licensed HEDIS Volume 2 for measurement year 2026 was not the copy open for this check. Production reporting still uses that volume. The events below follow NCQA's published specification language and measurement-year 2026 plan guides that cite it.

Controlling High Blood Pressure uses two visits on different dates, and the hypertension diagnosis is part of each visit. The window runs from 1 January 2025 through 30 June 2026. The visits may be outpatient, telephone, e-visit, or virtual check-in. The blood pressure has to fall on or after the second of those diagnosis dates. NCQA writes the event as a visit value set combined with the Essential Hypertension value set. Guides from Blue Cross NC, Priority Health, BCBST, Carolina Complete Health, and BCBSND use that event for 2026. One Florida Blue sheet lists the visits and "any diagnosis of hypertension" as separate bullets. That sheet still requires the second diagnosis date, so a single problem-list onset does not qualify.

Glycemic status uses two diabetes diagnosis dates of service in any setting during 2025 or 2026, excluding a laboratory claim, or one diagnosis date in that span plus a dispensing event in that span. That is NCQA's current event, the one that replaced a list of specific visit types.

## Controlling High Blood Pressure

The HEDIS denominator needs two outpatient, telephone, or online encounters in the identification window, on different dates, each carrying a hypertension diagnosis.

Encounters in that window that carry SNOMED 59621000 and have a qualifying class: patients with two such encounters = **0**.

The contract rate is not calculated. A denominator of zero is not a performance result.

The condition is present. 514 patients have essential hypertension active during the window. 387 of them also have two qualifying visits in the window. No patient has the hypertension code on two of those visits. The usual shape is one condition row, dated at onset. Reusing the problem list would put 353 adults age 18 to 85, with no death, hospice, pregnancy, or end-stage renal row found in 2026, into an internal denominator. That reuse is a different measure. Of those 353, 299 have a paired numeric systolic and diastolic in 2026 on an eligible encounter. 209 of those pairs are under 140 and under 90. Those counts describe the values in the file. They are a description, and the contract tile stays blank.

Payer spans have start and end timestamps. The file contains 0 spans with a blank end date. 251 of the internal-denominator patients have one payer whose own spans cover 31 December 2026 and meet the 45-day gap rule. Spans from different payers were not merged. Named payers are present, including Medicare, Medicaid, and Dual Eligible. Plan ownership on the member span takes these values: (blank), Guardian, Self, Spouse. Guardian, Self, and Spouse are subscriber relationships. A blank value is an empty field. The span does not identify an institutional special needs plan or a long-term institution, so that exclusion is not applied. Home blood-pressure device type is absent, so a home reading is not used. Clinical rows stop on 2026-10-13, so a 2026 blood pressure in this file cannot fall in November or December.

Patient `4675cf35-1466-3c14-4e58-6ffdc29d6270` has essential hypertension recorded on 1977-10-29. That code is attached to no qualifying encounter in the identification window. The same patient has 4 qualifying visits in the window, and a paired 2026 blood pressure.

## Glycemic Status Assessment for Patients With Diabetes

The HEDIS denominator needs two diabetes diagnosis dates of service in any non-laboratory setting during 2025 or 2026, or one such diagnosis date plus a diabetes medication dispense in that span.

Patients with two diabetes diagnosis dates in that span: **0**.

Patients with one in-window diabetes diagnosis date plus a diabetes medication course that has at least one dispense, and who do not already have two diagnosis dates: **4**.

Patients who meet either written method, are age 18 to 75, and are not removed for death, hospice, or palliative care: **4**. The contract rate is not calculated from that count. A medication row here is a course with a dispense count, which is the closest field the file has to a pharmacy fill.

Diabetes condition rows in the file: SNOMED 44054006, Diabetes mellitus type 2 (disorder), 163 rows. 163 patients have type 2 diabetes active in the two-year span, and 131 of those also have two qualifying visits. The diagnosis is stored at onset and is not coded again on the later visits. Reusing the problem list would put 105 adults age 18 to 75, with no death, hospice, or palliative row in 2026, into an internal list. That list is a different measure. There are no glucose-management indicator rows. Hemoglobin A1c, when present, is a numeric percent (LOINC 4548-4).

A1c values among the 4 patients who meet a written identification method:

| 2026 A1c | Patients |
| --- | ---: |
| Under 8.0% | 4 |
| 8.0% through 9.0% | 0 |
| Over 9.0% | 0 |
| No A1c in the extract | 0 |

A1c values among the 105 patients in the problem-list description, which is not a reportable denominator:

| 2026 A1c | Patients |
| --- | ---: |
| Under 8.0% | 89 |
| 8.0% through 9.0% | 1 |
| Over 9.0% | 0 |
| No A1c in the extract | 15 |

Neither table is a GSD rate. The first follows the written identification methods and is too small to display. The second describes the A1c file if the problem list is reused. In that second table, 15 patients have no 2026 A1c. The numerator rule would place a missing result in the over-9.0% rate. That step is not taken here, because those patients are not the HEDIS denominator.

## Hospital Harm — Severe Hypoglycemia

Adult inpatient encounters that end in 2026: **60**.

Glucose results under 40 mg/dL in 2026, in any setting: **0**. On those adult stays, glucose results from blood or serum: 70. The lowest of them is 64.8 mg/dL.

Medication rows are courses. They have a start, a stop, and a dispense count. They are not administration events. 11 adult stays overlap an insulin course. Overlap of a course does not locate a dose within 24 hours of a draw.

CMS816v5 is not scored. The numerator event does not occur in this file, and the administration clock the specification uses is not in the file. Urine glucose strips are present and were not treated as blood glucose.

## What this file changes in the packet

The gap is not a blood pressure buried in a note. Systolic, diastolic, and A1c values that Synthea writes are discrete numbers. The gap is the diagnosis. Hypertension and diabetes are recorded when they start and are not coded on later encounters, so the HEDIS denominators cannot be formed. The hospital measure has a second, separate limit: no glucose under 40 mg/dL, and no medication administration time.

An internal rate that reused the problem list would answer a different question. It is not the rate a payer or CMS would compute from this extract.
