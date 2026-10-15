# Quality measure specifications

**Portfolio note.** This is an independent demonstration for a regional health system with 3 hospitals and about 15 outpatient clinics. The organization is illustrative. The specifications below are plain-language operational definitions for internal quality work. They are not a copy of the licensed HEDIS Volume 2, and they are not a substitute for the CMS eCQM package. Production reporting uses the version locked for the measurement year. Counts from the Synthea extract are in `docs/data-profile.md`. Those counts describe that file. They are not a health system's results. The folder `data/synthetic/` is an earlier hand-built file and is not the analysis dataset.

**Measurement year.** 1 January 2026 through 31 December 2026.

## Where the measures come from

The case names two programs. Both were checked before any measure was specified.

**HEDIS, measurement year 2026.** Published by NCQA for health-plan reporting and used by payers in value-based contracts. Volume 2 for this year was frozen on 31 March 2026. Controlling High Blood Pressure (CBP) and Glycemic Status Assessment for Patients With Diabetes (GSD) are both in that measure set. This health system does not submit HEDIS to NCQA. Payers score the system on these measures.

**CMS hospital inpatient eCQMs, 2026 reporting period.** Published by CMS for electronic hospital quality reporting. The 2026 inpatient set contains 17 measures. Hospital Harm — Severe Hypoglycemia (CMS816v5) is in that set. Source: CMS, *2026 Electronic Clinical Quality Measures for Hospitals — Inpatient*, May 2025.

| Measure | Program | Status in this document |
| --- | --- | --- |
| Controlling High Blood Pressure (CBP) | HEDIS MY 2026 | Specified below |
| Glycemic Status Assessment for Patients With Diabetes (GSD) | HEDIS MY 2026 | Specified below |
| Hospital Harm — Severe Hypoglycemia (CMS816v5) | CMS eCQM, 2026 | Specified below |

CBP is a HEDIS measure only. It does not appear in the CMS hospital eCQM set, because that set covers inpatient care.

---

## 1. Controlling High Blood Pressure (CBP)

**Program.** HEDIS, measurement year 2026.
**Steward.** National Committee for Quality Assurance.
**Setting.** Outpatient clinics.
**Used for.** Value-based contracts with payers.

### What it measures and why it matters

CBP is the percentage of adults 18 to 85 with hypertension whose most recent eligible blood pressure in the measurement year is below 140/90 mm Hg.

Uncontrolled hypertension drives stroke, heart attack, and heart failure admissions. For this system, the rate is a contract measure across the clinics, not a hospital measure. A clinic can look busy and still fail the contract if the latest eligible reading is high, missing, or stored in a form the measure cannot use. A missing reading is not a neutral gap. The patient counts as not controlled.

### Numerator and denominator

This is the HEDIS population. The official payer rate also depends on membership data the EHR does not hold. Those pieces are called out so an internal clinic rate is not presented as the contract rate.

**Denominator.** Patients who meet all of the following:

- Age 18 through 85 on 31 December 2026.
- Continuously enrolled with the contracting payer during 2026, with no more than one gap of up to 45 days, and still enrolled on 31 December 2026. This rule comes from the payer membership file.
- At least two qualifying encounters on different dates of service between 1 January 2025 and 30 June 2026, each carrying a hypertension diagnosis from the HEDIS hypertension value set. Qualifying encounters are outpatient visits, telephone visits, and online assessments. The diagnosis is part of each visit. A problem-list onset that is not tied to two visit dates does not meet this event.

**Where this event was checked.** NCQA publishes the event as a visit value set combined with the Essential Hypertension value set, and the reading is taken on or after the second diagnosis. Measurement-year 2026 guides from Blue Cross NC, Priority Health, BCBST, Carolina Complete Health, and BCBSND use that event. The licensed Volume 2 was not the copy open for this check. Production reporting still uses that volume.

**Numerator.** Patients in the denominator whose most recent eligible blood pressure in 2026 is controlled.

