"""Profile the synthetic extract and write the measurement-year data profile."""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from measures import evaluate_cbp, evaluate_cms816, evaluate_gsd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "synthetic"
PROFILE = ROOT / "docs" / "data-profile.md"
SUMMARY = ROOT / "outputs" / "measure_results.json"


def load(name):
    with (DATA / name).open(newline="") as handle:
        return list(csv.DictReader(handle))


def parse_date(value):
    if not value:
        return None
    return date.fromisoformat(value[:10])


def parse_dt(value):
    if not value:
        return None
    return datetime.fromisoformat(value)


def parse_num(value):
    if value is None or value == "":
        return None
    return float(value)


def parse_bool(value):
    return value == "true"


def pct(numerator, denominator):
    if not denominator:
        return "n/a"
    return f"{(100 * numerator / denominator):.1f}%"


def fraction(numerator, denominator):
    return f"{numerator} / {denominator} ({pct(numerator, denominator)})"


def prepare():
    patients = []
    for row in load("patients.csv"):
        patients.append({
            "patient_id": row["patient_id"],
            "cohort": row["cohort"],
            "scenario": row["scenario"],
            "birth_date": parse_date(row["birth_date"]),
            "death_date": parse_date(row["death_date"]),
            "clinic_id": row["clinic_id"],
        })
    spans = defaultdict(list)
    for row in load("enrollment_spans.csv"):
        spans[row["patient_id"]].append({
            "span_start": parse_date(row["span_start"]),
            "span_end": parse_date(row["span_end"]),
            "medical_benefit": parse_bool(row["medical_benefit"]),
            "product_line": row["product_line"],
            "isnp": parse_bool(row["isnp"]),
            "lti": parse_bool(row["lti"]),
        })
    encounters = []
    by_patient_enc = defaultdict(list)
    for row in load("encounters.csv"):
        item = {
            "encounter_id": row["encounter_id"],
            "patient_id": row["patient_id"],
            "encounter_class": row["encounter_class"],
            "start": parse_dt(row["start_datetime"]),
            "end": parse_dt(row["end_datetime"]),
            "facility_id": row["facility_id"],
            "place_of_service": row["place_of_service"],
            "scenario": row["scenario"],
        }
        encounters.append(item)
        by_patient_enc[row["patient_id"]].append(item)
    diagnoses = defaultdict(list)
    for row in load("diagnoses.csv"):
        diagnoses[row["patient_id"]].append({
            "encounter_id": row["encounter_id"],
            "concept": row["concept"],
            "recorded_date": parse_date(row["recorded_date"]),
        })
    bps = defaultdict(list)
    for row in load("blood_pressures.csv"):
        bps[row["patient_id"]].append({
            "taken_at": parse_dt(row["taken_at"]),
            "systolic": parse_num(row["systolic"]),
            "diastolic": parse_num(row["diastolic"]),
            "source": row["source"],
            "setting": row["setting"],
            "capture": row["capture"],
            "procedure_diet_change": parse_bool(row["procedure_diet_change"]),
        })
    glycemic = defaultdict(list)
    for row in load("glycemic_results.csv"):
        glycemic[row["patient_id"]].append({
            "analyte": row["analyte"],
            "value": parse_num(row["value"]),
            "unit": row["unit"],
            "capture": row["capture"],
            "result_date": parse_date(row["result_date"]),
            "gmi_range_end": parse_date(row["gmi_range_end"]),
        })
    glucoses = defaultdict(list)
    for row in load("glucose_results.csv"):
        glucoses[row["patient_id"]].append({
            "result_id": row["result_id"],
            "drawn_at": parse_dt(row["drawn_at"]),
            "value": parse_num(row["value"]),
            "unit": row["unit"],
            "specimen": row["specimen"],
            "in_glucose_value_set": parse_bool(row["in_glucose_value_set"]),
            "capture": row["capture"],
        })
    admins = defaultdict(list)
    for row in load("med_administrations.csv"):
        admins[row["patient_id"]].append({
            "action": row["action"],
            "in_hypoglycemic_value_set": parse_bool(row["in_hypoglycemic_value_set"]),
            "start": parse_dt(row["start_datetime"]),
        })
    dispenses = defaultdict(list)
    for row in load("med_dispenses.csv"):
        dispenses[row["patient_id"]].append({
            "drug_class": row["drug_class"],
            "fill_date": parse_date(row["fill_date"]),
        })
    meter = defaultdict(list)
    for row in load("meter_held_glucose.csv"):
        meter[row["patient_id"]].append({
            "result_id": row["held_id"],
            "drawn_at": parse_dt(row["drawn_at"]),
            "value": parse_num(row["value"]),
            "unit": row["unit"],
            "specimen": row["specimen"],
            "in_glucose_value_set": parse_bool(row["in_glucose_value_set"]),
            "capture": row["capture"],
        })
    facilities = {row["facility_id"]: row["facility_name"] for row in load("facilities.csv")}
    return {
        "patients": patients,
        "spans": spans,
        "encounters": encounters,
        "by_patient_enc": by_patient_enc,
        "diagnoses": diagnoses,
        "bps": bps,
        "glycemic": glycemic,
        "glucoses": glucoses,
        "admins": admins,
        "dispenses": dispenses,
        "meter": meter,
        "facilities": facilities,
        "raw_counts": {
            "patients": len(patients),
            "encounters": len(encounters),
            "blood_pressures": sum(len(v) for v in bps.values()),
            "glycemic_results": sum(len(v) for v in glycemic.values()),
            "glucose_results": sum(len(v) for v in glucoses.values()),
            "meter_held": sum(len(v) for v in meter.values()),
        },
    }


