"""Profile a Synthea CSV extract against the three operational specifications.

The specifications stay in src/measures.py. This script only reads Synthea's
tables and applies those rules where the columns exist. A result that the
file cannot support is reported as not calculable.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from measures import continuously_enrolled  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = ROOT / "data" / "synthea" / "csv"
META_DIR = ROOT / "data" / "synthea" / "metadata"
PROFILE = ROOT / "docs" / "data-profile.md"
SUMMARY = ROOT / "outputs" / "synthea_results.json"

YEAR_START = date(2026, 1, 1)
YEAR_END = date(2026, 12, 31)
WINDOW_START = date(2025, 1, 1)
WINDOW_END = date(2026, 6, 30)

QUALIFYING_CLASSES = {"ambulatory", "wellness", "outpatient", "virtual"}
LAB_CLASSES = {"laboratory", "lab"}
HTN_CODE = "59621000"
DIABETES_CODES = {"44054006", "46635009"}
GLUCOSE_CODES = {"2339-0", "2345-7"}
A1C_CODE = "4548-4"
GMI_CODE = "97506-0"
SYSTOLIC = "8480-6"
DIASTOLIC = "8462-4"

DIABETES_DRUGS = (
    "insulin",
    "metformin",
    "glipizide",
    "glimepiride",
    "glyburide",
    "sitagliptin",
    "empagliflozin",
    "liraglutide",
    "semaglutide",
    "pioglitazone",
    "canagliflozin",
    "dapagliflozin",
    "dulaglutide",
    "exenatide",
    "linagliptin",
)


def parse_day(value: str):
    if not value:
        return None
    return date.fromisoformat(value[:10])


def load(name):
    with (CSV_DIR / f"{name}.csv").open(newline="") as handle:
        yield from csv.DictReader(handle)


def metadata():
    files = sorted(META_DIR.glob("*.json"))
    if not files:
        return {}
    return json.loads(files[-1].read_text())


def active(start, stop, window_start, window_end):
    if start is None or start > window_end:
        return False
    if stop is not None and stop < window_start:
        return False
    return True


def pregnancy(description: str) -> bool:
    text = description.lower()
    if "past pregnancy" in text or "history" in text:
        return False
    return "pregnancy" in text or "eclampsia" in text


def renal(description: str) -> bool:
    text = description.lower()
    return any(phrase in text for phrase in ("end-stage renal", "end stage renal", "dialysis", "kidney disease stage 5"))


def band(value: float) -> str:
    if value < 8.0:
        return "under 8.0%"
    if value > 9.0:
        return "over 9.0%"
    return "8.0% through 9.0%"


def payer_enrolled(spans):
    """True when one payer covers 31 Dec 2026 and that payer's own spans meet the gap rule."""
    by_payer = defaultdict(list)
    for span in spans:
        if span["span_start"] is None:
            continue
        by_payer[span["payer"]].append(span)
    for payer_spans in by_payer.values():
        covers_anchor = any(
            span["span_start"] <= YEAR_END and (span["span_end"] is None or span["span_end"] >= YEAR_END)
            for span in payer_spans
        )
        if not covers_anchor:
            continue
        normalized = []
        for span in payer_spans:
            end = YEAR_END if span["span_end"] is None else span["span_end"]
            normalized.append({
                "span_start": span["span_start"],
                "span_end": end,
                "medical_benefit": True,
            })
        if continuously_enrolled(normalized, require_medical=False):
            return True
    return False