- The reading must fall on or after the date of the second hypertension diagnosis.
- Controlled means systolic under 140 mm Hg and diastolic under 90 mm Hg.
- If several readings share the same date, use the lowest systolic and the lowest diastolic on that date. They may come from different readings.
- A distinct number is required for both systolic and diastolic. A range or a threshold does not count. An average that is written as two numbers, such as 139/70, can count.
- A reading taken by the patient on a digital device counts when it is documented in the record. A reading the patient took on a non-digital device does not.

**Not numerator compliant.** The latest eligible reading is 140/90 or higher, either number is missing, or there is no eligible reading in 2026.

**Readings that cannot be used:**

- Taken during an acute inpatient stay.
- Taken during an emergency department visit.
- Taken the same day as a diagnostic test or procedure that required a diet or medication change that day or the day before, other than a fasting blood test.

**Remove the patient from the measure when any of these apply:**

- Died during 2026.
- Hospice or palliative care during 2026.
- Pregnancy diagnosis during 2026.
- Nonacute inpatient admission during 2026.
- End-stage renal disease, dialysis, nephrectomy, or kidney transplant at any time through 31 December 2026.
- Age 66 or older and enrolled in an institutional special needs plan, or living long-term in an institution, during 2026. These flags come from the payer enrollment file.
- Age 81 or older with frailty during 2026.
- Age 66 to 80 with frailty during 2026 and advanced illness during 2025 or 2026, including a dispensed dementia medication.

Code lists, including the hypertension value set and the CPT Category II blood pressure codes used on claims, come from the HEDIS MY 2026 Value Set Directory. They are not restated here. Category II codes can support a payer’s claims calculation. They are categories, not a numeric result, so they do not replace a systolic and diastolic value in the EHR calculation.

### Data elements needed from the EHR

| Element | What the measure uses it for |
| --- | --- |
| Date of birth, and date of death if recorded | Age on 31 December 2026, and the death exclusion |
| Encounter date, type, and setting | The two hypertension encounters, and rejection of inpatient and emergency readings |
| Diagnosis code on the encounter | Hypertension in the identification window; pregnancy; end-stage renal disease |
| Problem list and procedure history | Kidney transplant, nephrectomy, dialysis, and older hypertension evidence that never landed on an encounter |
| Systolic value, diastolic value, result date and time, and the encounter the reading belongs to | Selecting the most recent eligible reading and applying the 140/90 rule |
| How the reading was obtained | Separating a documented digital home reading from a non-digital home reading, and from a free-text note |
| Palliative care and hospice documentation | Required exclusions |
| Frailty and advanced-illness diagnoses | Required exclusions for older adults |

**Not in the EHR, and still required for the contract rate.** Payer membership and continuous enrollment, institutional special needs plan and long-term institution flags, and pharmacy dispenses for dementia medications. An internal rate built only from the EHR will not match the payer’s official CBP rate.

### Data quality issues that miscount patients

- **One hypertension code is treated as enough.** The denominator needs two qualifying encounters with the diagnosis, on different dates, inside 1 January 2025 through 30 June 2026. A problem-list entry alone does not create those encounters. Patients are dropped, or, if any hypertension code is accepted, patients are added who do not belong.
- **The wrong reading wins.** Using the latest reading in the chart, rather than the latest eligible reading, pulls in an inpatient or emergency value. Using the last pair on a date, rather than the lowest systolic and the lowest diastolic, marks a patient uncontrolled after a repeat reading that was actually controlled.
- **The reading is real and still unusable.** “140s/80s,” “elevated,” or a blood pressure typed only in the progress note has no distinct systolic and diastolic. The patient falls into the numerator failure group, which looks like uncontrolled hypertension.
- **A reading before the second diagnosis is used.** Control is assessed only on or after that second date. An earlier good reading makes the rate look better than the specification allows.
- **Home readings are mixed together.** A digital-cuff reading documented in the record can count. A non-digital reading cannot. If the source is not stored, the measure either drops valid control or accepts a reading the specification rejects.
- **Exclusions are incomplete.** Pregnancy, hospice, palliative care, and end-stage renal disease often sit in notes or outside records. Those patients stay in the denominator. Frailty and institutional status are especially easy to miss because much of that evidence is on claims and enrollment files.
- **The clinic rate is labeled as the contract rate.** Without the membership file, patients who failed continuous enrollment remain in an internal denominator. Leadership then compares the wrong population with the payer’s score.

