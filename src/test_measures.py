"""Logic checks for the operational measure rules. These rows are fixtures, not the extract."""

from __future__ import annotations

import sys
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from measures import (  # noqa: E402
    continuously_enrolled,
    evaluate_cbp,
    evaluate_cms816,
    evaluate_gsd,
)


def patient(pid="P1", born=date(1970, 4, 15), death=None, clinic="C01", scenario="fixture"):
    return {
        "patient_id": pid,
        "birth_date": born,
        "death_date": death,
        "clinic_id": clinic,
        "scenario": scenario,
    }


def span(start=date(2026, 1, 1), end=date(2026, 12, 31), medical=True, product="commercial", isnp=False, lti=False):
    return {
        "span_start": start,
        "span_end": end,
        "medical_benefit": medical,
        "product_line": product,
        "isnp": isnp,
        "lti": lti,
    }


def encounter(eid, pid, kind, start, end=None, facility="C01", pos="11", scenario="fixture"):
    if isinstance(start, date) and not isinstance(start, datetime):
        start = datetime(start.year, start.month, start.day, 9, 0)
    if end is None:
        end = start + timedelta(hours=1)
    return {
        "encounter_id": eid,
        "patient_id": pid,
        "encounter_class": kind,
        "start": start,
        "end": end,
        "facility_id": facility,
        "place_of_service": pos,
        "scenario": scenario,
    }


def diagnosis(eid, concept, recorded, pid="P1"):
    if isinstance(recorded, datetime):
        recorded = recorded.date()
    return {"encounter_id": eid, "patient_id": pid, "concept": concept, "recorded_date": recorded}


def bp(taken, systolic, diastolic, setting="outpatient", source="office", capture="discrete", diet=False, pid="P1"):
    if isinstance(taken, date) and not isinstance(taken, datetime):
        taken = datetime(taken.year, taken.month, taken.day, 10, 0)
    return {
        "patient_id": pid,
        "taken_at": taken,
        "systolic": systolic,
        "diastolic": diastolic,
        "setting": setting,
        "source": source,
        "capture": capture,
        "procedure_diet_change": diet,
    }


def htn_pair():
    first = encounter("E1", "P1", "ambulatory", date(2025, 3, 10))
    second = encounter("E2", "P1", "ambulatory", date(2026, 2, 12))
    diagnoses = [
        diagnosis("E1", "hypertension", date(2025, 3, 10)),
        diagnosis("E2", "hypertension", date(2026, 2, 12)),
    ]
    return [first, second], diagnoses


class EnrollmentTests(unittest.TestCase):
    def test_full_year(self):
        self.assertTrue(continuously_enrolled([span()]))

    def test_gap_of_45_days_passes(self):
        spans = [span(date(2026, 1, 1), date(2026, 3, 1)), span(date(2026, 4, 16), date(2026, 12, 31))]
        self.assertTrue(continuously_enrolled(spans))

    def test_gap_of_46_days_fails(self):
        spans = [span(date(2026, 1, 1), date(2026, 3, 1)), span(date(2026, 4, 17), date(2026, 12, 31))]
        self.assertFalse(continuously_enrolled(spans))

    def test_two_gaps_fail(self):
        spans = [
            span(date(2026, 1, 1), date(2026, 1, 31)),
            span(date(2026, 2, 10), date(2026, 6, 1)),
            span(date(2026, 6, 20), date(2026, 12, 31)),
        ]
        self.assertFalse(continuously_enrolled(spans))

    def test_not_enrolled_on_anchor_fails(self):
        self.assertFalse(continuously_enrolled([span(end=date(2026, 12, 1))]))

    def test_gsd_requires_medical_benefit(self):
        self.assertFalse(continuously_enrolled([span(medical=False)], require_medical=True))
        self.assertTrue(continuously_enrolled([span(medical=False)], require_medical=False))


