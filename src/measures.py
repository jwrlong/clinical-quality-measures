"""Operational logic for the three measures in docs/measure-specifications.md.

The functions follow that document. Demonstration concepts stand in for the
HEDIS value sets and the CMS value set OIDs. They are not those code lists.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional


YEAR_START = date(2026, 1, 1)
YEAR_END = date(2026, 12, 31)
HTN_WINDOW_START = date(2025, 1, 1)
HTN_WINDOW_END = date(2026, 6, 30)
PRIOR_START = date(2025, 1, 1)

QUALIFYING_HTN_CLASSES = {"ambulatory", "telephone", "online"}
DIABETES_ENCOUNTER_CLASSES = {"ambulatory", "telephone", "online", "emergency", "inpatient", "observation"}
RENAL_CONCEPTS = {"esrd", "dialysis", "nephrectomy", "kidney_transplant"}


def age_on(born: date, on: date) -> int:
    years = on.year - born.year
    if (on.month, on.day) < (born.month, born.day):
        years -= 1
    return years


def _as_date(value: datetime | date) -> date:
    if isinstance(value, datetime):
        return value.date()
    return value


def continuously_enrolled(spans: list[dict], require_medical: bool = False) -> bool:
    """One gap of at most 45 days is allowed. The member must be enrolled on 31 Dec 2026."""
    covered = [False] * 365
    for span in spans:
        start = span["span_start"]
        end = span["span_end"]
        if require_medical and not span.get("medical_benefit", False):
            continue
        start = max(start, YEAR_START)
        end = min(end, YEAR_END)
        if end < start:
            continue
        for offset in range((end - start).days + 1):
            covered[(start - YEAR_START).days + offset] = True
    if not covered[-1]:
        return False
    gaps: list[int] = []
    length = 0
    for day_covered in covered:
        if not day_covered:
            length += 1
        elif length:
            gaps.append(length)
            length = 0
    if length:
        gaps.append(length)
    if len(gaps) > 1:
        return False
    if len(gaps) == 1 and gaps[0] > 45:
        return False
    return True


def _in_year(value: datetime | date, start: date = YEAR_START, end: date = YEAR_END) -> bool:
    day = _as_date(value)
    return start <= day <= end


def _flag(span: dict, name: str) -> bool:
    return bool(span.get(name))


def _spans_overlap_year(spans: list[dict]) -> list[dict]:
    found = []
    for span in spans:
        if span["span_end"] >= YEAR_START and span["span_start"] <= YEAR_END:
            found.append(span)
    return found


def cbp_exclusion(patient: dict, encounters: list[dict], diagnoses: list[dict], spans: list[dict], dispenses: list[dict]) -> Optional[str]:
    death = patient.get("death_date")
    if death is not None and _in_year(death):
        return "death"
    age = age_on(patient["birth_date"], YEAR_END)
    for encounter in encounters:
        if encounter["encounter_class"] == "hospice" and _in_year(encounter["start"]):
            return "hospice"
        if encounter["encounter_class"] == "nonacute_inpatient" and _in_year(encounter["start"]):
            return "nonacute_inpatient"
    for diagnosis in diagnoses:
        recorded = diagnosis["recorded_date"]
        concept = diagnosis["concept"]
        if concept == "palliative" and _in_year(recorded):
            return "palliative"
        if concept == "pregnancy" and _in_year(recorded):
            return "pregnancy"
        if concept in RENAL_CONCEPTS and _as_date(recorded) <= YEAR_END:
            return "renal"
    overlapping = _spans_overlap_year(spans)
    if age >= 66 and any(_flag(span, "isnp") or _flag(span, "lti") for span in overlapping):
        return "institutional"
    frailty_dates = {
        _as_date(diagnosis["recorded_date"])
        for diagnosis in diagnoses
        if diagnosis["concept"] == "frailty" and _in_year(diagnosis["recorded_date"])
    }
    advanced_dates = {
        _as_date(diagnosis["recorded_date"])
        for diagnosis in diagnoses
        if diagnosis["concept"] == "advanced_illness" and PRIOR_START <= _as_date(diagnosis["recorded_date"]) <= YEAR_END
    }
    dementia = any(
        dispense["drug_class"] == "dementia" and PRIOR_START <= dispense["fill_date"] <= YEAR_END
        for dispense in dispenses
    )
    if age >= 81 and frailty_dates:
        return "frailty"
    if 66 <= age <= 80 and frailty_dates and (advanced_dates or dementia):
        return "frailty_and_advanced_illness"
    return None


def htn_visit_dates(encounters: list[dict], diagnoses: list[dict]) -> list[date]:
    htn_encounters = {diagnosis["encounter_id"] for diagnosis in diagnoses if diagnosis["concept"] == "hypertension"}
    dates = []
    for encounter in encounters:
        if encounter["encounter_id"] not in htn_encounters:
            continue
        if encounter["encounter_class"] not in QUALIFYING_HTN_CLASSES:
            continue
        day = _as_date(encounter["start"])
        if HTN_WINDOW_START <= day <= HTN_WINDOW_END:
            dates.append(day)
    return sorted(set(dates))


def eligible_blood_pressures(readings: list[dict], second_dx: date) -> list[dict]:
    eligible = []
    for reading in readings:
        if reading.get("capture") != "discrete":
            continue
        if reading.get("systolic") is None or reading.get("diastolic") is None:
            continue
        taken = reading["taken_at"]
        if not _in_year(taken):
            continue
        if _as_date(taken) < second_dx:
            continue
        if reading.get("setting") in {"inpatient", "emergency"}:
            continue
        if reading.get("source") == "home_nondigital":
            continue
        if reading.get("procedure_diet_change"):
            continue
        eligible.append(reading)
    return eligible


def representative_bp(readings: list[dict]) -> Optional[dict]:
    if not readings:
        return None
    latest = max(_as_date(reading["taken_at"]) for reading in readings)
    day_readings = [reading for reading in readings if _as_date(reading["taken_at"]) == latest]
    return {
        "date": latest,
        "systolic": min(reading["systolic"] for reading in day_readings),
        "diastolic": min(reading["diastolic"] for reading in day_readings),
    }


def evaluate_cbp(patient: dict, encounters: list[dict], diagnoses: list[dict], readings: list[dict], spans: list[dict], dispenses: list[dict]) -> dict:
    age = age_on(patient["birth_date"], YEAR_END)
    age_ok = 18 <= age <= 85
    visit_dates = htn_visit_dates(encounters, diagnoses)
    second_dx = visit_dates[1] if len(visit_dates) >= 2 else None
    exclusion = cbp_exclusion(patient, encounters, diagnoses, spans, dispenses) if age_ok and second_dx else None
    enrolled = continuously_enrolled(spans, require_medical=False)
    in_ehr = bool(age_ok and second_dx and exclusion is None)
    chosen = representative_bp(eligible_blood_pressures(readings, second_dx)) if second_dx else None
    no_usable = bool(in_ehr and chosen is None)
    controlled = None
    if in_ehr and chosen is not None:
        controlled = chosen["systolic"] < 140 and chosen["diastolic"] < 90
    if in_ehr and chosen is None:
        controlled = False
    return {
        "patient_id": patient["patient_id"],
        "clinic_id": patient.get("clinic_id"),
        "scenario": patient.get("scenario"),
        "age": age,
        "age_ok": age_ok,
        "htn_visit_count": len(visit_dates),
        "second_dx": second_dx,
        "exclusion": exclusion,
        "enrolled": enrolled,
        "in_ehr_denominator": in_ehr,
        "in_payer_denominator": bool(in_ehr and enrolled),
        "systolic": None if chosen is None else chosen["systolic"],
        "diastolic": None if chosen is None else chosen["diastolic"],
        "bp_date": None if chosen is None else chosen["date"],
        "controlled": controlled,
        "no_usable_bp": no_usable,
    }


def gsd_exclusion(patient: dict, encounters: list[dict], diagnoses: list[dict], spans: list[dict], dispenses: list[dict]) -> Optional[str]:
    death = patient.get("death_date")
    if death is not None and _in_year(death):
        return "death"
    age = age_on(patient["birth_date"], YEAR_END)
    for encounter in encounters:
        if encounter["encounter_class"] == "hospice" and _in_year(encounter["start"]):
            return "hospice"
    for diagnosis in diagnoses:
        if diagnosis["concept"] == "palliative" and _in_year(diagnosis["recorded_date"]):
            return "palliative"
    overlapping = _spans_overlap_year(spans)
    institutional = any(
        span.get("product_line") == "medicare" and (_flag(span, "isnp") or _flag(span, "lti"))
        for span in overlapping
    )
    if age >= 66 and institutional:
        return "institutional"
    frailty_dates = {
        _as_date(diagnosis["recorded_date"])
        for diagnosis in diagnoses
        if diagnosis["concept"] == "frailty" and _in_year(diagnosis["recorded_date"])
    }
    advanced_dates = {
        _as_date(diagnosis["recorded_date"])
        for diagnosis in diagnoses
        if diagnosis["concept"] == "advanced_illness" and PRIOR_START <= _as_date(diagnosis["recorded_date"]) <= YEAR_END
    }
    dementia = any(
        dispense["drug_class"] == "dementia" and PRIOR_START <= dispense["fill_date"] <= YEAR_END
        for dispense in dispenses
    )
    if age >= 66 and len(frailty_dates) >= 2 and (len(advanced_dates) >= 2 or dementia):
        return "frailty_and_advanced_illness"
    return None


def diabetes_method(encounters: list[dict], diagnoses: list[dict], dispenses: list[dict]) -> Optional[str]:
    encounters_by_id = {encounter["encounter_id"]: encounter for encounter in encounters}
    diagnosis_dates = set()
    for diagnosis in diagnoses:
        if diagnosis["concept"] != "diabetes":
            continue
        encounter = encounters_by_id.get(diagnosis["encounter_id"])
        if encounter is None:
            continue
        if encounter["encounter_class"] not in DIABETES_ENCOUNTER_CLASSES:
            continue
        if str(encounter.get("place_of_service")) == "81":
            continue
        day = _as_date(encounter["start"])
        if PRIOR_START <= day <= YEAR_END:
            diagnosis_dates.add(day)
    has_dispense = any(
        dispense["drug_class"] == "diabetes" and PRIOR_START <= dispense["fill_date"] <= YEAR_END
        for dispense in dispenses
    )
    if len(diagnosis_dates) >= 2:
        return "encounter"
    if len(diagnosis_dates) >= 1 and has_dispense:
        return "pharmacy"
    return None


def usable_glycemic(results: list[dict]) -> list[dict]:
    usable = []
    for result in results:
        if result.get("capture") != "discrete":
            continue
        if result.get("value") is None:
            continue
        analyte = result["analyte"]
        if analyte == "a1c":
            if result.get("unit") != "%":
                continue
            if not _in_year(result["result_date"]):
                continue
            usable.append({"date": _as_date(result["result_date"]), "value": float(result["value"]), "analyte": "a1c"})
        elif analyte == "gmi":
            range_end = result.get("gmi_range_end")
            if range_end is None:
                continue
            if not _in_year(range_end):
                continue
            usable.append({"date": _as_date(range_end), "value": float(result["value"]), "analyte": "gmi"})
    return usable


def glycemic_band(value: float) -> str:
    if value < 8.0:
        return "lt8"
    if value > 9.0:
        return "gt9"
    return "mid"


def evaluate_gsd(patient: dict, encounters: list[dict], diagnoses: list[dict], results: list[dict], spans: list[dict], dispenses: list[dict]) -> dict:
    age = age_on(patient["birth_date"], YEAR_END)
    age_ok = 18 <= age <= 75
    method = diabetes_method(encounters, diagnoses, dispenses)
    exclusion = gsd_exclusion(patient, encounters, diagnoses, spans, dispenses) if age_ok and method else None
    enrolled = continuously_enrolled(spans, require_medical=True)
    in_ehr = bool(age_ok and method and exclusion is None)
    usable = usable_glycemic(results)
    chosen = None
    if usable:
        latest = max(item["date"] for item in usable)
        on_day = [item for item in usable if item["date"] == latest]
        chosen = min(on_day, key=lambda item: item["value"])
    trapped = False
    if chosen is not None:
        for result in results:
            if result.get("capture") == "discrete":
                continue
            marker = result.get("result_date")
            if marker is not None and _as_date(marker) > chosen["date"]:
                trapped = True
    band = None
    if in_ehr:
        band = "missing" if chosen is None else glycemic_band(chosen["value"])
    return {
        "patient_id": patient["patient_id"],
        "clinic_id": patient.get("clinic_id"),
        "scenario": patient.get("scenario"),
        "age": age,
        "age_ok": age_ok,
        "diabetes_method": method,
        "exclusion": exclusion,
        "enrolled": enrolled,
        "in_ehr_denominator": in_ehr,
        "in_payer_denominator": bool(in_ehr and enrolled),
        "value": None if chosen is None else chosen["value"],
        "result_date": None if chosen is None else chosen["date"],
        "analyte": None if chosen is None else chosen["analyte"],
        "band": band,
        "trapped_later_result": bool(in_ehr and trapped),
    }


def hospitalization_window(inpatient: dict, encounters: list[dict]) -> tuple[datetime, datetime]:
    """Extend the stay backward through observation and emergency care when the gap is one hour or less."""
    ip_start = inpatient["start"]
    ip_end = inpatient["end"]
    patient_id = inpatient["patient_id"]
    observations = [
        encounter
        for encounter in encounters
        if encounter["patient_id"] == patient_id
        and encounter["encounter_class"] == "observation"
        and encounter["end"] <= ip_start
        and ip_start - encounter["end"] <= timedelta(hours=1)
    ]
    observation = max(observations, key=lambda encounter: encounter["end"], default=None)
    visit_start = observation["start"] if observation else ip_start
    emergencies = [
        encounter
        for encounter in encounters
        if encounter["patient_id"] == patient_id
        and encounter["encounter_class"] == "emergency"
        and encounter["end"] <= visit_start
        and visit_start - encounter["end"] <= timedelta(hours=1)
    ]
    emergency = max(emergencies, key=lambda encounter: encounter["end"], default=None)
    window_start = emergency["start"] if emergency else visit_start
    return window_start, ip_end


def glucose_mg_dl(row: dict) -> Optional[float]:
    if row.get("specimen") == "urine":
        return None
    if not row.get("in_glucose_value_set"):
        return None
    if row.get("capture") != "discrete":
        return None
    if row.get("value") is None or row.get("drawn_at") is None:
        return None
    if row.get("unit") == "mg/dL":
        return float(row["value"])
    if row.get("unit") == "mmol/L":
        return float(row["value"]) * 18
    return None


def _meds_given(administrations: list[dict], window_start: datetime, window_end: datetime) -> list[dict]:
    given = []
    for administration in administrations:
        if administration.get("action") != "given":
            continue
        if not administration.get("in_hypoglycemic_value_set"):
            continue
        start = administration["start"]
        if window_start <= start <= window_end:
            given.append(administration)
    return given


def _linked_lows(glucoses: list[dict], meds: list[dict], window_start: datetime, window_end: datetime) -> list[dict]:
    lows = []
    for glucose in glucoses:
        value = glucose_mg_dl(glucose)
        drawn = glucose.get("drawn_at")
        if value is None or drawn is None:
            continue
        if not (window_start <= drawn <= window_end):
            continue
        if value >= 40:
            continue
        linked = False
        for med in meds:
            delta = drawn - med["start"]
            if timedelta(0) <= delta <= timedelta(hours=24):
                linked = True
                break
        if linked:
            lows.append({"id": glucose["result_id"], "drawn_at": drawn, "value": value})
    return lows


def _cleared_by(low: dict, glucoses: list[dict], window_start: datetime, window_end: datetime) -> bool:
    for glucose in glucoses:
        if glucose.get("result_id") == low["id"]:
            continue
        value = glucose_mg_dl(glucose)
        drawn = glucose.get("drawn_at")
        if value is None or drawn is None:
            continue
        if not (window_start <= drawn <= window_end):
            continue
        delta = drawn - low["drawn_at"]
        if timedelta(0) < delta <= timedelta(minutes=5) and value > 80:
            return True
    return False


def evaluate_cms816(encounter: dict, patient: dict, encounters: list[dict], administrations: list[dict], glucoses: list[dict], meter_glucoses: list[dict]) -> dict:
    in_period = YEAR_START <= encounter["end"].date() <= YEAR_END
    age = age_on(patient["birth_date"], encounter["start"].date())
    age_ok = age >= 18
    window_start, window_end = hospitalization_window(encounter, encounters)
    meds = _meds_given(administrations, window_start, window_end)
    has_admin = bool(meds)
    in_denominator = bool(in_period and age_ok and has_admin)
    clearance = None
    in_numerator = False
    meter_would_remove = False
    if in_denominator:
        lows = _linked_lows(glucoses, meds, window_start, window_end)
        uncleared = [low for low in lows if not _cleared_by(low, glucoses, window_start, window_end)]
        if lows and not uncleared:
            clearance = "cleared_in_extract"
        elif uncleared:
            in_numerator = True
            meter_flags = [
                _cleared_by(low, meter_glucoses, window_start, window_end)
                for low in uncleared
            ]
            outside = False
            for low in uncleared:
                for glucose in glucoses:
                    value = glucose_mg_dl(glucose)
                    drawn = glucose.get("drawn_at")
                    if value is None or drawn is None or glucose.get("result_id") == low["id"]:
                        continue
                    delta = drawn - low["drawn_at"]
                    if delta > timedelta(minutes=5) and delta <= timedelta(minutes=30) and value > 80:
                        outside = True
            if any(meter_flags):
                clearance = "meter_not_exported"
                meter_would_remove = True
            elif outside:
                clearance = "repeat_outside_five_minutes"
            else:
                clearance = "no_clearing_repeat"
    return {
        "encounter_id": encounter["encounter_id"],
        "patient_id": patient["patient_id"],
        "facility_id": encounter.get("facility_id"),
        "scenario": encounter.get("scenario"),
        "in_period": in_period,
        "age": age,
        "age_ok": age_ok,
        "has_admin": has_admin,
        "in_denominator": in_denominator,
        "in_numerator": in_numerator,
        "clearance": clearance,
        "meter_would_remove": meter_would_remove,
    }
