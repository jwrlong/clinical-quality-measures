"""Build a deterministic synthetic extract for measurement year 2026.

The file is a teaching sample. Failure cases are planted so the documentation
gap in the data-gap memo can be counted. It is not a prevalence sample and it
is not a health-system extract.
"""

from __future__ import annotations

import csv
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "synthetic"

CONCEPT_CODE = {
    "hypertension": "I10",
    "diabetes": "E11.9",
    "palliative": "Z51.5",
    "pregnancy": "Z33.1",
    "esrd": "N18.6",
    "frailty": "R54",
    "advanced_illness": "I50.22",
}


class Bundle:
    def __init__(self):
        self.patients = []
        self.enrollment = []
        self.encounters = []
        self.diagnoses = []
        self.bps = []
        self.glycemic = []
        self.glucose = []
        self.admins = []
        self.dispenses = []
        self.meter = []
        self.n_enc = 0
        self.n_dx = 0
        self.n_bp = 0
        self.n_gly = 0
        self.n_glu = 0
        self.n_admin = 0
        self.n_disp = 0
        self.n_meter = 0

    def add_patient(self, pid, cohort, scenario, born, clinic, death=None):
        self.patients.append({
            "patient_id": pid,
            "cohort": cohort,
            "scenario": scenario,
            "birth_date": born.isoformat(),
            "death_date": "" if death is None else death.isoformat(),
            "clinic_id": clinic or "",
            "data_source": "synthetic",
        })

    def add_enrollment(self, pid, start, end, medical=True, product="commercial", isnp=False, lti=False):
        self.enrollment.append({
            "patient_id": pid,
            "span_start": start.isoformat(),
            "span_end": end.isoformat(),
            "medical_benefit": _bool(medical),
            "product_line": product,
            "isnp": _bool(isnp),
            "lti": _bool(lti),
        })

    def add_encounter(self, pid, kind, start, end, facility, pos="11", scenario=""):
        self.n_enc += 1
        eid = f"E{self.n_enc:05d}"
        self.encounters.append({
            "encounter_id": eid,
            "patient_id": pid,
            "encounter_class": kind,
            "start_datetime": _dt(start),
            "end_datetime": _dt(end),
            "facility_id": facility,
            "place_of_service": pos,
            "scenario": scenario,
        })
        return eid

    def add_dx(self, pid, eid, concept, recorded):
        self.n_dx += 1
        self.diagnoses.append({
            "diagnosis_id": f"D{self.n_dx:05d}",
            "patient_id": pid,
            "encounter_id": eid,
            "concept": concept,
            "code": CONCEPT_CODE.get(concept, ""),
            "recorded_date": _day(recorded),
        })

    def add_bp(self, pid, eid, taken, systolic, diastolic, source, setting, capture, diet=False, note=""):
        self.n_bp += 1
        self.bps.append({
            "reading_id": f"B{self.n_bp:05d}",
            "patient_id": pid,
            "encounter_id": eid or "",
            "taken_at": _dt(taken),
            "systolic": "" if systolic is None else systolic,
            "diastolic": "" if diastolic is None else diastolic,
            "source": source,
            "setting": setting,
            "capture": capture,
            "procedure_diet_change": _bool(diet),
            "note_text": note,
        })

    def add_a1c(self, pid, eid, value, on, capture="discrete", note="", analyte="a1c", range_start=None, range_end=None, unit="%"):
        self.n_gly += 1
        self.glycemic.append({
            "result_id": f"Y{self.n_gly:05d}",
            "patient_id": pid,
            "encounter_id": eid or "",
            "analyte": analyte,
            "value": "" if value is None else value,
            "unit": unit,
            "result_date": "" if on is None else _day(on),
            "capture": capture,
            "gmi_range_start": "" if range_start is None else _day(range_start),
            "gmi_range_end": "" if range_end is None else _day(range_end),
            "note_text": note,
        })

    def add_glucose(self, pid, eid, drawn, value, unit="mg/dL", specimen="capillary", flag=True, capture="discrete"):
        self.n_glu += 1
        rid = f"G{self.n_glu:05d}"
        posted = drawn + timedelta(minutes=20)
        self.glucose.append({
            "result_id": rid,
            "patient_id": pid,
            "encounter_id": eid,
            "drawn_at": _dt(drawn),
            "posted_at": _dt(posted),
            "value": value,
            "unit": unit,
            "specimen": specimen,
            "in_glucose_value_set": _bool(flag),
            "capture": capture,
        })
        return rid

    def add_admin(self, pid, eid, start, action="given", drug="insulin lispro", flag=True):
        self.n_admin += 1
        self.admins.append({
            "admin_id": f"A{self.n_admin:05d}",
            "patient_id": pid,
            "encounter_id": eid,
            "drug_name": drug,
            "in_hypoglycemic_value_set": _bool(flag),
            "action": action,
            "start_datetime": _dt(start),
        })

    def add_dispense(self, pid, drug_class, fill):
        self.n_disp += 1
        self.dispenses.append({
            "dispense_id": f"R{self.n_disp:05d}",
            "patient_id": pid,
            "drug_class": drug_class,
            "fill_date": fill.isoformat(),
        })

    def add_meter(self, pid, eid, related, drawn, value):
        self.n_meter += 1
        self.meter.append({
            "held_id": f"M{self.n_meter:05d}",
            "patient_id": pid,
            "encounter_id": eid,
            "related_low_result_id": related,
            "drawn_at": _dt(drawn),
            "value": value,
            "unit": "mg/dL",
            "specimen": "capillary",
            "in_glucose_value_set": "true",
            "capture": "discrete",
        })