### How to validate against chart review

Review charts before the rate is shown as a contract result. The review tests whether the calculated status matches the record, not whether the clinician treated the patient well.

1. Take a random sample from the calculated population, with separate groups for controlled, not controlled, and no usable reading. Include patients the logic excluded, so missed exclusions are visible.
2. Give the abstractor the measurement year, the identification window, and the reading rules above. Do not show the calculated status.
3. The abstractor records: whether two qualifying hypertension encounters exist in the window, the date of the second diagnosis, every blood pressure in 2026 with setting and source, which reading the rules select, the systolic and diastolic used, and any exclusion.
4. Compare the abstractor’s status with the calculated status. Classify each mismatch as one of: patient should not be in the denominator, exclusion missed, ineligible reading used, wrong same-day reading selected, numeric result missed in free text, or reading taken before the second diagnosis.
5. Use the mismatches to fix the logic or the capture problem. Repeat the sample on the corrected logic. The rate can go to clinical leaders when the remaining mismatches are understood and the dashboard says which population it represents: EHR clinic rate, or payer-aligned rate that also applies membership rules.

---

## 2. Glycemic Status Assessment for Patients With Diabetes (GSD)

**Program.** HEDIS, measurement year 2026.
**Steward.** National Committee for Quality Assurance.
**Setting.** Outpatient clinics.
**Used for.** Value-based contracts with payers.

### What it measures and why it matters

GSD is the percentage of adults 18 to 75 with type 1 or type 2 diabetes whose most recent glycemic status in the measurement year falls at one of two levels. Glycemic status means a hemoglobin A1c or a glucose management indicator (GMI) from a continuous glucose monitor.

The measure has two rates, and they share one denominator:

- **Glycemic status under 8.0%.** A higher rate is better.
- **Glycemic status over 9.0%.** A lower rate is better. A missing result, or no test in the year, counts in this rate.

A result from 8.0% through 9.0%, including both of those numbers, is in neither rate. Reporting only one of them hides that middle group.

For contract conversations, the over 9.0% rate is the one that changes decisions. It is the rate a missing lab inflates. A clinic that ordered the test, and never got a discrete result back, looks the same as a clinic whose patients are markedly above goal. Both rates have to be calculated together, with the same data method, so leadership can see how much of the poor-control rate is a result over 9.0% and how much is no usable result.

### Numerator and denominator

This is the HEDIS population. Membership data still sit outside the EHR. An internal clinic rate and the payer’s official rate are different populations and should be labeled as such.

**Denominator.** Patients who meet all of the following, and who are not removed by an exclusion:

- Age 18 through 75 on 31 December 2026.
- Continuously enrolled with the contracting payer during 2026, with a medical benefit, no more than one gap of up to 45 days, and still enrolled on 31 December 2026. This rule comes from the payer membership file.
- Diabetes identified in 2025 or 2026 by at least one of these methods. Search both methods. Either one is enough.
  - **Encounters.** Two diagnoses of diabetes, from the HEDIS diabetes value set, on different dates of service, in any setting. Do not count a laboratory claim (place of service 81) as one of those diagnoses. The setting is not limited to an outpatient visit.
  - **Pharmacy.** One diabetes diagnosis from that same value set during 2025 or 2026, plus one dispensing event for insulin or another diabetes medication on the HEDIS diabetes medication list during that same span. An order in the EHR is not a dispensing event. An onset dated before 2025 does not supply the diagnosis date.