def build():
    meta = metadata()
    extract_end = date.fromisoformat(meta.get("referenceTime", "20261013"))
    patients = {}
    for row in load("patients"):
        patients[row["Id"]] = {
            "id": row["Id"],
            "birth": parse_day(row["BIRTHDATE"]),
            "death": parse_day(row["DEATHDATE"]),
        }
    encounters = {}
    by_patient_enc = defaultdict(list)
    for row in load("encounters"):
        item = {
            "id": row["Id"],
            "patient": row["PATIENT"],
            "start": parse_day(row["START"]),
            "stop": parse_day(row["STOP"]),
            "class": row["ENCOUNTERCLASS"],
        }
        encounters[item["id"]] = item
        by_patient_enc[item["patient"]].append(item)

    conditions = []
    diabetes_rows = defaultdict(int)
    for row in load("conditions"):
        if row["CODE"] in DIABETES_CODES:
            diabetes_rows[f"{row['CODE']} {row['DESCRIPTION']}"] += 1
        conditions.append({
            "patient": row["PATIENT"],
            "encounter": row["ENCOUNTER"],
            "code": row["CODE"],
            "description": row["DESCRIPTION"],
            "start": parse_day(row["START"]),
            "stop": parse_day(row["STOP"]),
        })

    spans = defaultdict(list)
    ownership_values = set()
    open_spans = 0
    for row in load("payer_transitions"):
        ownership_values.add(row.get("PLAN_OWNERSHIP") or "(blank)")
        end = parse_day(row["END_DATE"])
        if end is None and row["START_DATE"]:
            open_spans += 1
        spans[row["PATIENT"]].append({
            "payer": row["PAYER"],
            "span_start": parse_day(row["START_DATE"]),
            "span_end": end,
        })

    bp = defaultdict(lambda: {"sys": None, "dia": None})
    a1c = defaultdict(list)
    glucose = []
    gmi_rows = 0
    urine_glucose_2026 = 0
    for row in load("observations"):
        code = row["CODE"]
        day = parse_day(row["DATE"])
        if code == GMI_CODE or "management indicator" in row["DESCRIPTION"].lower():
            gmi_rows += 1
        if code in {SYSTOLIC, DIASTOLIC} and day and day.year == 2026:
            slot = bp[(row["PATIENT"], row["ENCOUNTER"], row["DATE"])]
            try:
                value = float(row["VALUE"])
            except ValueError:
                continue
            if code == SYSTOLIC:
                slot["sys"] = value
            else:
                slot["dia"] = value
            slot["day"] = day
            slot["patient"] = row["PATIENT"]
            slot["encounter"] = row["ENCOUNTER"]
        elif code == A1C_CODE and day and day.year == 2026 and row["UNITS"] == "%":
            try:
                value = float(row["VALUE"])
            except ValueError:
                continue
            a1c[row["PATIENT"]].append((day, value))
        elif code in GLUCOSE_CODES and day and day.year == 2026:
            try:
                value = float(row["VALUE"])
            except ValueError:
                continue
            glucose.append((row["PATIENT"], row["ENCOUNTER"], day, value))
        elif code == "5792-7" and day and day.year == 2026:
            urine_glucose_2026 += 1

    meds = []
    for row in load("medications"):
        name = row["DESCRIPTION"].lower()
        if not any(drug in name for drug in DIABETES_DRUGS):
            continue
        try:
            dispenses = int(row["DISPENSES"])
        except ValueError:
            dispenses = 0
        meds.append({
            "patient": row["PATIENT"],
            "start": parse_day(row["START"]),
            "stop": parse_day(row["STOP"]),
            "dispenses": dispenses,
            "insulin": "insulin" in name,
        })

    return {
        "meta": meta,
        "extract_end": extract_end,
        "patients": patients,
        "encounters": encounters,
        "by_patient_enc": by_patient_enc,
        "conditions": conditions,
        "diabetes_rows": dict(diabetes_rows),
        "spans": spans,
        "ownership_values": sorted(ownership_values),
        "open_spans": open_spans,
        "bp": bp,
        "a1c": a1c,
        "glucose": glucose,
        "gmi_rows": gmi_rows,
        "urine_glucose_2026": urine_glucose_2026,
        "meds": meds,
    }


def age_on(born, on):
    years = on.year - born.year
    if (on.month, on.day) < (born.month, born.day):
        years -= 1
    return years


def qualifying_dates(encounters, window_start, window_end):
    dates = set()
    for encounter in encounters:
        if encounter["class"] not in QUALIFYING_CLASSES:
            continue
        if encounter["start"] and window_start <= encounter["start"] <= window_end:
            dates.add(encounter["start"])
    return sorted(dates)