class CbpTests(unittest.TestCase):
    def test_same_day_uses_lowest_of_each(self):
        encounters, diagnoses = htn_pair()
        readings = [
            bp(date(2026, 9, 1), 150, 70),
            bp(datetime(2026, 9, 1, 11, 0), 132, 96),
        ]
        result = evaluate_cbp(patient(), encounters, diagnoses, readings, [span()], [])
        self.assertTrue(result["in_ehr_denominator"])
        self.assertEqual(result["systolic"], 132)
        self.assertEqual(result["diastolic"], 70)
        self.assertTrue(result["controlled"])

    def test_inpatient_reading_is_ignored(self):
        encounters, diagnoses = htn_pair()
        readings = [
            bp(date(2026, 4, 1), 130, 80),
            bp(date(2026, 11, 1), 190, 100, setting="inpatient"),
        ]
        result = evaluate_cbp(patient(), encounters, diagnoses, readings, [span()], [])
        self.assertEqual(result["systolic"], 130)
        self.assertTrue(result["controlled"])

    def test_reading_before_second_diagnosis_is_ignored(self):
        encounters, diagnoses = htn_pair()
        readings = [
            bp(date(2026, 1, 5), 120, 70),
            bp(date(2026, 9, 1), 146, 88),
        ]
        result = evaluate_cbp(patient(), encounters, diagnoses, readings, [span()], [])
        self.assertEqual(result["bp_date"], date(2026, 9, 1))
        self.assertFalse(result["controlled"])

    def test_note_only_is_not_usable(self):
        encounters, diagnoses = htn_pair()
        readings = [bp(date(2026, 9, 1), None, None, capture="note_only")]
        result = evaluate_cbp(patient(), encounters, diagnoses, readings, [span()], [])
        self.assertTrue(result["in_ehr_denominator"])
        self.assertTrue(result["no_usable_bp"])
        self.assertFalse(result["controlled"])

    def test_nondigital_home_reading_does_not_count(self):
        encounters, diagnoses = htn_pair()
        readings = [bp(date(2026, 9, 1), 120, 70, setting="home", source="home_nondigital")]
        result = evaluate_cbp(patient(), encounters, diagnoses, readings, [span()], [])
        self.assertTrue(result["no_usable_bp"])

    def test_diet_change_day_is_not_used(self):
        encounters, diagnoses = htn_pair()
        readings = [
            bp(date(2026, 8, 1), 128, 78),
            bp(date(2026, 10, 1), 110, 70, diet=True),
        ]
        result = evaluate_cbp(patient(), encounters, diagnoses, readings, [span()], [])
        self.assertEqual(result["bp_date"], date(2026, 8, 1))

    def test_one_visit_is_out(self):
        only = encounter("E1", "P1", "ambulatory", date(2025, 4, 1))
        late = encounter("E2", "P1", "ambulatory", date(2026, 8, 1))
        diagnoses = [
            diagnosis("E1", "hypertension", date(2025, 4, 1)),
            diagnosis("E2", "hypertension", date(2026, 8, 1)),
        ]
        result = evaluate_cbp(patient(), [only, late], diagnoses, [], [span()], [])
        self.assertFalse(result["in_ehr_denominator"])
        self.assertEqual(result["htn_visit_count"], 1)

    def test_pregnancy_excluded(self):
        encounters, diagnoses = htn_pair()
        diagnoses.append(diagnosis("E2", "pregnancy", date(2026, 3, 1)))
        result = evaluate_cbp(patient(), encounters, diagnoses, [bp(date(2026, 9, 1), 120, 70)], [span()], [])
        self.assertEqual(result["exclusion"], "pregnancy")
        self.assertFalse(result["in_ehr_denominator"])

    def test_enrollment_gap_stays_in_ehr_rate(self):
        encounters, diagnoses = htn_pair()
        spans = [span(date(2026, 1, 1), date(2026, 3, 1)), span(date(2026, 6, 1), date(2026, 12, 31))]
        result = evaluate_cbp(patient(), encounters, diagnoses, [bp(date(2026, 9, 1), 128, 76)], spans, [])
        self.assertTrue(result["in_ehr_denominator"])
        self.assertFalse(result["in_payer_denominator"])
        self.assertTrue(result["controlled"])

    def test_age_bounds(self):
        encounters, diagnoses = htn_pair()
        young = evaluate_cbp(patient(born=date(2009, 1, 1)), encounters, diagnoses, [], [span()], [])
        old = evaluate_cbp(patient(born=date(1940, 1, 1)), encounters, diagnoses, [], [span()], [])
        edge = evaluate_cbp(patient(born=date(1941, 12, 31)), encounters, diagnoses, [], [span()], [])
        self.assertFalse(young["age_ok"])
        self.assertFalse(old["age_ok"])
        self.assertTrue(edge["age_ok"])
        self.assertEqual(edge["age"], 85)