**Where this event was checked.** NCQA's current glycemic-status event counts two diagnosis dates in any setting, or one diagnosis date plus a dispensing event, both inside the measurement year or the year before it. Laboratory claims are excluded. The same Volume 2 limit applies.

**Both rates use the same test.** Find the most recent A1c or GMI in 2026. If results from the EHR, claims, and supplemental files are combined, the most recent result wins regardless of which file it came from. If several results share a date, use the lowest result.

A usable result has a test type, a date, and a distinct number. A range, a threshold, or the word “unknown” is not a result. For a GMI, the record also has to include the continuous-glucose-monitor date range the value came from. The last date in that range is the test date, not the day someone typed the number in. A GMI the patient collected counts when it is documented in the record. It does not have to have been collected by a primary care clinician or a specialist.

**Rate 1, under 8.0%.** The patient is in the numerator when that most recent result is under 8.0%. The patient is out of the numerator when the result is 8.0% or higher, the result is missing, or no test was done in 2026.

**Rate 2, over 9.0%.** The patient is in the numerator when that most recent result is over 9.0%, the result is missing, or no test was done in 2026. The patient is out of the numerator only when the most recent result is 9.0% or lower.

If the most recent evidence is a CPT Category II code rather than a number, the category decides the rate. Codes with a Category II modifier do not count. A code for a result over 9.0% places the patient in the over 9.0% numerator. A code for a result under 8.0% places the patient in the under 8.0% numerator. A code for 8.0% through 9.0% places the patient in neither numerator.

**Remove the patient from the measure when any of these apply:**

- Died during 2026.
- Hospice, or a hospice benefit, during 2026.
- Palliative care during 2026, including an encounter coded Z51.5.
- Age 66 or older, covered by Medicare, and enrolled in an institutional special needs plan or living long-term in an institution during 2026. These flags come from the payer enrollment file.
- Age 66 or older, with at least two indications of frailty on different dates during 2026, and advanced illness. Advanced illness means two advanced-illness diagnoses on different dates in 2025 or 2026, or a dispensed dementia medication.

Code lists, including the diabetes value set, the diabetes medication list, and the A1c result codes, come from the HEDIS MY 2026 Value Set Directory and Medication List Directory. They are not restated here. GMI is identified with LOINC 97506-0.

### Data elements needed from the EHR

| Element | What the measure uses it for |
| --- | --- |
| Date of birth, and date of death if recorded | Age on 31 December 2026, and the death exclusion |
| Encounter date and diagnosis code | The two diabetes diagnoses in 2025 or 2026. Laboratory-only claims are not diagnosis events |
| Problem list | Supporting clinical context. A problem-list entry alone does not supply two diagnosis dates, and an onset before 2025 does not supply the pharmacy-path diagnosis date |
| A1c result, numeric value, test date, and LOINC or local test code | The most recent glycemic status, and which rate the patient falls in |
| GMI result, the monitor’s date range, and the last date in that range | Dating a continuous-glucose-monitor result and comparing it with A1c dates |
| Where the result lives | Separating a discrete lab result from a scanned report, a portal note, or a device screenshot |
| Hospice and palliative-care documentation | Required exclusions |
| Frailty and advanced-illness diagnoses | Required exclusions for adults 66 and older |

**Not in the EHR, and still required for the contract rate.** Payer membership and continuous enrollment, Medicare and institutional flags, and pharmacy dispenses for diabetes medications and dementia medications. A medication the clinician ordered, or a medication the patient says they take, does not by itself meet the pharmacy path into the denominator.

### Data quality issues that miscount patients

