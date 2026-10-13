# Memorandum

**Portfolio note.** Independent demonstration. The organization is illustrative. This memo is written as an internal note to quality leadership.

**To:** Vice President, Quality, and Chief Medical Officer
**From:** Quality Analytics
**Date:** 12 October 2026
**Subject:** Point-of-care and patient-generated results are not usable for CBP, GSD, or CMS816v5

## The gap

The EHR often contains the clinical fact and still cannot feed the measure. A blood pressure, an A1c, a glucose-monitor summary, or a bedside glucose is in a note, a scanned report, or a meter download. The measure needs a discrete number, a test type, and a time. Those three fields are missing or are stored on the wrong clock.

This is one capture problem with three consequences. The figures in the next section come from the synthetic extract profiled for this project. Documentation failures were planted so they could be counted. They are not rates from a health system.

- **Controlling High Blood Pressure (HEDIS).** The rate uses the latest eligible 2026 reading with a distinct systolic and diastolic. A repeat clinic pressure or a home reading typed as prose has no values the logic can select, and no source to show that a home reading came from a digital device. The patient counts as not controlled.
- **Glycemic Status Assessment for Patients With Diabetes (HEDIS).** The over 9.0% rate counts a missing result as poor control. A point-of-care A1c in a progress note, an outside lab sitting as a PDF, or a patient glucose-management indicator without the monitor’s date range never becomes the most recent result. The contract rate rises because the result was not captured, not because the latest value was over 9.0%.
- **Hospital Harm — Severe Hypoglycemia (CMS816v5).** The false-low check requires a different glucose over 80 mg/dL within five minutes of a result under 40 mg/dL, timed from the draw. That repeat is usually a point-of-care test. When it stays on the meter, posts late, or is typed as a comment on the first result, a false low remains in the numerator and the hospitalization is reported as harm.

## What the extract showed

The profile in `docs/data-profile.md` applied the measure specifications to the file.

- **CBP.** Of 540 patients in the EHR denominator, 30 are not controlled because the 2026 blood pressure is text with no systolic or diastolic. Example: patient P1061, clinic 06, note "BP 132/78 today." Another 30 are not controlled because the only reading is from a non-digital home device. That second group is the specification, not a missing interface. The EHR rate is 360 / 540 (66.7%). The payer-aligned rate is 330 / 510 (64.7%).
- **GSD.** Of 270 patients in the EHR denominator, 45 have no usable result and therefore sit in the over-9.0% rate: 15 notes, 15 scanned documents, and 15 glucose-management indicators with a number and no monitor date range. They are 45 of the 87 patients in that rate. Fifteen more are scored on an older A1c of 9.4% while a later result is stuck in a note. The EHR over-9.0% rate is 87 / 270 (32.2%).
- **CMS816v5.** The pooled rate is 20 / 486 hospitalizations (4.1%). One of those numerator stays, at Hospital B, has a repeat of 110 mg/dL three minutes later that exists only on the meter file. The same event at Hospital A is not in the numerator, because the repeat reached the extract. The Hospital C stay is in the numerator for a different reason: its repeat is in the extract and is six minutes later, outside the rule.

Clinics 06 through 10 are the weak end of both contract measures in this file. That is where the planted text, notes, and scans were assigned. The split above is what keeps that ranking from being read as worse clinical control.

## What we will do now

We will not relax the specifications to read free text into the official rate. A note can nominate a chart for review. It cannot silently change a HEDIS result or a CMS submission.

Until device interfaces are in place, reporting carries three controls.

1. **Show the missing-result share next to the rate.** On the leadership page, CBP shows the share of the denominator with no usable blood pressure. GSD splits the over 9.0% rate into a numeric result over 9.0% and no usable result. Leaders can see how much of the rate is capture.
2. **Review the charts this gap affects.** For CBP and GSD, abstract the “no usable result” sample already defined in the measure specifications, and record values that exist only in notes or scans. For CMS816v5, review numerator stays whose low glucose is a point-of-care result, and check the meter for a repeat within five minutes. Confirmed values are used in the validated rate. They are not imputed for stays that were not reviewed.
3. **Label the population.** The HEDIS figures remain an EHR clinic rate until membership and dispensing files are applied. CMS816v5 remains the hospitalization rate in the specification, not a count of every glucose under 40 mg/dL.

## What we are asking to fund

Interface the clinic glucometers, point-of-care A1c devices, and hospital bedside meters so each result lands as its own observation: numeric value, unit, specimen type, and device time. Add two structured documentation fields. Home blood pressure stores systolic, diastolic, and whether the device was digital. A patient glucose-management indicator stores the number and the monitor date range, and the measure dates the result on the last day of that range.

That is the workaround that removes the gap. Chart review covers the year now in progress. It does not scale to every clinic visit, and it will not see a bedside repeat that was never exported from the meter.