class GsdTests(unittest.TestCase):
    def base(self):
        first = encounter("E1", "P1", "ambulatory", date(2025, 4, 1))
        second = encounter("E2", "P1", "ambulatory", date(2026, 2, 1))
        diagnoses = [
            diagnosis("E1", "diabetes", date(2025, 4, 1)),
            diagnosis("E2", "diabetes", date(2026, 2, 1)),
        ]
        return [first, second], diagnoses

    def test_bands(self):
        encounters, diagnoses = self.base()
        low = evaluate_gsd(patient(), encounters, diagnoses, [self.a1c(7.9)], [span()], [])
        mid_low = evaluate_gsd(patient(), encounters, diagnoses, [self.a1c(8.0)], [span()], [])
        mid_high = evaluate_gsd(patient(), encounters, diagnoses, [self.a1c(9.0)], [span()], [])
        high = evaluate_gsd(patient(), encounters, diagnoses, [self.a1c(9.1)], [span()], [])
        missing = evaluate_gsd(patient(), encounters, diagnoses, [], [span()], [])
        self.assertEqual(low["band"], "lt8")
        self.assertEqual(mid_low["band"], "mid")
        self.assertEqual(mid_high["band"], "mid")
        self.assertEqual(high["band"], "gt9")
        self.assertEqual(missing["band"], "missing")

    def test_same_day_uses_lowest(self):
        encounters, diagnoses = self.base()
        results = [self.a1c(8.4, date(2026, 6, 1)), self.a1c(7.2, date(2026, 6, 1))]
        result = evaluate_gsd(patient(), encounters, diagnoses, results, [span()], [])
        self.assertEqual(result["value"], 7.2)
        self.assertEqual(result["band"], "lt8")

    def test_most_recent_wins(self):
        encounters, diagnoses = self.base()
        results = [self.a1c(6.8, date(2026, 3, 1)), self.a1c(10.2, date(2026, 11, 1))]
        result = evaluate_gsd(patient(), encounters, diagnoses, results, [span()], [])
        self.assertEqual(result["value"], 10.2)
        self.assertEqual(result["band"], "gt9")

    def test_gmi_uses_range_end(self):
        encounters, diagnoses = self.base()
        results = [
            self.a1c(10.4, date(2026, 8, 1)),
            {
                "analyte": "gmi",
                "value": 6.9,
                "unit": "%",
                "capture": "discrete",
                "result_date": date(2026, 9, 1),
                "gmi_range_end": date(2026, 10, 15),
            },
        ]
        result = evaluate_gsd(patient(), encounters, diagnoses, results, [span()], [])
        self.assertEqual(result["result_date"], date(2026, 10, 15))
        self.assertEqual(result["analyte"], "gmi")
        self.assertEqual(result["band"], "lt8")

    def test_gmi_without_range_is_missing(self):
        encounters, diagnoses = self.base()
        results = [{
            "analyte": "gmi",
            "value": 7.0,
            "unit": "%",
            "capture": "discrete",
            "result_date": date(2026, 9, 1),
            "gmi_range_end": None,
        }]
        result = evaluate_gsd(patient(), encounters, diagnoses, results, [span()], [])
        self.assertEqual(result["band"], "missing")

    def test_note_does_not_replace_an_older_lab(self):
        encounters, diagnoses = self.base()
        results = [
            self.a1c(9.4, date(2026, 3, 1)),
            {"analyte": "a1c", "value": None, "unit": "%", "capture": "note_only", "result_date": date(2026, 11, 1), "gmi_range_end": None},
        ]
        result = evaluate_gsd(patient(), encounters, diagnoses, results, [span()], [])
        self.assertEqual(result["band"], "gt9")
        self.assertTrue(result["trapped_later_result"])

    def test_lab_claim_does_not_identify_diabetes(self):
        first = encounter("E1", "P1", "lab", date(2025, 4, 1), pos="81")
        second = encounter("E2", "P1", "lab", date(2026, 2, 1), pos="81")
        diagnoses = [
            diagnosis("E1", "diabetes", date(2025, 4, 1)),
            diagnosis("E2", "diabetes", date(2026, 2, 1)),
        ]
        result = evaluate_gsd(patient(), [first, second], diagnoses, [self.a1c(7.0)], [span()], [])
        self.assertFalse(result["in_ehr_denominator"])
        self.assertIsNone(result["diabetes_method"])

    def test_pharmacy_path(self):
        only = encounter("E1", "P1", "ambulatory", date(2026, 2, 1))
        diagnoses = [diagnosis("E1", "diabetes", date(2026, 2, 1))]
        dispenses = [{"drug_class": "diabetes", "fill_date": date(2026, 3, 1)}]
        result = evaluate_gsd(patient(), [only], diagnoses, [self.a1c(7.5)], [span()], dispenses)
        self.assertEqual(result["diabetes_method"], "pharmacy")
        self.assertEqual(result["band"], "lt8")

    def test_hospice_excluded(self):
        encounters, diagnoses = self.base()
        hospice = encounter("EH", "P1", "hospice", date(2026, 5, 1))
        result = evaluate_gsd(patient(), encounters + [hospice], diagnoses, [self.a1c(7.0)], [span()], [])
        self.assertEqual(result["exclusion"], "hospice")

    def a1c(self, value, on=date(2026, 6, 1)):
        return {
            "analyte": "a1c",
            "value": value,
            "unit": "%",
            "capture": "discrete",
            "result_date": on,
            "gmi_range_end": None,
        }