- **The denominator is built from the wrong diabetes evidence.** One diagnosis date, or a problem-list entry alone, is not the two-date method. A laboratory claim billed as place of service 81 is not a diagnosis event. Using it adds patients who only had a rule-out test. Ignoring the pharmacy path drops patients who have one diagnosis and a filled diabetes medication. An onset from before the two-year window does not count as the pharmacy-path diagnosis.
- **An order is treated as a fill.** The pharmacy path requires a dispensing event. An active medication on the list, or an order that was never filled, puts the patient in the denominator early.
- **The best result of the year is used.** The measure uses the most recent result. A well-controlled A1c in March does not count if a later result is higher. Across files, the latest date wins even when an older result is the only one stored as a clean number.
- **Same-day results are averaged or the last one is kept.** Several results on one date resolve to the lowest result, not the average and not the last one entered.
- **A real result is stored as words.** “A1c about 7,” “good control,” or a range has no distinct number, so the test does not count. On the over 9.0% rate that patient joins the numerator. The dashboard then shows poor control when the chart shows a test the interface never captured.
- **The GMI is dated on the wrong day.** Without the monitor’s date range, the terminal date is unknown. Using the day the value was typed, or the day a PDF arrived, can make an older GMI look like the most recent test and can hide a newer A1c.
- **External and point-of-care results never become discrete.** Retail labs, hospital labs outside this EHR, and clinic point-of-care devices often land as scanned documents. The clinician can read them. The measure cannot, and the patient counts as untested.
- **The two rates are collapsed.** A result of 8.4% fails the under 8.0% rate and does not belong in the over 9.0% rate. Publishing a single “diabetes control” number assigns that patient to the wrong story.
- **Exclusions and enrollment are incomplete.** Hospice, palliative care, frailty, and institutional status are easy to miss in the EHR. Patients who were not continuously enrolled stay in an internal denominator and make the clinic rate diverge from the payer’s score.

### How to validate against chart review

GSD can be validated with chart review because the official measure allows a hybrid method: claims identify the denominator, and the record can supply the result. The review checks whether the calculated status matches the documentation.

1. Draw a random sample from the calculated denominator. Keep separate groups for under 8.0%, 8.0% through 9.0%, over 9.0% with a numeric result, and over 9.0% because no usable result was found. Include patients the logic excluded.
2. Give the abstractor the measurement year, both identification methods, and the result rules above. Do not show the calculated rates.
3. The abstractor records: how diabetes was identified, any exclusion, and every A1c or GMI in 2026 with test type, date, numeric result, and, for a GMI, the monitor date range. The abstractor also notes results that exist only in a note, a scan, or a device image.
4. Compare the abstractor’s two rates with the calculated rates. Classify each mismatch as one of: patient should not be in the denominator, laboratory claim used as a diagnosis, exclusion missed, older result used, same-day result chosen incorrectly, GMI dated on the entry date, numeric result trapped in a document, or a range treated as a number.
5. Separate mismatches that need a logic fix from mismatches that need an interface or scanning fix. Repeat the sample after the correction. Show leaders both rates, and show what share of the over 9.0% rate has no usable result. Label the population as an EHR clinic rate or as a payer-aligned rate that also applies membership and dispensing rules.

---

## 3. Hospital Harm — Severe Hypoglycemia (CMS816v5)

**Program.** CMS hospital inpatient eCQM, 2026 reporting period. Version 5.1.000.
**Steward.** Centers for Medicare & Medicaid Services. Developed by Mathematica.
**Setting.** Inpatient hospitalizations at the three hospitals, including emergency department and observation time when that care is contiguous with the admission.
**Used for.** CMS electronic hospital quality reporting.
**Score.** Proportion of hospitalizations. A lower rate is better. The measure has no denominator exclusions, no numerator exclusions, and no risk adjustment.

Source for the logic below: the CMS816v5 specification published for the 2026 reporting period on the eCQI Resource Center. Value set members are not copied here. Production submission uses that specification and the value sets named in it.

### What it measures and why it matters

CMS816v5 is the percentage of adult inpatient hospitalizations in which the patient received at least one hypoglycemic medication and then had a severe low glucose that the measure accepts as harm.