def coded_dates(conditions, encounters, codes, window_start, window_end, visit_classes):
    """Dates of service where the diagnosis sits on the encounter.

    CBP passes the outpatient, telephone, and online stand-in classes. GSD
    passes None, which keeps every setting except a laboratory encounter.
    """
    dates = set()
    for condition in conditions:
        if condition["code"] not in codes:
            continue
        encounter = encounters.get(condition["encounter"])
        if encounter is None:
            continue
        if visit_classes is not None and encounter["class"] not in visit_classes:
            continue
        if visit_classes is None and encounter["class"] in LAB_CLASSES:
            continue
        if encounter["start"] and window_start <= encounter["start"] <= window_end:
            dates.add(encounter["start"])
    return sorted(dates)


def removed(patient, encounters, conditions, measure):
    """Death, hospice, and palliative care apply to both HEDIS measures.

    Pregnancy and end-stage renal disease remove a patient from CBP only.
    GSD does not use those two exclusions.
    """
    if patient["death"] and YEAR_START <= patient["death"] <= YEAR_END:
        return "death"
    for encounter in encounters:
        if encounter["class"] == "hospice" and encounter["start"] and YEAR_START <= encounter["start"] <= YEAR_END:
            return "hospice"
    for condition in conditions:
        if not active(condition["start"], condition["stop"], YEAR_START, YEAR_END):
            continue
        if "palliative" in condition["description"].lower():
            return "palliative"
        if measure == "cbp" and pregnancy(condition["description"]):
            return "pregnancy"
        if measure == "cbp" and renal(condition["description"]):
            return "renal"
    return None


def latest_a1c(readings):
    if not readings:
        return None
    latest = max(day for day, _value in readings)
    on_day = [value for day, value in readings if day == latest]
    return latest, min(on_day)


def representative_bp(pairs, second_visit, encounters):
    eligible = []
    for pair in pairs:
        if pair["sys"] is None or pair["dia"] is None:
            continue
        encounter = encounters.get(pair["encounter"])
        if encounter is None:
            continue
        if encounter["class"] in {"inpatient", "emergency", "home"}:
            continue
        if pair["day"] < second_visit or pair["day"].year != 2026:
            continue
        eligible.append(pair)
    if not eligible:
        return None
    latest = max(pair["day"] for pair in eligible)
    day_pairs = [pair for pair in eligible if pair["day"] == latest]
    return {
        "day": latest,
        "sys": min(pair["sys"] for pair in day_pairs),
        "dia": min(pair["dia"] for pair in day_pairs),
    }


