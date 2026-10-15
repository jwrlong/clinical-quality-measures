# Memorandum

**Portfolio note.** Independent demonstration. The organization is illustrative. This memo is written as an internal note to quality leadership. The counts are from a Synthea extract, not from a health system.

**To:** Vice President, Quality, and Chief Medical Officer
**From:** Quality Analytics
**Date:** 13 October 2026
**Subject:** CBP and GSD denominators cannot be formed from the current extract, and CMS816v5 cannot be scored

## The gap

The specifications need a diagnosis on the encounter, a numeric result, and, for the hospital measure, a medication administration time next to a glucose draw time. In this extract the numeric results are already discrete. Systolic, diastolic, and A1c values are stored as numbers with units. The HEDIS denominators still come out empty, because hypertension and diabetes are written once, when the condition starts, and are not coded on later visits.

The hospital measure has a separate limit. No glucose in 2026 is under 40 mg/dL, and a medication row is a course with a start, a stop, and a dispense count. A course cannot place a dose inside the 24 hours before a draw.

## What the extract showed

The profile in `docs/data-profile.md` applied the written specifications to the Synthea file (Massachusetts, seed 2026, history through 13 October 2026). Measurement year 2026 is incomplete in this file.

- **Controlling High Blood Pressure (HEDIS).** Patients with essential hypertension (SNOMED 59621000) on two qualifying encounters in the identification window: 0. Patients with that condition active in the window: 514. Of those, 387 also have two qualifying visits. The code is on the onset row. Example: patient `4675cf35-1466-3c14-4e58-6ffdc29d6270`, onset 29 October 1977, four qualifying visits in the window, one paired 2026 blood pressure, and no hypertension code on those visits. The contract rate is not calculated.
- **Glycemic Status Assessment for Patients With Diabetes (HEDIS).** Patients with two diabetes diagnosis dates in any non-laboratory setting during 2025 or 2026: 0. Patients with one diagnosis date in that span plus a diabetes medication course that records at least one dispense: 4. Those four are not a contract denominator. A course with a dispense count is the closest field this file has to a pharmacy fill. Type 2 diabetes is active for 163 patients, and 131 of them have two qualifying visits. Each person still has one diagnosis date. Glucose-management indicator rows: 0. A1c values that exist are numeric percents.
- **Hospital Harm — Severe Hypoglycemia (CMS816v5).** Adult inpatient encounters that end in 2026: 60. Glucose results under 40 mg/dL in 2026: 0. On those adult stays the file holds 70 blood or serum glucose results, and the lowest is 64.8 mg/dL. Eleven of the stays overlap an insulin course. Overlap of a course is not an administration. Urine glucose strips are in the file and were ignored. The measure is not scored.

The file is a statewide population with 946 organizations. It does not support a 15-clinic ranking or a three-hospital comparison.

A recount that reused the problem list is in the profile, labeled as a different measure. It is not on the leadership tiles. For that recount, 15 of 105 adults with active diabetes and two visits have no 2026 A1c. The numerator rule would treat a missing result as over 9.0%. That arithmetic stays off the page, because those 105 patients are not the HEDIS denominator.

## What we will do now

The three leadership tiles stay blank, with the failed count printed on the tile. A denominator of zero is not displayed as 0%.

We will not recode the problem list onto the encounters in order to produce a rate. That would answer a different question from the one the contract and CMS ask.

When a production extract is available, the first test is the one this file failed: for patients who have hypertension or diabetes on the problem list and two qualifying visits, does each visit carry the diagnosis as its own coded row? Chart review of that sample records whether the note supports the diagnosis on that date. Confirmed visits can correct a mapping error. They do not become the official rate for patients who were not reviewed.

Membership spans in this file can be tested for a 45-day gap, one payer at a time. They cannot support the institutional exclusion. Plan ownership is self, spouse, or guardian. There is no institutional special-needs flag and no long-term-institution flag.

## What we are asking to fund

Fund encounter diagnosis capture for the two contract measures. The hypertension or diabetes code has to be stored on the visit that is supposed to count, including when the condition has been on the problem list for years. Add a pre-close check that counts patients with the problem and two visits, and counts how many of those visits carry the code. The check fails closed: if the second count is near zero, the rate is withheld.

For CMS816v5, a production feed still has to carry medication administration start times and glucose draw times, in mg/dL, excluding urine. This extract does not justify a meter-interface purchase. The severe-low event is absent here, and the blood pressure and A1c values that are present are already discrete numbers.