Severe means a laboratory, point-of-care, or continuous-glucose-monitor result under 40 mg/dL, after a qualifying medication, and not followed by a near-term repeat that shows the first result was a false low. Urine glucose does not count.

Inpatient hypoglycemia is a common medication harm. It is associated with longer stays and higher cost, and hospitals can prevent much of it by how they use insulin and other glucose-lowering drugs. CMS uses the rate as a hospital outcome. For this system it is the inpatient reporting measure, one rate for each hospital. A decline is improvement only when the timestamps and the units are trustworthy. A glucometer clock or a unit conversion can move the rate without any change in nursing practice.

The rate counts hospitalizations, not low-glucose events. Several qualifying lows during one stay still count once.

### Numerator and denominator

The population is the hospital encounter. Membership files are not part of this measure.

**Denominator.** An inpatient encounter that meets all of the following:

- The encounter ends on a date in 2026. An admission in late 2025 counts when the discharge is in 2026. An admission in 2026 that discharges in 2027 does not.
- The patient is age 18 or older at the start of the inpatient encounter. Age is not calculated at emergency department arrival and not at discharge.
- At least one hypoglycemic medication administration starts during the hospitalization. The medication must be in the CMS value set Hypoglycemics Severe Hypoglycemia (OID 2.16.840.1.113762.1.4.1196.393). An order, a home medication list, or a held dose does not count. The administration has to be recorded as given.

The hospitalization window is longer than the inpatient admission timestamp when emergency department or observation care connects to it. Pull in the last observation encounter that ends no more than one hour before the inpatient start. Then pull in the last emergency encounter that ends no more than one hour before that observation, or before the inpatient start when there is no observation. The window runs from the start of that earliest connected encounter through the inpatient discharge. A gap longer than one hour leaves the earlier glucose and medication outside the measure.

**Numerator.** Denominator hospitalizations with at least one severe hypoglycemic harm event. All three of the following are required:

- A glucose result under 40 mg/dL from the CMS value set Glucose Lab Test Mass Per Volume (OID 2.16.840.1.113762.1.4.1248.34). The result must be in mg/dL. A result reported in mmol/L is converted before the comparison (mg/dL equals mmol/L times 18). A result of exactly 40 mg/dL does not qualify. The specimen time is the time the glucose was drawn, or the start of the test period, not the time the laboratory posted the result. That time must fall inside the hospitalization window. Laboratory blood, point-of-care capillary tests, and interstitial results from a continuous glucose monitor can qualify. Urine glucose cannot.
- A qualifying medication administration that starts during the hospitalization window and starts no more than 24 hours before that draw, or at the same time as the draw. The submitted specification times this from the start of the administration. A local rule that instead uses the end of an infusion, or that counts a drip still running from the day before, will not match the CMS rate.
- No different glucose test, also inside the hospitalization window, with a result over 80 mg/dL and a draw time no more than five minutes after the low result. A repeat of exactly 80 mg/dL does not remove the event. The five-minute check exists to drop false lows from point-of-care testing.

One qualifying event puts the hospitalization in the numerator. Further events in that same stay do not raise the count.

Nothing removes a hospitalization from the denominator. Comfort care, hospice discharge, and a low glucose present on arrival are not exclusions in this specification. Those rules belong to other hospital-harm measures and must not be added here.

### Data elements needed from the EHR

| Element | What the measure uses it for |
| --- | --- |
| Inpatient encounter start and end | Age at inpatient start, and whether the discharge falls in 2026 |
| Emergency and observation encounter start and end | Extending the hospitalization window when the gap to the next encounter is one hour or less |
| Date of birth | Age of 18 or older at the inpatient start |
| Medication administration code, action, and start time | A drug in the hypoglycemic value set, documented as given, with a start inside the window |
| Glucose test code, specimen type, numeric result, unit, and draw time | The under-40 result, rejection of urine glucose, and both clocks (24 hours and 5 minutes) |
| A second glucose result and its draw time | The false-low check: over 80 mg/dL within five minutes |
| Payer, race, ethnicity, and sex | Required supplemental data elements on the CMS submission. They do not change the rate |