def profile(data):
    patients = data["patients"]
    by_patient_conditions = defaultdict(list)
    for condition in data["conditions"]:
        by_patient_conditions[condition["patient"]].append(condition)
    by_patient_meds = defaultdict(list)
    for med in data["meds"]:
        by_patient_meds[med["patient"]].append(med)
    bp_by_patient = defaultdict(list)
    for pair in data["bp"].values():
        if "patient" in pair:
            bp_by_patient[pair["patient"]].append(pair)

    htn_literal = 0
    htn_active = 0
    htn_two_visits = 0
    htn_proxy = []
    example = None
    dm_literal = 0
    dm_active = 0
    dm_two_visits = 0
    dm_pharmacy_only = 0
    dm_literal_kept = 0
    a1c_bands = defaultdict(int)
    a1c_missing = 0
    dm_list_kept = 0
    list_bands = defaultdict(int)
    list_missing = 0

    for pid, patient in patients.items():
        encs = data["by_patient_enc"][pid]
        conds = by_patient_conditions[pid]
        htn_dates = coded_dates(conds, data["encounters"], {HTN_CODE}, WINDOW_START, WINDOW_END, QUALIFYING_CLASSES)
        if len(htn_dates) >= 2:
            htn_literal += 1
        htn_is_active = any(
            condition["code"] == HTN_CODE and active(condition["start"], condition["stop"], WINDOW_START, WINDOW_END)
            for condition in conds
        )
        visit_dates = qualifying_dates(encs, WINDOW_START, WINDOW_END)
        if htn_is_active:
            htn_active += 1
            if len(visit_dates) >= 2:
                htn_two_visits += 1
                exclusion = removed(patient, encs, conds, "cbp")
                age = age_on(patient["birth"], YEAR_END)
                if 18 <= age <= 85 and exclusion is None:
                    reading = representative_bp(bp_by_patient[pid], visit_dates[1], data["encounters"])
                    htn_proxy.append({
                        "id": pid,
                        "enrolled": payer_enrolled(data["spans"][pid]),
                        "reading": reading,
                    })
                    onset = min(
                        (condition["start"] for condition in conds if condition["code"] == HTN_CODE and condition["start"]),
                        default=None,
                    )
                    preferred = onset is not None and onset < WINDOW_START and reading is not None
                    if example is None or (preferred and not example.get("preferred")):
                        example = {
                            "id": pid,
                            "onset": onset.isoformat() if onset else "",
                            "coded_encounters": len(htn_dates),
                            "qualifying_visits": len(visit_dates),
                            "has_bp": reading is not None,
                            "preferred": preferred,
                        }

        dm_dates = coded_dates(conds, data["encounters"], DIABETES_CODES, WINDOW_START, YEAR_END, None)
        if len(dm_dates) >= 2:
            dm_literal += 1
        dm_is_active = any(
            condition["code"] in DIABETES_CODES and active(condition["start"], condition["stop"], WINDOW_START, YEAR_END)
            for condition in conds
        )
        dm_in_window = any(
            condition["code"] in DIABETES_CODES and condition["start"] and WINDOW_START <= condition["start"] <= YEAR_END
            for condition in conds
        )
        drug = any(
            med["dispenses"] >= 1 and active(med["start"], med["stop"], WINDOW_START, YEAR_END)
            for med in by_patient_meds[pid]
        )
        if dm_is_active:
            dm_active += 1
        if len(qualifying_dates(encs, WINDOW_START, YEAR_END)) >= 2 and dm_is_active:
            dm_two_visits += 1
        if dm_in_window and drug and len(dm_dates) < 2:
            dm_pharmacy_only += 1
        age = age_on(patient["birth"], YEAR_END)
        gsd_exclusion = removed(patient, encs, conds, "gsd")
        literal_member = (len(dm_dates) >= 2) or (dm_in_window and drug)
        if literal_member and 18 <= age <= 75 and gsd_exclusion is None:
            dm_literal_kept += 1
            chosen = latest_a1c(data["a1c"][pid])
            if chosen is None:
                a1c_missing += 1
            else:
                a1c_bands[band(chosen[1])] += 1
        gsd_visits = qualifying_dates(encs, WINDOW_START, YEAR_END)
        if dm_is_active and len(gsd_visits) >= 2 and 18 <= age <= 75 and gsd_exclusion is None:
            dm_list_kept += 1
            chosen = latest_a1c(data["a1c"][pid])
            if chosen is None:
                list_missing += 1
            else:
                list_bands[band(chosen[1])] += 1

    inpatient_2026 = []
    for encounter in data["encounters"].values():
        if encounter["class"] != "inpatient" or encounter["stop"] is None:
            continue
        if encounter["stop"].year != 2026:
            continue
        patient = patients.get(encounter["patient"])
        if patient is None:
            continue
        inpatient_2026.append(encounter)
    adult_inpatient = [
        encounter for encounter in inpatient_2026
        if age_on(patients[encounter["patient"]]["birth"], encounter["start"]) >= 18
    ]
    lows = [item for item in data["glucose"] if item[3] < 40]
    inpatient_ids = {encounter["id"] for encounter in adult_inpatient}
    inpatient_lows = [item for item in lows if item[1] in inpatient_ids]
    glucose_on_adult_stays = [item for item in data["glucose"] if item[1] in inpatient_ids]
    min_glucose = min((item[3] for item in glucose_on_adult_stays), default=None)
    insulin_overlap = 0
    meds_by_patient = defaultdict(list)
    for med in data["meds"]:
        if med["insulin"]:
            meds_by_patient[med["patient"]].append(med)
    for encounter in adult_inpatient:
        for med in meds_by_patient[encounter["patient"]]:
            if active(med["start"], med["stop"], encounter["start"], encounter["stop"] or encounter["start"]):
                insulin_overlap += 1
                break

    proxy_with_bp = [row for row in htn_proxy if row["reading"] is not None]
    controlled = [
        row for row in proxy_with_bp
        if row["reading"]["sys"] < 140 and row["reading"]["dia"] < 90
    ]
    enrolled_proxy = [row for row in htn_proxy if row["enrolled"]]

    return {
        "patients": len(patients),
        "seed": data["meta"].get("seed"),
        "clinician_seed": data["meta"].get("clinicianSeed"),
        "reference": data["meta"].get("referenceTime"),
        "version": (data["meta"].get("version") or "").strip(),
        "state": data["meta"].get("state"),
        "extract_end": data["extract_end"].isoformat(),
        "htn_literal": htn_literal,
        "htn_active": htn_active,
        "htn_two_visits": htn_two_visits,
        "htn_proxy": len(htn_proxy),
        "htn_with_bp": len(proxy_with_bp),
        "htn_controlled_proxy": len(controlled),
        "htn_enrolled_proxy": len(enrolled_proxy),
        "example": example,
        "dm_literal": dm_literal,
        "dm_active": dm_active,
        "dm_two_visits": dm_two_visits,
        "dm_pharmacy_only": dm_pharmacy_only,
        "dm_literal_kept": dm_literal_kept,
        "a1c_bands": dict(a1c_bands),
        "a1c_missing": a1c_missing,
        "dm_list_kept": dm_list_kept,
        "list_bands": dict(list_bands),
        "list_missing": list_missing,
        "open_spans": data["open_spans"],
        "gmi_rows": data["gmi_rows"],
        "urine_glucose_2026": data["urine_glucose_2026"],
        "inpatient_2026": len(inpatient_2026),
        "adult_inpatient": len(adult_inpatient),
        "glucose_under_40": len(lows),
        "inpatient_lows": len(inpatient_lows),
        "adult_stay_glucoses": len(glucose_on_adult_stays),
        "min_glucose_adult_stay": min_glucose,
        "insulin_course_overlap": insulin_overlap,
        "ownership_values": data["ownership_values"],
        "diabetes_rows": data["diabetes_rows"],
        "organizations": sum(1 for _ in load("organizations")),
    }