class CmsTests(unittest.TestCase):
    def stay(self, start=datetime(2026, 5, 1, 12, 0), end=datetime(2026, 5, 4, 15, 0), facility="H01", scenario="fixture", pid="P1"):
        return encounter("IP", pid, "inpatient", start, end, facility, scenario=scenario)

    def insulin(self, at, action="given", pid="P1", eid="IP"):
        return {
            "patient_id": pid,
            "encounter_id": eid,
            "action": action,
            "in_hypoglycemic_value_set": True,
            "start": at,
        }

    def glucose(self, at, value, unit="mg/dL", specimen="capillary", rid="G1", flag=True, pid="P1"):
        return {
            "result_id": rid,
            "patient_id": pid,
            "drawn_at": at,
            "value": value,
            "unit": unit,
            "specimen": specimen,
            "in_glucose_value_set": flag,
            "capture": "discrete",
        }

    def test_under_40_is_numerator(self):
        stay = self.stay()
        person = patient()
        result = evaluate_cms816(
            stay,
            person,
            [stay],
            [self.insulin(datetime(2026, 5, 1, 14, 0))],
            [self.glucose(datetime(2026, 5, 1, 18, 0), 32)],
            [],
        )
        self.assertTrue(result["in_numerator"])
        self.assertEqual(result["clearance"], "no_clearing_repeat")

    def test_exactly_40_is_not_harm(self):
        stay = self.stay()
        result = evaluate_cms816(
            stay,
            patient(),
            [stay],
            [self.insulin(datetime(2026, 5, 1, 14, 0))],
            [self.glucose(datetime(2026, 5, 1, 18, 0), 40)],
            [],
        )
        self.assertTrue(result["in_denominator"])
        self.assertFalse(result["in_numerator"])

    def test_repeat_over_80_within_five_minutes_clears(self):
        stay = self.stay()
        low_at = datetime(2026, 5, 1, 18, 0)
        glucoses = [
            self.glucose(low_at, 28, rid="G1"),
            self.glucose(low_at + timedelta(minutes=5), 81, rid="G2"),
        ]
        result = evaluate_cms816(stay, patient(), [stay], [self.insulin(datetime(2026, 5, 1, 14, 0))], glucoses, [])
        self.assertFalse(result["in_numerator"])
        self.assertEqual(result["clearance"], "cleared_in_extract")

    def test_repeat_of_exactly_80_does_not_clear(self):
        stay = self.stay()
        low_at = datetime(2026, 5, 1, 18, 0)
        glucoses = [
            self.glucose(low_at, 28, rid="G1"),
            self.glucose(low_at + timedelta(minutes=4), 80, rid="G2"),
        ]
        result = evaluate_cms816(stay, patient(), [stay], [self.insulin(datetime(2026, 5, 1, 14, 0))], glucoses, [])
        self.assertTrue(result["in_numerator"])

    def test_repeat_after_five_minutes_does_not_clear(self):
        stay = self.stay()
        low_at = datetime(2026, 5, 1, 18, 0)
        glucoses = [
            self.glucose(low_at, 28, rid="G1"),
            self.glucose(low_at + timedelta(minutes=5, seconds=1), 110, rid="G2"),
        ]
        result = evaluate_cms816(stay, patient(), [stay], [self.insulin(datetime(2026, 5, 1, 14, 0))], glucoses, [])
        self.assertTrue(result["in_numerator"])
        self.assertEqual(result["clearance"], "repeat_outside_five_minutes")

    def test_medication_window_is_inclusive_of_24_hours(self):
        stay = self.stay()
        drawn = datetime(2026, 5, 2, 14, 0)
        on_time = evaluate_cms816(
            stay, patient(), [stay], [self.insulin(drawn - timedelta(hours=24))], [self.glucose(drawn, 30)], []
        )
        late = evaluate_cms816(
            stay,
            patient(),
            [stay],
            [self.insulin(drawn - timedelta(hours=24, seconds=1))],
            [self.glucose(drawn, 30, rid="G9")],
            [],
        )
        self.assertTrue(on_time["in_numerator"])
        self.assertTrue(late["in_denominator"])
        self.assertFalse(late["in_numerator"])

    def test_order_not_given_is_out_of_denominator(self):
        stay = self.stay()
        result = evaluate_cms816(
            stay,
            patient(),
            [stay],
            [self.insulin(datetime(2026, 5, 1, 14, 0), action="ordered_not_given")],
            [self.glucose(datetime(2026, 5, 1, 18, 0), 30)],
            [],
        )
        self.assertFalse(result["in_denominator"])

    def test_ed_gap_of_one_hour_is_included(self):
        ip_start = datetime(2026, 5, 1, 12, 0)
        stay = self.stay(start=ip_start)
        ed = encounter("ED", "P1", "emergency", datetime(2026, 5, 1, 8, 0), datetime(2026, 5, 1, 11, 0))
        result = evaluate_cms816(
            stay,
            patient(),
            [stay, ed],
            [self.insulin(datetime(2026, 5, 1, 8, 30), eid="ED")],
            [self.glucose(datetime(2026, 5, 1, 9, 0), 30)],
            [],
        )
        self.assertTrue(result["in_numerator"])

    def test_ed_gap_over_one_hour_is_excluded(self):
        ip_start = datetime(2026, 5, 1, 12, 0)
        stay = self.stay(start=ip_start)
        ed = encounter("ED", "P1", "emergency", datetime(2026, 5, 1, 8, 0), datetime(2026, 5, 1, 10, 58))
        result = evaluate_cms816(
            stay,
            patient(),
            [stay, ed],
            [self.insulin(datetime(2026, 5, 1, 13, 0))],
            [self.glucose(datetime(2026, 5, 1, 9, 0), 30)],
            [],
        )
        self.assertTrue(result["in_denominator"])
        self.assertFalse(result["in_numerator"])

    def test_mmol_is_converted(self):
        stay = self.stay()
        result = evaluate_cms816(
            stay,
            patient(),
            [stay],
            [self.insulin(datetime(2026, 5, 1, 14, 0))],
            [self.glucose(datetime(2026, 5, 1, 18, 0), 1.6, unit="mmol/L", specimen="blood")],
            [],
        )
        self.assertTrue(result["in_numerator"])

    def test_urine_glucose_is_ignored(self):
        stay = self.stay()
        glucoses = [
            self.glucose(datetime(2026, 5, 1, 18, 0), 20, specimen="urine", rid="U", flag=True),
            self.glucose(datetime(2026, 5, 1, 18, 10), 90, specimen="blood", rid="B"),
        ]
        result = evaluate_cms816(stay, patient(), [stay], [self.insulin(datetime(2026, 5, 1, 14, 0))], glucoses, [])
        self.assertFalse(result["in_numerator"])

    def test_two_lows_count_once(self):
        stay = self.stay()
        glucoses = [
            self.glucose(datetime(2026, 5, 1, 18, 0), 30, rid="G1"),
            self.glucose(datetime(2026, 5, 2, 8, 0), 35, rid="G2"),
        ]
        result = evaluate_cms816(stay, patient(), [stay], [self.insulin(datetime(2026, 5, 1, 14, 0))], glucoses, [])
        self.assertTrue(result["in_numerator"])

    def test_discharge_in_2027_is_out(self):
        stay = self.stay(start=datetime(2026, 12, 30, 8, 0), end=datetime(2027, 1, 3, 10, 0))
        result = evaluate_cms816(
            stay,
            patient(),
            [stay],
            [self.insulin(datetime(2026, 12, 30, 12, 0))],
            [self.glucose(datetime(2026, 12, 31, 8, 0), 30)],
            [],
        )
        self.assertFalse(result["in_period"])
        self.assertFalse(result["in_denominator"])

    def test_age_uses_inpatient_start(self):
        stay = self.stay(start=datetime(2026, 5, 2, 8, 0))
        result = evaluate_cms816(
            stay,
            patient(born=date(2008, 5, 3)),
            [stay],
            [self.insulin(datetime(2026, 5, 2, 10, 0))],
            [self.glucose(datetime(2026, 5, 2, 12, 0), 30)],
            [],
        )
        self.assertEqual(result["age"], 17)
        self.assertFalse(result["in_denominator"])

    def test_meter_repeat_does_not_change_the_official_numerator(self):
        stay = self.stay()
        low_at = datetime(2026, 5, 1, 18, 0)
        official = [self.glucose(low_at, 28, rid="G1")]
        meter = [self.glucose(low_at + timedelta(minutes=3), 110, rid="M1")]
        result = evaluate_cms816(stay, patient(), [stay], [self.insulin(datetime(2026, 5, 1, 14, 0))], official, meter)
        self.assertTrue(result["in_numerator"])
        self.assertTrue(result["meter_would_remove"])
        self.assertEqual(result["clearance"], "meter_not_exported")


if __name__ == "__main__":
    unittest.main()