**Mapping belongs to the named value sets.** Local medication codes and local glucose codes have to map to the two OIDs above. A drug or a test that clinicians treat as in scope, and that is not in the value set, will not be in the submitted rate.

### Data quality issues that miscount patients

- **An order is counted as a dose given.** The denominator and the 24-hour link both require an administration. Counting orders adds hospitalizations in which the drug was never given. Dropping administrations that were scanned late removes real exposure.
- **The laboratory result time is used as the draw time.** Both clocks run from the specimen time. A result that posts 20 minutes later can miss the five-minute repeat window, so a false low remains in the numerator, or can fall outside the 24-hour medication window, so a real harm drops out.
- **The unit is wrong.** A value stored in mmol/L and compared with 40 as if it were mg/dL will not describe the patient’s glucose. Convert before the threshold. Do not mix the two units in one field.
- **The repeat glucose never arrives as its own test.** Point-of-care false lows are supposed to fall out when a different test exceeds 80 mg/dL within five minutes. If the repeat stays in the meter, posts at six minutes because of clock drift, or is filed as a comment on the first result, the hospitalization is scored as harm.
- **Emergency and observation time is stitched on the wrong gap.** A gap of one hour or less joins that care to the inpatient stay. A longer gap does not. Using the arrival-to-discharge story without the one-hour rule pulls in, or drops, insulin and glucoses from the emergency department.
- **The wrong specimen is mapped.** Urine glucose is out. Capillary, serum, plasma, and interstitial continuous-monitor results that sit in the glucose value set are in. Mapping a urine dipstick into that value set creates false harm. Leaving point-of-care meters unmapped hides real harm.
- **Every low glucose is counted.** The CMS rate counts the hospitalization once. A unit-level count of every result under 40 mg/dL is a different measure and will not match the submitted rate.
- **Another harm measure’s exclusions are borrowed.** This specification has none. Removing comfort-care patients, hospice discharges, or lows present on arrival makes an internal rate that CMS will not reproduce.
- **Infusion timing is rewritten locally.** The administration must start inside the hospitalization and start no more than 24 hours before the draw. Treating “still infusing” as enough will include drips whose start is too early, and the hospital’s rate will diverge from the CMS calculation.

### How to validate against chart review

Review the record against the calculated status before the hospital rate is treated as a safety result. The question is whether the encounter met the specification, not whether the clinical response to the low glucose was adequate.

1. Sample calculated denominator hospitalizations and calculated numerator hospitalizations. Add hospitalizations the logic kept out for a specific reason: repeat glucose over 80 mg/dL within five minutes, medication start outside 24 hours, glucose of 40 mg/dL or higher only, and encounters whose emergency department gap was just over one hour.
2. Give the abstractor the window rules, the two thresholds, and the value set names. Do not show the calculated status.
3. The abstractor records the inpatient start and end, any emergency or observation encounter and the gap in minutes, each hypoglycemic administration with its start time and whether it was given, and each glucose with specimen type, unit, result, and draw time. Repeats within five minutes are recorded as separate tests.
4. Compare the abstractor’s status with the calculated status. Classify each mismatch as one of: order used instead of an administration, result time used instead of draw time, unit not converted, repeat glucose missing from the extract, emergency or observation window joined incorrectly, urine or other out-of-set test included, encounter discharged outside 2026, or more than one event counted for one stay.
5. Fix logic mismatches and interface mismatches separately. Repeat the sample. Report one rate per hospital, state that a lower rate is better, and state that the rate counts hospitalizations with at least one qualifying event. Keep a separate operational count of events only if it is labeled as an internal safety tally and not as CMS816v5.