def pct(numerator, denominator):
    if not denominator:
        return "n/a"
    return f"{(100 * numerator / denominator):.1f}%"


def render(result):
    bands = result["a1c_bands"]
    under = bands.get("under 8.0%", 0)
    mid = bands.get("8.0% through 9.0%", 0)
    over = bands.get("over 9.0%", 0)
    list_bands = result["list_bands"]
    list_under = list_bands.get("under 8.0%", 0)
    list_mid = list_bands.get("8.0% through 9.0%", 0)
    list_over = list_bands.get("over 9.0%", 0)
    ownership_line = ", ".join(result["ownership_values"]) or "none"
    diabetes_bits = []
    for name, count in sorted(result["diabetes_rows"].items()):
        code, description = name.split(" ", 1)
        diabetes_bits.append(f"SNOMED {code}, {description}, {count} rows")
    diabetes_line = "; ".join(diabetes_bits) or "none"
    example = result["example"] or {}
    min_glucose = result["min_glucose_adult_stay"]
    min_text = "none" if min_glucose is None else f"{min_glucose:.1f} mg/dL"
    example_text = "No patient met the proxy population."
    if example:
        coded = example["coded_encounters"]
        if coded == 0:
            coded_text = "no qualifying encounter"
        elif coded == 1:
            coded_text = "one qualifying encounter"
        else:
            coded_text = f"{coded} qualifying encounters"
        example_text = (
            f"Patient `{example['id']}` has essential hypertension recorded on {example['onset']}. "
            f"That code is attached to {coded_text} in the identification window. "
            f"The same patient has {example['qualifying_visits']} qualifying visits in the window"
            f"{', and a paired 2026 blood pressure' if example['has_bp'] else ''}."
        )
    return f"""# Data profile, Synthea extract

**Portfolio note.** Independent demonstration. The rows are synthetic patients produced by Synthea, not records from a health system, a payer, or CMS. The counts below describe this file only.

**Source.** Synthea version `{result['version']}`, state {result['state']}, seed {result['seed']}, clinician seed {result['clinician_seed']}, reference date {result['reference']}. The run asked for 2,000 living patients. The patient file contains {result['patients']} people, living and deceased. Clinical history in the files runs through {result['extract_end']}. Measurement year 2026 is therefore incomplete: November and December are not in the extract.

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
| Patients in the file | {result['patients']} |
| Essential hypertension (SNOMED 59621000) active in the identification window | {result['htn_active']} |
| Type 2 diabetes (SNOMED 44054006) active in 2025 or 2026 | {result['dm_active']} |
| Inpatient encounters that end in 2026 | {result['inpatient_2026']} |
| Glucose-management indicator rows (LOINC 97506-0) | {result['gmi_rows']} |
| Urine glucose strip results in 2026, ignored by CMS816v5 | {result['urine_glucose_2026']} |
| Provider organizations in the file | {result['organizations']} |

The file is a Massachusetts population. It is not a 15-clinic health system, and the organizations are not rolled into that shape.

## How the event rule was checked

The licensed HEDIS Volume 2 for measurement year 2026 was not the copy open for this check. Production reporting still uses that volume. The events below follow NCQA's published specification language and measurement-year 2026 plan guides that cite it.

Controlling High Blood Pressure uses two visits on different dates, and the hypertension diagnosis is part of each visit. The window runs from 1 January 2025 through 30 June 2026. The visits may be outpatient, telephone, e-visit, or virtual check-in. The blood pressure has to fall on or after the second of those diagnosis dates. NCQA writes the event as a visit value set combined with the Essential Hypertension value set. Guides from Blue Cross NC, Priority Health, BCBST, Carolina Complete Health, and BCBSND use that event for 2026. One Florida Blue sheet lists the visits and "any diagnosis of hypertension" as separate bullets. That sheet still requires the second diagnosis date, so a single problem-list onset does not qualify.

Glycemic status uses two diabetes diagnosis dates of service in any setting during 2025 or 2026, excluding a laboratory claim, or one diagnosis date in that span plus a dispensing event in that span. That is NCQA's current event, the one that replaced a list of specific visit types.

## Controlling High Blood Pressure

The HEDIS denominator needs two outpatient, telephone, or online encounters in the identification window, on different dates, each carrying a hypertension diagnosis.

Encounters in that window that carry SNOMED 59621000 and have a qualifying class: patients with two such encounters = **{result['htn_literal']}**.

The contract rate is not calculated. A denominator of zero is not a performance result.

The condition is present. {result['htn_active']} patients have essential hypertension active during the window. {result['htn_two_visits']} of them also have two qualifying visits in the window. No patient has the hypertension code on two of those visits. The usual shape is one condition row, dated at onset. Reusing the problem list would put {result['htn_proxy']} adults age 18 to 85, with no death, hospice, pregnancy, or end-stage renal row found in 2026, into an internal denominator. That reuse is a different measure. Of those {result['htn_proxy']}, {result['htn_with_bp']} have a paired numeric systolic and diastolic in 2026 on an eligible encounter. {result['htn_controlled_proxy']} of those pairs are under 140 and under 90. Those counts describe the values in the file. They are a description, and the contract tile stays blank.

Payer spans have start and end timestamps. The file contains {result['open_spans']} spans with a blank end date. {result['htn_enrolled_proxy']} of the internal-denominator patients have one payer whose own spans cover 31 December 2026 and meet the 45-day gap rule. Spans from different payers were not merged. Named payers are present, including Medicare, Medicaid, and Dual Eligible. Plan ownership on the member span takes these values: {ownership_line}. Guardian, Self, and Spouse are subscriber relationships. A blank value is an empty field. The span does not identify an institutional special needs plan or a long-term institution, so that exclusion is not applied. Home blood-pressure device type is absent, so a home reading is not used. Clinical rows stop on {result['extract_end']}, so a 2026 blood pressure in this file cannot fall in November or December.

{example_text}

## Glycemic Status Assessment for Patients With Diabetes

The HEDIS denominator needs two diabetes diagnosis dates of service in any non-laboratory setting during 2025 or 2026, or one such diagnosis date plus a diabetes medication dispense in that span.

Patients with two diabetes diagnosis dates in that span: **{result['dm_literal']}**.

Patients with one in-window diabetes diagnosis date plus a diabetes medication course that has at least one dispense, and who do not already have two diagnosis dates: **{result['dm_pharmacy_only']}**.

Patients who meet either written method, are age 18 to 75, and are not removed for death, hospice, or palliative care: **{result['dm_literal_kept']}**. The contract rate is not calculated from that count. A medication row here is a course with a dispense count, which is the closest field the file has to a pharmacy fill.

Diabetes condition rows in the file: {diabetes_line}. {result['dm_active']} patients have type 2 diabetes active in the two-year span, and {result['dm_two_visits']} of those also have two qualifying visits. The diagnosis is stored at onset and is not coded again on the later visits. Reusing the problem list would put {result['dm_list_kept']} adults age 18 to 75, with no death, hospice, or palliative row in 2026, into an internal list. That list is a different measure. There are no glucose-management indicator rows. Hemoglobin A1c, when present, is a numeric percent (LOINC 4548-4).

A1c values among the {result['dm_literal_kept']} patients who meet a written identification method:

| 2026 A1c | Patients |
| --- | ---: |
| Under 8.0% | {under} |
| 8.0% through 9.0% | {mid} |
| Over 9.0% | {over} |
| No A1c in the extract | {result['a1c_missing']} |

A1c values among the {result['dm_list_kept']} patients in the problem-list description, which is not a reportable denominator:

| 2026 A1c | Patients |
| --- | ---: |
| Under 8.0% | {list_under} |
| 8.0% through 9.0% | {list_mid} |
| Over 9.0% | {list_over} |
| No A1c in the extract | {result['list_missing']} |

Neither table is a GSD rate. The first follows the written identification methods and is too small to display. The second describes the A1c file if the problem list is reused. In that second table, {result['list_missing']} patients have no 2026 A1c. The numerator rule would place a missing result in the over-9.0% rate. That step is not taken here, because those patients are not the HEDIS denominator.

## Hospital Harm — Severe Hypoglycemia

Adult inpatient encounters that end in 2026: **{result['adult_inpatient']}**.

Glucose results under 40 mg/dL in 2026, in any setting: **{result['glucose_under_40']}**. On those adult stays, glucose results from blood or serum: {result['adult_stay_glucoses']}. The lowest of them is {min_text}.

Medication rows are courses. They have a start, a stop, and a dispense count. They are not administration events. {result['insulin_course_overlap']} adult stays overlap an insulin course. Overlap of a course does not locate a dose within 24 hours of a draw.

CMS816v5 is not scored. The numerator event does not occur in this file, and the administration clock the specification uses is not in the file. Urine glucose strips are present and were not treated as blood glucose.

## What this file changes in the packet

The gap is not a blood pressure buried in a note. Systolic, diastolic, and A1c values that Synthea writes are discrete numbers. The gap is the diagnosis. Hypertension and diabetes are recorded when they start and are not coded on later encounters, so the HEDIS denominators cannot be formed. The hospital measure has a second, separate limit: no glucose under 40 mg/dL, and no medication administration time.

An internal rate that reused the problem list would answer a different question. It is not the rate a payer or CMS would compute from this extract.
"""


def main():
    if not CSV_DIR.exists():
        print(f"Missing {CSV_DIR}. Generate the Synthea CSV extract first.", file=sys.stderr)
        return 1
    result = profile(build())
    PROFILE.write_text(render(result))
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in (
        "patients", "htn_literal", "htn_active", "htn_two_visits", "htn_proxy", "htn_with_bp",
        "dm_literal", "dm_active", "dm_pharmacy_only", "dm_literal_kept", "dm_list_kept", "a1c_missing", "list_missing",
        "adult_inpatient", "glucose_under_40", "min_glucose_adult_stay", "gmi_rows",
    )}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