def run(data):
    cbp = []
    gsd = []
    cms = []
    for person in data["patients"]:
        pid = person["patient_id"]
        if person["cohort"] == "cbp":
            cbp.append(evaluate_cbp(
                person, data["by_patient_enc"][pid], data["diagnoses"][pid], data["bps"][pid], data["spans"][pid], data["dispenses"][pid]
            ))
        elif person["cohort"] == "gsd":
            gsd.append(evaluate_gsd(
                person, data["by_patient_enc"][pid], data["diagnoses"][pid], data["glycemic"][pid], data["spans"][pid], data["dispenses"][pid]
            ))
        elif person["cohort"] == "cms":
            for encounter in data["by_patient_enc"][pid]:
                if encounter["encounter_class"] != "inpatient":
                    continue
                cms.append(evaluate_cms816(
                    encounter, person, data["by_patient_enc"][pid], data["admins"][pid], data["glucoses"][pid], data["meter"][pid]
                ))
    check(cbp, gsd, cms)
    return cbp, gsd, cms


def by_scenario(rows, scenario):
    return [row for row in rows if row["scenario"] == scenario]


def check(cbp, gsd, cms):
    for row in by_scenario(cbp, "note_only"):
        assert row["in_ehr_denominator"] and row["no_usable_bp"] and row["controlled"] is False
    for row in by_scenario(cbp, "pregnancy"):
        assert row["exclusion"] == "pregnancy" and not row["in_ehr_denominator"]
    for row in by_scenario(cbp, "one_visit"):
        assert not row["in_ehr_denominator"]
    for row in by_scenario(cbp, "enrollment_gap"):
        assert row["in_ehr_denominator"] and not row["in_payer_denominator"] and row["controlled"]
    for row in by_scenario(gsd, "lab_claim_only"):
        assert not row["in_ehr_denominator"]
    for row in by_scenario(gsd, "gmi_no_range"):
        assert row["band"] == "missing"
    for row in by_scenario(gsd, "newer_result_trapped"):
        assert row["band"] == "gt9" and row["trapped_later_result"]
    for row in by_scenario(gsd, "note_only"):
        assert row["band"] == "missing"
    false_lows = by_scenario(cms, "false_low")
    by_facility = {row["facility_id"]: row for row in false_lows}
    assert by_facility["H01"]["in_numerator"] is False
    assert by_facility["H02"]["in_numerator"] and by_facility["H02"]["meter_would_remove"]
    assert by_facility["H03"]["in_numerator"] and by_facility["H03"]["clearance"] == "repeat_outside_five_minutes"
    for row in by_scenario(cms, "glucose_40"):
        assert row["in_denominator"] and not row["in_numerator"]
    for row in by_scenario(cms, "order_not_given"):
        assert not row["in_denominator"]


def clinic_table(rows, facilities):
    grouped = defaultdict(list)
    for row in rows:
        if row["in_ehr_denominator"]:
            grouped[row["clinic_id"]].append(row)
    lines = []
    for clinic_id in sorted(grouped):
        group = grouped[clinic_id]
        controlled = sum(1 for row in group if row["controlled"])
        no_usable = sum(1 for row in group if row["no_usable_bp"])
        lines.append({
            "clinic_id": clinic_id,
            "name": facilities.get(clinic_id, clinic_id),
            "denominator": len(group),
            "controlled": controlled,
            "rate": controlled / len(group),
            "no_usable": no_usable,
        })
    lines.sort(key=lambda item: (item["rate"], item["clinic_id"]))
    return lines


