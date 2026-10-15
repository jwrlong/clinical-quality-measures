# Recommendations

**To.** Dr. Maya Okafor, Director of Clinical Quality, and Tom Reyes, Research Operations Manager.
**From.** Research data analytics.
**Date.** 14 October 2026.
**About.** What to do with the 2026 blood-pressure and diabetes study rates.

**Portfolio note.** Riverbend is illustrative. The patients are synthetic. The three recommendations below are what this team would do if a real extract had the same shape. They are not clinical findings, and they are not a contract submission.

The decision from the business task was whether the research team has a base it can defend. It does, for a documented study file: a known population, a window that ends 13 October 2026, and rates whose uncertainty is visible. It does not have a base for ranking clinics or for a contract rate.

## Three recommendations

**1. Show the network rate and its range. Withhold a clinic ranking until a site has at least 30 patients in the denominator.**

The network figures a manager can say out loud are blood pressure control 58.9% (53.9–63.7) among 377 patients, and A1c under 8% 82.9% (74.5–88.9) among 105. Control means systolic under 140 and diastolic under 90, both true.

The 377 blood-pressure patients are spread across 165 organizations. The largest has 11. None reaches 30, which is why a clinic comparison after age adjustment cannot be fit. The largest diabetes clinic has 4. Two clinics have an interval that misses the network rate, and each of those clinics has 3 patients. A floor of 30 is the smallest size at which this file could have supported that comparison. Below it, a league table ranks the width of the interval.

**2. Work the list of patients with no result before reading the rate as control.**

Fifty-nine of the 377 blood-pressure patients have no usable reading, and they count as not controlled. Thirty-one of those 59 had no visit in the window at all. Among patients who do have a reading, control stays near 70% from March through 13 October (222 of 318 by the end).

Seventeen of the 105 diabetes patients have no A1c, and those 17 are the entire poor result. Zero patients in the denominator have an A1c over 9%. Among patients who have a result, 87 of 88 are under 8%.

If this were a real panel, the first list to send a clinic would be the patients already in the denominator who have no usable result. Recalculate the rate after those results exist. A low rate that is mostly missing tests is a completion problem.

**3. Record the diagnosis on the visit before these rates are used as the published measure.**

The published blood-pressure and diabetes denominators need the diagnosis on two different dates. This file stores each diagnosis once, at onset. Patients with two diagnosis dates: 0 for essential hypertension, 0 for type 2 diabetes. The rates above use the problem list so the file can be studied. Only 19 of the 377 blood-pressure patients, and 12 of the 105 diabetes patients, have an onset inside the usual identification window. The rest were already on the list before 2025.

Until a visit can carry its own diagnosis date, the contract version of either measure stays blank. The study rate and the contract rate have to stay labeled as two different counts.

## Three limitations

**1. The patients are synthetic.** Every count describes this Synthea extract (Massachusetts, seed 2026, reference date 13 October 2026, 2,285 patients in the file). A real Riverbend panel replaces the numbers. The recommendations travel only if the real extract has the same shape: one diagnosis date per condition, small sites, and missing results counted in the rate.

**2. The study rate simplifies the published specification, and several published exclusions are absent.** Death during the window and a hospice encounter are removed. Pregnancy, advanced kidney disease, frailty, and a nursing-home or institutional stay are part of the published rules and are not applied, because the file has no value set and no institutional flag. Home readings are left out because the file does not say whether the cuff was a connected device. The window stops on 13 October, so November and December are absent. Medications are stored as a course with a dispense count, not as a fill on a date, so the published diabetes path that pairs one diagnosis with a dispensing event cannot be rebuilt from a fill date.

**3. “Clinic” here is the organization with the most visits in the window, and that organization is often a hospital.** A patient with no visit has no site and still counts as not meeting the goal (31 blood-pressure patients, 4 diabetes patients). A difference between those organizations is not a difference between assigned primary-care panels.

## What would change the analysis

Dated pharmacy fills would supply the dispensing date the published diabetes path requires. Claims and enrollment product would supply continuous coverage and the institutional flag the age-66 exclusions use. An assigned clinic or primary clinician would replace the most-visits organization. A diagnosis coded on the encounter would let the published denominator be counted beside the problem-list rate.

Social needs screening would not repair those gaps. It would extend the next study: among patients with no result, which needs (transport, language, cost, housing) show up, and whether that pattern differs for the 31 blood-pressure patients who had no visit at all.

## The next study this file can support

A measurement-completion study, on the patients already in the two denominators. The outcome is whether a usable blood pressure or A1c exists by a set date, not whether one clinic beats another. The comparison already visible in this file is patients with no visit versus patients who had visits and still have no usable result. Social needs and dated fills become covariates when they arrive. Clinic randomization waits until sites have denominators large enough for the interval to mean something. A contract-measure validation waits until encounter diagnoses exist.

## What a production run of this pipeline needs

Rebuild on a schedule from an untouched extract, and compare the extract to `data_raw/MANIFEST.sha256` before the SQL runs. Keep the prior warehouse snapshot until the new run passes. The loader used here deletes `warehouse/riverbend.duckdb` and has to be followed by `src/run_process.py`. A scheduled job should load into a new snapshot instead of destroying the one the last report used.

Tests that already guard the file: foreign keys that must match or the process step stops, the cohort count equals patients minus deaths before 1 January 2026, and the numerator split adds back to the denominator. Two more belong in a production run. Condition codes have to be compared in a type-safe way, because this warehouse stored SNOMED codes as integers and a text comparison returned an empty denominator. The count of patients with two diagnosis dates has to be written next to the study rate, so a later file that gains encounter diagnoses does not silently keep the problem-list percentage.

Access, on a real extract: the analytic table keeps the columns the measure needs and drops direct identifiers (name, address, SSN, subscriber name). The manager report stays aggregated. Warehouse credentials stay out of the repository. This demonstration used a local DuckDB file because the BigQuery client was not available. A production job runs under a service account in the warehouse, with read access limited to the extract and write access limited to the study schemas.

The portfolio README is `README.md`. The case packet asks for that page from a template, and the packet ends without one attached. The README follows the packet's own Ask through Act headings, and it keeps this study separate from the contract packet.