def _bool(value):
    return "true" if value else "false"


def _day(value):
    if isinstance(value, datetime):
        return value.date().isoformat()
    return value.isoformat()


def _dt(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%S")
    return datetime(value.year, value.month, value.day, 9, 0).strftime("%Y-%m-%dT%H:%M:%S")


def _at(day, hour, minute=0):
    return datetime(day.year, day.month, day.day, hour, minute)


def full_year(bundle, pid, product="commercial", isnp=False, lti=False):
    bundle.add_enrollment(pid, date(2026, 1, 1), date(2026, 12, 31), product=product, isnp=isnp, lti=lti)


def gap_year(bundle, pid):
    bundle.add_enrollment(pid, date(2026, 1, 1), date(2026, 3, 1))
    bundle.add_enrollment(pid, date(2026, 6, 1), date(2026, 12, 31))


def htn_visits(bundle, pid, clinic, scenario, first, second):
    e1 = bundle.add_encounter(pid, "ambulatory", _at(first, 9), _at(first, 10), clinic, scenario=scenario)
    e2 = bundle.add_encounter(pid, "ambulatory", _at(second, 9), _at(second, 10), clinic, scenario=scenario)
    bundle.add_dx(pid, e1, "hypertension", first)
    bundle.add_dx(pid, e2, "hypertension", second)
    return e2


def build_cbp(bundle):
    scenarios = [
        "controlled",
        "uncontrolled",
        "note_only",
        "one_visit",
        "enrollment_gap",
        "inpatient_reading",
        "same_day_pair",
        "home_digital",
        "home_nondigital",
        "pregnancy",
    ]
    serial = 1000
    for scenario in scenarios:
        for n in range(30):
            serial += 1
            pid = f"P{serial:04d}"
            clinic_index = (5 + (n % 5)) if scenario == "note_only" else (n % 15)
            clinic = f"C{clinic_index + 1:02d}"
            born = date(1970, 4, 15)
            bundle.add_patient(pid, "cbp", scenario, born, clinic)
            if scenario == "enrollment_gap":
                gap_year(bundle, pid)
            else:
                full_year(bundle, pid)
            first = date(2025, 3, 10) + timedelta(days=n % 20)
            second = date(2026, 2, 12) + timedelta(days=n % 20)
            if scenario == "one_visit":
                e1 = bundle.add_encounter(pid, "ambulatory", _at(first, 9), _at(first, 10), clinic, scenario=scenario)
                bundle.add_dx(pid, e1, "hypertension", first)
                late = date(2026, 8, 1)
                e2 = bundle.add_encounter(pid, "ambulatory", _at(late, 9), _at(late, 10), clinic, scenario=scenario)
                bundle.add_dx(pid, e2, "hypertension", late)
                bundle.add_bp(pid, e2, _at(late, 10), 128, 76, "office", "outpatient", "discrete")
                continue
            visit = htn_visits(bundle, pid, clinic, scenario, first, second)
            bp_day = date(2026, 9, 1) + timedelta(days=n % 20)
            if scenario == "controlled" or scenario == "enrollment_gap":
                bundle.add_bp(pid, visit, _at(bp_day, 10), 128, 76, "office", "outpatient", "discrete")
            elif scenario == "uncontrolled":
                bundle.add_bp(pid, visit, _at(bp_day, 10), 148, 86, "office", "outpatient", "discrete")
            elif scenario == "note_only":
                bundle.add_bp(pid, visit, _at(bp_day, 10), None, None, "office", "outpatient", "note_only", note="BP 132/78 today")
            elif scenario == "inpatient_reading":
                bundle.add_bp(pid, visit, _at(date(2026, 4, 1), 10), 130, 80, "office", "outpatient", "discrete")
                stay = bundle.add_encounter(pid, "inpatient", _at(date(2026, 11, 1), 8), _at(date(2026, 11, 3), 14), "H01", pos="21", scenario=scenario)
                bundle.add_bp(pid, stay, _at(date(2026, 11, 2), 6), 190, 100, "office", "inpatient", "discrete")
            elif scenario == "same_day_pair":
                bundle.add_bp(pid, visit, _at(bp_day, 10), 150, 70, "office", "outpatient", "discrete")
                bundle.add_bp(pid, visit, _at(bp_day, 11), 132, 96, "office", "outpatient", "discrete")
            elif scenario == "home_digital":
                bundle.add_bp(pid, "", _at(bp_day, 7), 136, 84, "home_digital", "home", "discrete")
            elif scenario == "home_nondigital":
                bundle.add_bp(pid, "", _at(bp_day, 7), 120, 70, "home_nondigital", "home", "discrete")
            elif scenario == "pregnancy":
                bundle.add_bp(pid, visit, _at(bp_day, 10), 122, 74, "office", "outpatient", "discrete")
                bundle.add_dx(pid, visit, "pregnancy", date(2026, 4, 1))

    exclusions = [
        ("age_under_18", date(2010, 6, 1), None),
        ("age_over_85", date(1940, 1, 1), None),
        ("esrd", date(1955, 1, 1), "esrd"),
        ("death", date(1955, 1, 1), "death"),
        ("frailty_81", date(1944, 1, 1), "frailty"),
        ("palliative", date(1955, 1, 1), "palliative"),
        ("nonacute_inpatient", date(1955, 1, 1), "nonacute"),
        ("institutional", date(1956, 1, 1), "isnp"),
    ]
    for scenario, born, kind in exclusions:
        for n in range(5):
            serial += 1
            pid = f"P{serial:04d}"
            clinic = f"C{(n % 15) + 1:02d}"
            death = date(2026, 11, 1) if kind == "death" else None
            bundle.add_patient(pid, "cbp", scenario, born, clinic, death=death)
            if kind == "isnp":
                full_year(bundle, pid, product="medicare", isnp=True)
            else:
                full_year(bundle, pid)
            visit = htn_visits(bundle, pid, clinic, scenario, date(2025, 5, 1), date(2026, 3, 1))
            bundle.add_bp(pid, visit, _at(date(2026, 8, 1), 10), 126, 74, "office", "outpatient", "discrete")
            if kind == "esrd":
                bundle.add_dx(pid, visit, "esrd", date(2020, 5, 1))
            elif kind == "frailty":
                bundle.add_dx(pid, visit, "frailty", date(2026, 3, 1))
            elif kind == "palliative":
                bundle.add_dx(pid, visit, "palliative", date(2026, 6, 1))
            elif kind == "nonacute":
                bundle.add_encounter(pid, "nonacute_inpatient", _at(date(2026, 7, 1), 8), _at(date(2026, 7, 4), 12), "H02", pos="21", scenario=scenario)

    for n in range(300):
        serial += 1
        pid = f"P{serial:04d}"
        clinic = f"C{(n % 15) + 1:02d}"
        scenario = "routine_controlled" if n < 210 else "routine_uncontrolled"
        bundle.add_patient(pid, "cbp", scenario, date(1968, 7, 20), clinic)
        full_year(bundle, pid)
        first = date(2025, 4, 1) + timedelta(days=n % 25)
        second = date(2026, 1, 15) + timedelta(days=n % 25)
        visit = htn_visits(bundle, pid, clinic, scenario, first, second)
        bp_day = date(2026, 10, 1) + timedelta(days=n % 25)
        if scenario == "routine_controlled":
            bundle.add_bp(pid, visit, _at(bp_day, 10), 124, 78, "office", "outpatient", "discrete")
        else:
            bundle.add_bp(pid, visit, _at(bp_day, 10), 152, 90, "office", "outpatient", "discrete")


def diabetes_visits(bundle, pid, clinic, scenario, first, second):
    e1 = bundle.add_encounter(pid, "ambulatory", _at(first, 9), _at(first, 10), clinic, scenario=scenario)
    e2 = bundle.add_encounter(pid, "ambulatory", _at(second, 9), _at(second, 10), clinic, scenario=scenario)
    bundle.add_dx(pid, e1, "diabetes", first)
    bundle.add_dx(pid, e2, "diabetes", second)
    return e2


def build_gsd(bundle):
    scenarios = [
        "a1c_7_1",
        "a1c_8_4",
        "a1c_10_2",
        "note_only",
        "scanned",
        "newer_result_trapped",
        "gmi_ok",
        "gmi_no_range",
        "pharmacy_path",
        "lab_claim_only",
        "hospice",
        "no_second_dx",
    ]
    serial = 2000
    for scenario in scenarios:
        for n in range(15):
            serial += 1
            pid = f"P{serial:04d}"
            if scenario in {"note_only", "scanned"}:
                clinic = f"C{(5 + (n % 5)) + 1:02d}"
            else:
                clinic = f"C{(n % 15) + 1:02d}"
            bundle.add_patient(pid, "gsd", scenario, date(1966, 2, 2), clinic)
            full_year(bundle, pid)
            first = date(2025, 6, 1)
            second = date(2026, 2, 1) + timedelta(days=n)
            if scenario == "lab_claim_only":
                e1 = bundle.add_encounter(pid, "lab", _at(first, 9), _at(first, 9, 20), "LAB", pos="81", scenario=scenario)
                e2 = bundle.add_encounter(pid, "lab", _at(second, 9), _at(second, 9, 20), "LAB", pos="81", scenario=scenario)
                bundle.add_dx(pid, e1, "diabetes", first)
                bundle.add_dx(pid, e2, "diabetes", second)
                bundle.add_a1c(pid, e2, 7.0, second)
                continue
            if scenario == "no_second_dx":
                e1 = bundle.add_encounter(pid, "ambulatory", _at(second, 9), _at(second, 10), clinic, scenario=scenario)
                bundle.add_dx(pid, e1, "diabetes", second)
                bundle.add_a1c(pid, e1, 7.2, date(2026, 6, 1))
                continue
            if scenario == "pharmacy_path":
                e1 = bundle.add_encounter(pid, "ambulatory", _at(second, 9), _at(second, 10), clinic, scenario=scenario)
                bundle.add_dx(pid, e1, "diabetes", second)
                bundle.add_dispense(pid, "diabetes", date(2026, 3, 1))
                bundle.add_a1c(pid, e1, 7.5, date(2026, 6, 1))
                continue
            visit = diabetes_visits(bundle, pid, clinic, scenario, first, second)
            if scenario == "a1c_7_1":
                bundle.add_a1c(pid, visit, 7.1, date(2026, 6, 1))
            elif scenario == "a1c_8_4":
                bundle.add_a1c(pid, visit, 8.4, date(2026, 6, 1))
            elif scenario == "a1c_10_2":
                bundle.add_a1c(pid, visit, 10.2, date(2026, 6, 1))
            elif scenario == "note_only":
                bundle.add_a1c(pid, visit, None, date(2026, 7, 15), capture="note_only", note="A1c 7.4 per patient")
            elif scenario == "scanned":
                bundle.add_a1c(pid, visit, None, date(2026, 7, 20), capture="scanned_pdf", note="outside lab PDF")
            elif scenario == "newer_result_trapped":
                bundle.add_a1c(pid, visit, 9.4, date(2026, 3, 1))
                bundle.add_a1c(pid, visit, None, date(2026, 11, 1), capture="note_only", note="A1c 7.1 at retail clinic")
            elif scenario == "gmi_ok":
                bundle.add_a1c(
                    pid, visit, 6.9, date(2026, 10, 16), analyte="gmi",
                    range_start=date(2026, 10, 1), range_end=date(2026, 10, 15),
                )
            elif scenario == "gmi_no_range":
                bundle.add_a1c(pid, visit, 7.0, date(2026, 9, 1), analyte="gmi")
            elif scenario == "hospice":
                bundle.add_a1c(pid, visit, 7.0, date(2026, 4, 1))
                bundle.add_encounter(pid, "hospice", _at(date(2026, 5, 1), 9), _at(date(2026, 5, 1), 10), clinic, scenario=scenario)

    for n in range(15):
        serial += 1
        pid = f"P{serial:04d}"
        clinic = f"C{(n % 15) + 1:02d}"
        bundle.add_patient(pid, "gsd", "enrollment_gap", date(1964, 9, 9), clinic)
        gap_year(bundle, pid)
        visit = diabetes_visits(bundle, pid, clinic, "enrollment_gap", date(2025, 5, 1), date(2026, 1, 20))
        bundle.add_a1c(pid, visit, 7.0, date(2026, 5, 1))

    for n in range(120):
        serial += 1
        pid = f"P{serial:04d}"
        clinic = f"C{(n % 15) + 1:02d}"
        if n < 84:
            scenario, value = "routine_lt8", 7.2
        elif n < 108:
            scenario, value = "routine_mid", 8.5
        else:
            scenario, value = "routine_gt9", 10.5
        bundle.add_patient(pid, "gsd", scenario, date(1972, 11, 3), clinic)
        full_year(bundle, pid)
        visit = diabetes_visits(bundle, pid, clinic, scenario, date(2025, 8, 1), date(2026, 3, 15) + timedelta(days=n % 10))
        bundle.add_a1c(pid, visit, value, date(2026, 8, 1) + timedelta(days=n % 10))


def build_cms(bundle):
    hospitals = ["H01", "H02", "H03"]
    scenarios = [
        "glucose_55",
        "glucose_32",
        "false_low",
        "repeat_too_late",
        "order_not_given",
        "med_too_early",
        "ed_stitched",
        "ed_not_stitched",
        "mmol",
        "urine",
        "age_17",
        "discharge_2027",
        "glucose_40",
        "repeat_80",
        "two_lows",
    ]
    serial = 3000
    for h_index, hospital in enumerate(hospitals):
        for s_index, scenario in enumerate(scenarios):
            serial += 1
            pid = f"P{serial:04d}"
            born = date(2008, 8, 1) if scenario == "age_17" else date(1956, 3, 1)
            bundle.add_patient(pid, "cms", scenario, born, "")
            full_year(bundle, pid)
            admit_day = date(2026, 5, 2) + timedelta(days=s_index + h_index)
            admit = _at(admit_day, 12)
            discharge = admit + timedelta(days=3)
            if scenario == "discharge_2027":
                admit = datetime(2026, 12, 30, 8, 0)
                discharge = datetime(2027, 1, 3, 10, 0)
            stay = bundle.add_encounter(pid, "inpatient", admit, discharge, hospital, pos="21", scenario=scenario)
            _cms_case(bundle, pid, stay, hospital, scenario, admit)

    for h_index, hospital in enumerate(hospitals):
        for n in range(150):
            serial += 1
            pid = f"P{serial:04d}"
            bundle.add_patient(pid, "cms", "background", date(1956, 1, 15), "")
            full_year(bundle, pid)
            admit_day = date(2026, 3, 1) + timedelta(days=(n * 2 + h_index) % 200)
            admit = _at(admit_day, 8)
            discharge = admit + timedelta(days=3)
            stay = bundle.add_encounter(pid, "inpatient", admit, discharge, hospital, pos="21", scenario="background")
            bundle.add_admin(pid, stay, admit + timedelta(hours=2))
            bundle.add_glucose(pid, stay, admit + timedelta(hours=8), 142, specimen="blood")


def _cms_case(bundle, pid, stay, hospital, scenario, admit):
    insulin_at = admit + timedelta(hours=2)
    low_at = admit + timedelta(hours=6)
    if scenario == "glucose_55":
        bundle.add_admin(pid, stay, insulin_at)
        bundle.add_glucose(pid, stay, low_at, 55)
    elif scenario == "glucose_32":
        bundle.add_admin(pid, stay, insulin_at)
        bundle.add_glucose(pid, stay, low_at, 32)
    elif scenario == "false_low":
        bundle.add_admin(pid, stay, insulin_at)
        low_id = bundle.add_glucose(pid, stay, low_at, 28)
        if hospital == "H01":
            bundle.add_glucose(pid, stay, low_at + timedelta(minutes=3), 110)
        elif hospital == "H02":
            bundle.add_meter(pid, stay, low_id, low_at + timedelta(minutes=3), 110)
        else:
            bundle.add_glucose(pid, stay, low_at + timedelta(minutes=6), 110)
    elif scenario == "repeat_too_late":
        bundle.add_admin(pid, stay, insulin_at)
        bundle.add_glucose(pid, stay, low_at, 28)
        bundle.add_glucose(pid, stay, low_at + timedelta(minutes=8), 110)
    elif scenario == "order_not_given":
        bundle.add_admin(pid, stay, insulin_at, action="ordered_not_given")
        bundle.add_glucose(pid, stay, low_at, 30)
    elif scenario == "med_too_early":
        bundle.add_admin(pid, stay, admit)
        bundle.add_glucose(pid, stay, admit + timedelta(hours=30), 31)
    elif scenario == "ed_stitched":
        ed_end = admit - timedelta(hours=1)
        ed_start = ed_end - timedelta(hours=3)
        ed = bundle.add_encounter(pid, "emergency", ed_start, ed_end, hospital, pos="23", scenario=scenario)
        bundle.add_admin(pid, ed, ed_start + timedelta(minutes=30))
        bundle.add_glucose(pid, ed, ed_start + timedelta(hours=1), 30)
    elif scenario == "ed_not_stitched":
        ed_end = admit - timedelta(hours=2)
        ed_start = ed_end - timedelta(hours=2)
        ed = bundle.add_encounter(pid, "emergency", ed_start, ed_end, hospital, pos="23", scenario=scenario)
        bundle.add_glucose(pid, ed, ed_start + timedelta(hours=1), 30)
        bundle.add_admin(pid, stay, admit + timedelta(hours=1))
        bundle.add_glucose(pid, stay, admit + timedelta(hours=4), 120, specimen="blood")
    elif scenario == "mmol":
        bundle.add_admin(pid, stay, insulin_at)
        bundle.add_glucose(pid, stay, low_at, 1.6, unit="mmol/L", specimen="blood")
    elif scenario == "urine":
        bundle.add_admin(pid, stay, insulin_at)
        bundle.add_glucose(pid, stay, low_at, 20, specimen="urine", flag=True)
        bundle.add_glucose(pid, stay, low_at + timedelta(minutes=10), 90, specimen="blood")
    elif scenario == "age_17":
        bundle.add_admin(pid, stay, insulin_at)
        bundle.add_glucose(pid, stay, low_at, 29)
    elif scenario == "discharge_2027":
        bundle.add_admin(pid, stay, admit + timedelta(hours=4))
        bundle.add_glucose(pid, stay, admit + timedelta(hours=8), 27)
    elif scenario == "glucose_40":
        bundle.add_admin(pid, stay, insulin_at)
        bundle.add_glucose(pid, stay, low_at, 40)
    elif scenario == "repeat_80":
        bundle.add_admin(pid, stay, insulin_at)
        bundle.add_glucose(pid, stay, low_at, 28)
        bundle.add_glucose(pid, stay, low_at + timedelta(minutes=4), 80)
    elif scenario == "two_lows":
        bundle.add_admin(pid, stay, insulin_at)
        bundle.add_glucose(pid, stay, low_at, 30)
        bundle.add_glucose(pid, stay, low_at + timedelta(hours=14), 35)


def facilities():
    rows = []
    for n in range(1, 16):
        rows.append({
            "facility_id": f"C{n:02d}",
            "facility_name": f"Outpatient clinic {n:02d}",
            "facility_type": "clinic",
        })
    for fid, name in (("H01", "Hospital A"), ("H02", "Hospital B"), ("H03", "Hospital C"), ("LAB", "Reference laboratory")):
        rows.append({"facility_id": fid, "facility_name": name, "facility_type": "hospital" if fid.startswith("H") else "laboratory"})
    return rows


def dictionary_rows():
    rows = [
        ("patients", "patient_id", "Identifier. Synthetic."),
        ("patients", "cohort", "Which teaching cohort the person belongs to: cbp, gsd, or cms."),
        ("patients", "scenario", "Named situation used to check the rules. Not a clinical field."),
        ("patients", "birth_date", "Used for age on 31 Dec 2026, and for age at inpatient start."),
        ("patients", "death_date", "Death during 2026 removes the person from CBP and GSD."),
        ("patients", "clinic_id", "Attributed clinic for the HEDIS clinic rates."),
        ("patients", "data_source", "Always synthetic."),
        ("enrollment_spans", "span_start", "Membership start. Payer file, not the EHR."),
        ("enrollment_spans", "span_end", "Membership end."),
        ("enrollment_spans", "medical_benefit", "Required for the GSD payer-aligned rate."),
        ("enrollment_spans", "product_line", "commercial, medicare, or medicaid. GSD institutional exclusion requires medicare."),
        ("enrollment_spans", "isnp", "Institutional special needs plan flag from the payer."),
        ("enrollment_spans", "lti", "Long-term institution flag from the payer."),
        ("encounters", "encounter_class", "ambulatory, telephone, online, emergency, observation, inpatient, nonacute_inpatient, hospice, or lab."),
        ("encounters", "start_datetime", "Arrival or visit start. CMS age uses the inpatient start."),
        ("encounters", "end_datetime", "CMS816 includes a stay only when this timestamp falls in 2026."),
        ("encounters", "place_of_service", "81 marks a laboratory claim, which cannot identify diabetes."),
        ("diagnoses", "concept", "Demonstration concept the calculator uses. This is not a HEDIS value set."),
        ("diagnoses", "code", "Illustrative ICD-10 code stored beside the concept. The calculator does not read it."),
        ("blood_pressures", "systolic", "Blank when the reading exists only as text."),
        ("blood_pressures", "diastolic", "Blank when the reading exists only as text."),
        ("blood_pressures", "source", "office, home_digital, or home_nondigital."),
        ("blood_pressures", "setting", "outpatient, inpatient, emergency, or home."),
        ("blood_pressures", "capture", "discrete or note_only."),
        ("blood_pressures", "procedure_diet_change", "True when the reading falls on a day the CBP rules reject."),
        ("glycemic_results", "analyte", "a1c or gmi."),
        ("glycemic_results", "value", "Blank when the result is a note or a scanned document."),
        ("glycemic_results", "capture", "discrete, note_only, or scanned_pdf."),
        ("glycemic_results", "gmi_range_end", "The measure dates a GMI on this day. Blank means the GMI cannot be used."),
        ("glucose_results", "drawn_at", "Specimen time. Both CMS816 clocks use this, not posted_at."),
        ("glucose_results", "posted_at", "When the result hit the chart. Present so the two clocks can be compared. Not used in the rate."),
        ("glucose_results", "unit", "mg/dL or mmol/L. mmol/L is multiplied by 18 before the threshold."),
        ("glucose_results", "specimen", "capillary, blood, interstitial, or urine. Urine is ignored."),
        ("glucose_results", "in_glucose_value_set", "Demonstration stand-in for the CMS glucose value set."),
        ("med_administrations", "action", "given or ordered_not_given. Only given doses enter CMS816."),
        ("med_administrations", "in_hypoglycemic_value_set", "Demonstration stand-in for OID 2.16.840.1.113762.1.4.1196.393."),
        ("med_dispenses", "drug_class", "diabetes or dementia. Stand-in for the HEDIS medication lists."),
        ("meter_held_glucose", "drawn_at", "A bedside repeat that is not in the EHR extract."),
        ("meter_held_glucose", "related_low_result_id", "The low glucose this repeat would have cleared."),
    ]
    return [{"table_name": table, "column_name": column, "description": description} for table, column, description in rows]


def write_table(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_readme(bundle):
    text = f"""# Synthetic extract

This folder is invented data for the measurement year 1 January 2026 through 31 December 2026. Every patient identifier is synthetic. Nothing here came from an EHR, a payer, or a hospital.

The extract is a teaching sample with three cohorts in one set of files: hypertension (CBP), diabetes (GSD), and inpatient stays (CMS816v5). Documentation failures are planted so they can be counted. Rates from this folder are not prevalence and are not a health system's performance.

`meter_held_glucose.csv` is not part of the EHR extract. It is the bedside file the EHR did not receive. The official CMS816v5 rate ignores it.

Rebuild from the repository root:

```
python3 src/test_measures.py
python3 src/generate_extract.py
python3 src/profile_measures.py
```

Row counts in this build: {len(bundle.patients)} patients, {len(bundle.encounters)} encounters, {len(bundle.bps)} blood pressures, {len(bundle.glycemic)} glycemic results, {len(bundle.glucose)} glucose results, {len(bundle.meter)} meter-held glucose results.
"""
    (OUT / "README.md").write_text(text)


def main():
    bundle = Bundle()
    build_cbp(bundle)
    build_gsd(bundle)
    build_cms(bundle)
    write_table(OUT / "facilities.csv", facilities())
    write_table(OUT / "patients.csv", bundle.patients)
    write_table(OUT / "enrollment_spans.csv", bundle.enrollment)
    write_table(OUT / "encounters.csv", bundle.encounters)
    write_table(OUT / "diagnoses.csv", bundle.diagnoses)
    write_table(OUT / "blood_pressures.csv", bundle.bps)
    write_table(OUT / "glycemic_results.csv", bundle.glycemic)
    write_table(OUT / "glucose_results.csv", bundle.glucose)
    write_table(OUT / "med_administrations.csv", bundle.admins)
    write_table(OUT / "med_dispenses.csv", bundle.dispenses)
    write_table(OUT / "meter_held_glucose.csv", bundle.meter)
    write_table(OUT / "data_dictionary.csv", dictionary_rows())
    write_readme(bundle)
    print(f"Wrote {len(bundle.patients)} synthetic patients to {OUT}")


if __name__ == "__main__":
    sys.exit(main())