def gsd_clinic_table(rows, facilities):
    grouped = defaultdict(list)
    for row in rows:
        if row["in_ehr_denominator"]:
            grouped[row["clinic_id"]].append(row)
    lines = []
    for clinic_id in sorted(grouped):
        group = grouped[clinic_id]
        over = sum(1 for row in group if row["band"] in {"gt9", "missing"})
        missing = sum(1 for row in group if row["band"] == "missing")
        lines.append({
            "clinic_id": clinic_id,
            "name": facilities.get(clinic_id, clinic_id),
            "denominator": len(group),
            "over": over,
            "missing": missing,
            "rate": over / len(group),
        })
    lines.sort(key=lambda item: (-item["rate"], item["clinic_id"]))
    return lines


def render(data, cbp, gsd, cms):
    ehr = [row for row in cbp if row["in_ehr_denominator"]]
    payer = [row for row in cbp if row["in_payer_denominator"]]
    ehr_controlled = sum(1 for row in ehr if row["controlled"])
    payer_controlled = sum(1 for row in payer if row["controlled"])
    note_only = sum(1 for row in ehr if row["no_usable_bp"] and row["scenario"] == "note_only")
    nondigital = sum(1 for row in ehr if row["no_usable_bp"] and row["scenario"] == "home_nondigital")
    high = sum(1 for row in ehr if row["controlled"] is False and not row["no_usable_bp"])
    age_out = sum(1 for row in cbp if not row["age_ok"])
    visit_out = sum(1 for row in cbp if row["age_ok"] and row["htn_visit_count"] < 2)
    excluded = [row for row in cbp if row["age_ok"] and row["htn_visit_count"] >= 2 and row["exclusion"]]

    g_ehr = [row for row in gsd if row["in_ehr_denominator"]]
    g_payer = [row for row in gsd if row["in_payer_denominator"]]
    bands = defaultdict(int)
    for row in g_ehr:
        bands[row["band"]] += 1
    over_n = bands["gt9"] + bands["missing"]
    payer_over = sum(1 for row in g_payer if row["band"] in {"gt9", "missing"})
    payer_lt8 = sum(1 for row in g_payer if row["band"] == "lt8")
    trapped = sum(1 for row in g_ehr if row["trapped_later_result"])
    missing_note = sum(1 for row in g_ehr if row["band"] == "missing" and row["scenario"] == "note_only")
    missing_scan = sum(1 for row in g_ehr if row["band"] == "missing" and row["scenario"] == "scanned")
    missing_gmi = sum(1 for row in g_ehr if row["band"] == "missing" and row["scenario"] == "gmi_no_range")

    cms_den = [row for row in cms if row["in_denominator"]]
    cms_num = [row for row in cms_den if row["in_numerator"]]
    meter_removed = [row for row in cms_num if row["meter_would_remove"]]
    hospitals = []
    for fid in ("H01", "H02", "H03"):
        den = [row for row in cms_den if row["facility_id"] == fid]
        num = [row for row in den if row["in_numerator"]]
        hospitals.append({
            "id": fid,
            "name": data["facilities"][fid],
            "denominator": len(den),
            "numerator": len(num),
            "meter": sum(1 for row in num if row["meter_would_remove"]),
            "late_repeat": sum(1 for row in num if row["clearance"] == "repeat_outside_five_minutes"),
        })

    clinics = clinic_table(cbp, data["facilities"])
    gsd_clinics = gsd_clinic_table(gsd, data["facilities"])
    lowest = clinics[:5]
    highest_gsd = gsd_clinics[:5]

    false_low = {row["facility_id"]: row for row in cms if row["scenario"] == "false_low"}
    note_patient = by_scenario(cbp, "note_only")[0]
    trapped_patient = by_scenario(gsd, "newer_result_trapped")[0]

    summary = {
        "cbp_ehr": {"numerator": ehr_controlled, "denominator": len(ehr), "note_only": note_only, "nondigital": nondigital, "high": high},
        "cbp_payer": {"numerator": payer_controlled, "denominator": len(payer)},
        "gsd_ehr": {
            "denominator": len(g_ehr),
            "lt8": bands["lt8"],
            "mid": bands["mid"],
            "gt9": bands["gt9"],
            "missing": bands["missing"],
            "over": over_n,
            "trapped": trapped,
        },
        "gsd_payer": {"denominator": len(g_payer), "over": payer_over, "lt8": payer_lt8},
        "cms": {
            "numerator": len(cms_num),
            "denominator": len(cms_den),
            "meter_would_remove": len(meter_removed),
            "hospitals": hospitals,
        },
        "lowest_cbp_clinics": [row["clinic_id"] for row in lowest],
        "highest_gsd_clinics": [row["clinic_id"] for row in highest_gsd],
    }

    clinic_lines = "\n".join(
        f"| {row['name']} | {row['controlled']} / {row['denominator']} | {pct(row['controlled'], row['denominator'])} | {row['no_usable']} |"
        for row in clinics
    )
    gsd_lines = "\n".join(
        f"| {row['name']} | {row['over']} / {row['denominator']} | {pct(row['over'], row['denominator'])} | {row['missing']} |"
        for row in gsd_clinics
    )
    hospital_lines = "\n".join(
        f"| {row['name']} | {row['numerator']} / {row['denominator']} | {pct(row['numerator'], row['denominator'])} | {row['meter']} | {row['late_repeat']} |"
        for row in hospitals
    )
    counts = data["raw_counts"]
    text = f"""# Data profile, measurement year 2026

**Portfolio note.** Independent demonstration. Every row in `data/synthetic/` is synthetic. The extract was built so the rules in `docs/measure-specifications.md` could be counted, including planted documentation failures. The percentages below are not a health system's performance and are not a prevalence estimate.

**How this was produced.** `python3 src/test_measures.py`, then `python3 src/generate_extract.py`, then `python3 src/profile_measures.py`. The calculator reads the CSV files. It does not read the scenario name when it decides a rate. The scenario name is used only to explain a row after the fact.

## What is in the file

The extract holds three cohorts in one set of tables, because that is how an analyst usually receives data: one patient file, one encounter file, and the clinical tables beside them.

| Table | Rows |
| --- | ---: |
| Patients | {counts['patients']} |
| Encounters | {counts['encounters']} |
| Blood pressures | {counts['blood_pressures']} |
| Glycemic results | {counts['glycemic_results']} |
| Glucose results in the EHR extract | {counts['glucose_results']} |
| Glucose results held on the meter, not in the EHR extract | {counts['meter_held']} |

`data/synthetic/data_dictionary.csv` defines the columns. `meter_held_glucose.csv` is not part of the EHR extract. The official CMS816v5 rate does not see it.

Starting a denominator from every patient in the file would be a mistake. Most of the file is in a different cohort and was never a candidate for that measure. Each waterfall below starts from its own cohort.

The failure rows are planted. A routine panel, with discrete results and complete enrollment, sits beside them so a clean record can be told from a capture failure. A rate that mixes the two describes this teaching file. It does not describe a clinic.

## Controlling High Blood Pressure

Cohort size: {len(cbp)} patients.

| Step | Patients |
| --- | ---: |
| In the hypertension cohort | {len(cbp)} |
| Age 18 through 85 on 31 December 2026 | {len(cbp) - age_out} |
| Removed for age | {age_out} |
| Age in range but fewer than two qualifying hypertension encounters in the identification window | {visit_out} |
| Removed by an exclusion after the encounter rule | {len(excluded)} |
| EHR denominator | {len(ehr)} |
| Also continuously enrolled: payer-aligned denominator | {len(payer)} |

EHR clinic rate: **{fraction(ehr_controlled, len(ehr))}** controlled. Higher is better.

Payer-aligned rate: **{fraction(payer_controlled, len(payer))}** controlled. The {len(ehr) - len(payer)} patients in the EHR denominator and not in the payer denominator failed continuous enrollment. They are a real difference between an internal rate and a contract rate. They are not a capture gap.

Among the EHR denominator:

| Result | Patients |
| --- | ---: |
| Controlled | {ehr_controlled} |
| Not controlled, usable reading at or above 140/90 | {high} |
| Not controlled, blood pressure exists only as text | {note_only} |
| Not controlled, only reading is an ineligible home device | {nondigital} |

The text readings are the capture gap. The ineligible home device is the specification working as written: a non-digital home reading does not count, and those patients have no other 2026 reading. Both groups sit inside "not controlled." The leadership page has to show them separately, or a device rule looks like missing data.

Clinic rates use the attributed clinic and the EHR denominator. Clinics 06 through 10 hold the planted text readings, and they are the five lowest rates.

| Clinic | Controlled | Rate | No usable reading |
| --- | ---: | ---: | ---: |
{clinic_lines}

## Glycemic Status Assessment for Patients With Diabetes

Cohort size: {len(gsd)} patients. EHR denominator: {len(g_ehr)}. Payer-aligned denominator: {len(g_payer)}.

| EHR result | Patients | Share of EHR denominator |
| --- | ---: | ---: |
| Under 8.0% | {bands['lt8']} | {pct(bands['lt8'], len(g_ehr))} |
| 8.0% through 9.0% | {bands['mid']} | {pct(bands['mid'], len(g_ehr))} |
| Over 9.0%, numeric result | {bands['gt9']} | {pct(bands['gt9'], len(g_ehr))} |
| No usable result | {bands['missing']} | {pct(bands['missing'], len(g_ehr))} |

Over 9.0% rate, EHR: **{fraction(over_n, len(g_ehr))}**. Lower is better. This rate adds the numeric results over 9.0% and the patients with no usable result.

Of the {over_n} patients in that rate, {bands['missing']} have no usable result ({pct(bands['missing'], over_n)} of the numerator). Those {bands['missing']} split into {missing_note} notes, {missing_scan} scanned documents, and {missing_gmi} glucose-management indicators that have a number and no monitor date range.

{trapped} other patients are in the numeric over-9.0% group because the most recent usable lab is over 9.0%, while a later result sits in a note. The measure cannot use the note. The chart and the rate disagree.

Payer-aligned over 9.0% rate: **{fraction(payer_over, len(g_payer))}**. Under 8.0%, payer-aligned: **{fraction(payer_lt8, len(g_payer))}**.

Clinic rates below use the EHR denominator. A higher over-9.0% rate is worse. Clinics 06 through 10 again carry the planted notes and scans.

| Clinic | Over 9.0% | Rate | No usable result |
| --- | ---: | ---: | ---: |
{gsd_lines}

## Hospital Harm — Severe Hypoglycemia

Inpatient encounters evaluated: {len(cms)}. Denominator: {len(cms_den)}. Numerator: {len(cms_num)}.

Pooled rate: **{fraction(len(cms_num), len(cms_den))}**. Lower is better. The denominator is dominated by {sum(1 for row in cms_den if row['scenario'] == 'background')} background stays with a glucose of 142 mg/dL after insulin, so the planted harm cases do not become the whole rate. Even so, harm cases were inserted on purpose. This is not a hospital's expected rate.

| Hospital | Numerator stays | Rate | Stays that a meter export would remove | Stays whose repeat was documented after five minutes |
| --- | ---: | ---: | ---: | ---: |
{hospital_lines}

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

- CBP: {note_only} denominator patients have a 2026 blood pressure only as text. They count as not controlled. Another {nondigital} are not controlled because the only reading is from a non-digital home device.
- GSD: {bands['missing']} denominator patients have no usable A1c or GMI, so they sit in the over-9.0% rate. {trapped} more are scored on an older lab because a later result is stuck in a note.
- CMS816v5: {len(meter_removed)} stay in the numerator would leave it if the meter file were part of the extract.

## Worked rows

**Blood pressure as text.** Patient {note_patient['patient_id']}, {data['facilities'].get(note_patient['clinic_id'], note_patient['clinic_id'])}. Two hypertension encounters fall in the identification window, so the patient is in the EHR denominator. The only 2026 reading has blank systolic and diastolic and the note "BP 132/78 today." Result: not controlled, no usable reading.

**Later result trapped in a note.** Patient {trapped_patient['patient_id']}. A discrete A1c of 9.4% on 1 March 2026 is the most recent usable result. A 1 November 2026 note says "A1c 7.1 at retail clinic" and stores no number. The over-9.0% rate uses 9.4%.

**False low, three hospitals.** Encounters {false_low['H01']['encounter_id']}, {false_low['H02']['encounter_id']}, and {false_low['H03']['encounter_id']}. Each has a capillary glucose of 28 mg/dL after insulin. Hospital A clears it with a repeat in the extract. Hospital B does not, because that repeat is only on the meter. Hospital C does not, because its repeat is at six minutes.

## What this file cannot tell us

It cannot estimate how often a real clinic loses a blood pressure to free text. Those rows were inserted. It has no time zone and no clock drift, so it cannot show a glucometer clock pushing a repeat past five minutes. It uses demonstration concepts in place of the HEDIS value sets and the CMS value set OIDs. A production extract would be scored with those code lists, and the counts would move.
"""
    return text, summary


def main():
    data = prepare()
    cbp, gsd, cms = run(data)
    text, summary = render(data, cbp, gsd, cms)
    PROFILE.write_text(text)
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"Wrote {PROFILE}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    sys.exit(main())
