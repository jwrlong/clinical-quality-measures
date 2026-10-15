"""Write the Synthea data dictionary from the columns in the raw export.

Meanings follow the Synthea CSV wiki where that page matches this jar.
Where the file differs, the description says so. A column with no entry
fails the script, so the dictionary cannot silently skip a field.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data_raw" / "synthea" / "csv"
FALLBACK = ROOT / "data" / "synthea" / "csv"
OUT = ROOT / "docs" / "synthea-data-dictionary.csv"

# table, column -> type, meaning, code system, key
FIELDS: dict[tuple[str, str], tuple[str, str, str, str]] = {
    ("allergies", "START"): ("date", "Date the allergy was diagnosed.", "", ""),
    ("allergies", "STOP"): ("date", "Date the allergy ended. Blank when it is still present.", "", ""),
    ("allergies", "PATIENT"): ("uuid", "Patient who has the allergy.", "", "FK patients.Id"),
    ("allergies", "ENCOUNTER"): ("uuid", "Encounter at which the allergy was diagnosed.", "", "FK encounters.Id"),
    ("allergies", "CODE"): ("string", "Allergy code. The system depends on SYSTEM.", "SNOMED-CT or RxNorm", ""),
    ("allergies", "SYSTEM"): ("string", "Terminology of CODE. RxNorm for a medication allergy, otherwise SNOMED-CT.", "", ""),
    ("allergies", "DESCRIPTION"): ("string", "Display text for CODE.", "", ""),
    ("allergies", "TYPE"): ("string", "allergy or intolerance.", "", ""),
    ("allergies", "CATEGORY"): ("string", "drug, medication, food, or environment.", "", ""),
    ("allergies", "REACTION1"): ("string", "First reaction, when present.", "SNOMED-CT", ""),
    ("allergies", "DESCRIPTION1"): ("string", "Display text for REACTION1.", "", ""),
    ("allergies", "SEVERITY1"): ("string", "MILD, MODERATE, or SEVERE.", "", ""),
    ("allergies", "REACTION2"): ("string", "Second reaction, when present.", "SNOMED-CT", ""),
    ("allergies", "DESCRIPTION2"): ("string", "Display text for REACTION2.", "", ""),
    ("allergies", "SEVERITY2"): ("string", "MILD, MODERATE, or SEVERE.", "", ""),
    ("careplans", "Id"): ("uuid", "Care plan identifier.", "", "PK"),
    ("careplans", "START"): ("date", "Date the care plan started.", "", ""),
    ("careplans", "STOP"): ("date", "Date the care plan ended. Blank when it is still open.", "", ""),
    ("careplans", "PATIENT"): ("uuid", "Patient the care plan belongs to.", "", "FK patients.Id"),
    ("careplans", "ENCOUNTER"): ("uuid", "Encounter at which the care plan was started.", "", "FK encounters.Id"),
    ("careplans", "CODE"): ("string", "Care plan code.", "SNOMED-CT", ""),
    ("careplans", "DESCRIPTION"): ("string", "Display text for CODE.", "", ""),
    ("careplans", "REASONCODE"): ("string", "Condition the care plan addresses. Often blank in this export.", "SNOMED-CT", ""),
    ("careplans", "REASONDESCRIPTION"): ("string", "Display text for REASONCODE.", "", ""),
    ("claims", "Id"): ("uuid", "Claim identifier.", "", "PK"),
    ("claims", "PATIENTID"): ("uuid", "Patient on the claim.", "", "FK patients.Id"),
    ("claims", "PROVIDERID"): ("uuid", "Billing provider.", "", "FK providers.Id"),
    ("claims", "PRIMARYPATIENTINSURANCEID"): ("uuid", "Primary payer. Blank when the patient is uninsured on that claim.", "", "FK payers.Id"),
    ("claims", "SECONDARYPATIENTINSURANCEID"): ("uuid", "Secondary payer, when present.", "", "FK payers.Id"),
    ("claims", "DEPARTMENTID"): ("numeric", "Placeholder department number, not a clinic key.", "", ""),
    ("claims", "PATIENTDEPARTMENTID"): ("numeric", "Placeholder patient department number.", "", ""),
    ("claims", "DIAGNOSIS1"): ("string", "First diagnosis on the claim.", "SNOMED-CT", ""),
    ("claims", "DIAGNOSIS2"): ("string", "Second diagnosis on the claim.", "SNOMED-CT", ""),
    ("claims", "DIAGNOSIS3"): ("string", "Third diagnosis on the claim.", "SNOMED-CT", ""),
    ("claims", "DIAGNOSIS4"): ("string", "Fourth diagnosis on the claim.", "SNOMED-CT", ""),
    ("claims", "DIAGNOSIS5"): ("string", "Fifth diagnosis on the claim.", "SNOMED-CT", ""),
    ("claims", "DIAGNOSIS6"): ("string", "Sixth diagnosis on the claim.", "SNOMED-CT", ""),
    ("claims", "DIAGNOSIS7"): ("string", "Seventh diagnosis on the claim.", "SNOMED-CT", ""),
    ("claims", "DIAGNOSIS8"): ("string", "Eighth diagnosis on the claim.", "SNOMED-CT", ""),
    ("claims", "REFERRINGPROVIDERID"): ("uuid", "Referring provider, when present.", "", "FK providers.Id"),
    ("claims", "APPOINTMENTID"): ("uuid", "Encounter the claim is for.", "", "FK encounters.Id"),
    ("claims", "CURRENTILLNESSDATE"): ("timestamp", "When the patient experienced symptoms.", "", ""),
    ("claims", "SERVICEDATE"): ("timestamp", "Date of service on the claim.", "", ""),
    ("claims", "SUPERVISINGPROVIDERID"): ("uuid", "Supervising provider, when present.", "", "FK providers.Id"),
    ("claims", "STATUS1"): ("string", "Primary-insurance status, BILLED or CLOSED.", "", ""),
    ("claims", "STATUS2"): ("string", "Secondary-insurance status, BILLED or CLOSED.", "", ""),
    ("claims", "STATUSP"): ("string", "Patient-responsibility status, BILLED or CLOSED.", "", ""),
    ("claims", "OUTSTANDING1"): ("numeric", "Amount still owed by the primary payer.", "", ""),
    ("claims", "OUTSTANDING2"): ("numeric", "Amount still owed by the secondary payer.", "", ""),
    ("claims", "OUTSTANDINGP"): ("numeric", "Amount still owed by the patient.", "", ""),
    ("claims", "LASTBILLEDDATE1"): ("timestamp", "When the claim was sent to the primary payer.", "", ""),
    ("claims", "LASTBILLEDDATE2"): ("timestamp", "When the claim was sent to the secondary payer.", "", ""),
    ("claims", "LASTBILLEDDATEP"): ("timestamp", "When the claim was sent to the patient.", "", ""),
    ("claims", "HEALTHCARECLAIMTYPEID1"): ("numeric", "1 professional, 2 institutional, for the primary claim.", "", ""),
    ("claims", "HEALTHCARECLAIMTYPEID2"): ("numeric", "1 professional, 2 institutional, for the secondary claim.", "", ""),
    ("claims_transactions", "ID"): ("uuid", "Transaction identifier.", "", "PK"),
    ("claims_transactions", "CLAIMID"): ("uuid", "Claim this line belongs to.", "", "FK claims.Id"),
    ("claims_transactions", "CHARGEID"): ("numeric", "Charge number within the claim.", "", ""),
    ("claims_transactions", "PATIENTID"): ("uuid", "Patient on the transaction.", "", "FK patients.Id"),
    ("claims_transactions", "TYPE"): ("string", "CHARGE, PAYMENT, ADJUSTMENT, TRANSFERIN, or TRANSFEROUT.", "", ""),
    ("claims_transactions", "AMOUNT"): ("numeric", "Dollar amount for a charge or transfer in.", "", ""),
    ("claims_transactions", "METHOD"): ("string", "How a payment was made, when TYPE is PAYMENT.", "", ""),
    ("claims_transactions", "FROMDATE"): ("timestamp", "Transaction start.", "", ""),
    ("claims_transactions", "TODATE"): ("timestamp", "Transaction end.", "", ""),
    ("claims_transactions", "PLACEOFSERVICE"): ("uuid", "Organization where the service occurred.", "", "FK organizations.Id"),
    ("claims_transactions", "PROCEDURECODE"): ("string", "Service code. Usually SNOMED-CT. Vaccines may use CVX.", "SNOMED-CT or CVX", ""),
    ("claims_transactions", "MODIFIER1"): ("string", "Procedure modifier. Unused in this generator.", "", ""),
    ("claims_transactions", "MODIFIER2"): ("string", "Second procedure modifier. Unused in this generator.", "", ""),
    ("claims_transactions", "DIAGNOSISREF1"): ("numeric", "Pointer to diagnosis 1 through 8 on the claim.", "", ""),
    ("claims_transactions", "DIAGNOSISREF2"): ("numeric", "Second diagnosis pointer.", "", ""),
    ("claims_transactions", "DIAGNOSISREF3"): ("numeric", "Third diagnosis pointer.", "", ""),
    ("claims_transactions", "DIAGNOSISREF4"): ("numeric", "Fourth diagnosis pointer.", "", ""),
    ("claims_transactions", "UNITS"): ("numeric", "Service units.", "", ""),
    ("claims_transactions", "DEPARTMENTID"): ("numeric", "Placeholder department number.", "", ""),
    ("claims_transactions", "NOTES"): ("string", "Description of the service or transaction.", "", ""),
    ("claims_transactions", "UNITAMOUNT"): ("numeric", "Cost per unit.", "", ""),
    ("claims_transactions", "TRANSFEROUTID"): ("numeric", "Charge id of the matching transfer out, when TYPE is TRANSFERIN.", "", ""),
    ("claims_transactions", "TRANSFERTYPE"): ("string", "1 primary payer, 2 secondary payer, or p patient.", "", ""),
    ("claims_transactions", "PAYMENTS"): ("numeric", "Payment amount when TYPE is PAYMENT.", "", ""),
    ("claims_transactions", "ADJUSTMENTS"): ("numeric", "Adjustment amount when TYPE is ADJUSTMENT.", "", ""),
    ("claims_transactions", "TRANSFERS"): ("numeric", "Transfer amount when TYPE is a transfer.", "", ""),
    ("claims_transactions", "OUTSTANDING"): ("numeric", "Unpaid amount after this transaction.", "", ""),
    ("claims_transactions", "APPOINTMENTID"): ("uuid", "Encounter for the line.", "", "FK encounters.Id"),
    ("claims_transactions", "LINENOTE"): ("string", "Line note.", "", ""),
    ("claims_transactions", "PATIENTINSURANCEID"): ("uuid", "Payer member identifier, when populated.", "", "FK payer_transitions.MEMBERID"),
    ("claims_transactions", "FEESCHEDULEID"): ("numeric", "Fixed to 1 by the generator.", "", ""),
    ("claims_transactions", "PROVIDERID"): ("uuid", "Provider on the line.", "", "FK providers.Id"),
    ("claims_transactions", "SUPERVISINGPROVIDERID"): ("uuid", "Supervising provider, when present.", "", "FK providers.Id"),
    ("conditions", "START"): ("date", "Date the condition was diagnosed. In this export that is the onset, and the code is not repeated on later encounters.", "", ""),
    ("conditions", "STOP"): ("date", "Date the condition resolved. Blank when it is still active.", "", ""),
    ("conditions", "PATIENT"): ("uuid", "Patient with the condition. This table has no primary key of its own.", "", "FK patients.Id"),
    ("conditions", "ENCOUNTER"): ("uuid", "Encounter at which the condition was recorded.", "", "FK encounters.Id"),
    ("conditions", "SYSTEM"): ("string", "Terminology of CODE. Observed value in this export is SNOMED-CT.", "SNOMED-CT", ""),
    ("conditions", "CODE"): ("string", "Condition code.", "SNOMED-CT", ""),
    ("conditions", "DESCRIPTION"): ("string", "Display text for CODE.", "", ""),
    ("devices", "START"): ("timestamp", "When the device was associated with the patient.", "", ""),
    ("devices", "STOP"): ("timestamp", "When the device was removed.", "", ""),
    ("devices", "PATIENT"): ("uuid", "Patient. This table has no primary key of its own.", "", "FK patients.Id"),
    ("devices", "ENCOUNTER"): ("uuid", "Encounter at which the device was associated.", "", "FK encounters.Id"),
    ("devices", "CODE"): ("string", "Device type.", "SNOMED-CT", ""),
    ("devices", "DESCRIPTION"): ("string", "Display text for CODE.", "", ""),
    ("devices", "UDI"): ("string", "Unique device identifier. Synthetic.", "", ""),
    ("encounters", "Id"): ("uuid", "Encounter identifier.", "", "PK"),
    ("encounters", "START"): ("timestamp", "Encounter start, UTC.", "", ""),
    ("encounters", "STOP"): ("timestamp", "Encounter end, UTC.", "", ""),
    ("encounters", "PATIENT"): ("uuid", "Patient.", "", "FK patients.Id"),
    ("encounters", "ORGANIZATION"): ("uuid", "Site of care. This is the clinic grain available in the file.", "", "FK organizations.Id"),
    ("encounters", "PROVIDER"): ("uuid", "Clinician.", "", "FK providers.Id"),
    ("encounters", "PAYER"): ("uuid", "Payer for the encounter.", "", "FK payers.Id"),
    ("encounters", "ENCOUNTERCLASS"): ("string", "Synthea class, such as ambulatory, wellness, outpatient, virtual, emergency, inpatient, urgentcare, home, snf, or hospice.", "", ""),
    ("encounters", "CODE"): ("string", "Encounter type.", "SNOMED-CT", ""),
    ("encounters", "DESCRIPTION"): ("string", "Display text for CODE.", "", ""),
    ("encounters", "BASE_ENCOUNTER_COST"): ("numeric", "Base encounter cost, excluding line items.", "", ""),
    ("encounters", "TOTAL_CLAIM_COST"): ("numeric", "Total encounter cost, including line items.", "", ""),
    ("encounters", "PAYER_COVERAGE"): ("numeric", "Amount covered by the payer.", "", ""),
    ("encounters", "REASONCODE"): ("string", "Targeted condition, when the encounter has one.", "SNOMED-CT", ""),
    ("encounters", "REASONDESCRIPTION"): ("string", "Display text for REASONCODE.", "", ""),
    ("imaging_studies", "Id"): ("uuid", "Study identifier. Not unique. One study can have several rows.", "", ""),
    ("imaging_studies", "DATE"): ("timestamp", "When the study was performed.", "", ""),
    ("imaging_studies", "PATIENT"): ("uuid", "Patient.", "", "FK patients.Id"),
    ("imaging_studies", "ENCOUNTER"): ("uuid", "Encounter.", "", "FK encounters.Id"),
    ("imaging_studies", "SERIES_UID"): ("string", "DICOM series identifier.", "DICOM UID", ""),
    ("imaging_studies", "BODYSITE_CODE"): ("string", "Body structure imaged.", "SNOMED-CT", ""),
    ("imaging_studies", "BODYSITE_DESCRIPTION"): ("string", "Display text for BODYSITE_CODE.", "", ""),
    ("imaging_studies", "MODALITY_CODE"): ("string", "Imaging method.", "DICOM-DCM", ""),
    ("imaging_studies", "MODALITY_DESCRIPTION"): ("string", "Display text for MODALITY_CODE.", "", ""),
    ("imaging_studies", "INSTANCE_UID"): ("string", "DICOM instance identifier.", "DICOM UID", ""),
    ("imaging_studies", "SOP_CODE"): ("string", "DICOM subject-object pair.", "DICOM-SOP", ""),
    ("imaging_studies", "SOP_DESCRIPTION"): ("string", "Display text for SOP_CODE.", "", ""),
    ("imaging_studies", "PROCEDURE_CODE"): ("string", "Procedure performed.", "SNOMED-CT", ""),
    ("immunizations", "DATE"): ("timestamp", "When the immunization was given.", "", ""),
    ("immunizations", "PATIENT"): ("uuid", "Patient. This table has no primary key of its own.", "", "FK patients.Id"),
    ("immunizations", "ENCOUNTER"): ("uuid", "Encounter.", "", "FK encounters.Id"),
    ("immunizations", "CODE"): ("string", "Vaccine code.", "CVX", ""),
    ("immunizations", "DESCRIPTION"): ("string", "Display text for CODE.", "", ""),
    ("immunizations", "BASE_COST"): ("numeric", "Line cost. The public wiki calls this column Cost. This export names it BASE_COST.", "", ""),
    ("medications", "START"): ("timestamp", "When the medication course was prescribed. This is not an administration time.", "", ""),
    ("medications", "STOP"): ("timestamp", "When the course ended. Blank when it is still open.", "", ""),
    ("medications", "PATIENT"): ("uuid", "Patient. This table has no primary key of its own.", "", "FK patients.Id"),
    ("medications", "PAYER"): ("uuid", "Payer for the prescription.", "", "FK payers.Id"),
    ("medications", "ENCOUNTER"): ("uuid", "Encounter at which the medication was prescribed.", "", "FK encounters.Id"),
    ("medications", "CODE"): ("string", "Medication code.", "RxNorm", ""),
    ("medications", "DESCRIPTION"): ("string", "Display text for CODE.", "", ""),
    ("medications", "BASE_COST"): ("numeric", "Line cost of one dispense.", "", ""),
    ("medications", "PAYER_COVERAGE"): ("numeric", "Amount covered by the payer.", "", ""),
    ("medications", "DISPENSES"): ("numeric", "Number of fills recorded on the course. A count, not a dated fill event.", "", ""),
    ("medications", "TOTALCOST"): ("numeric", "Cost across the recorded dispenses.", "", ""),
    ("medications", "REASONCODE"): ("string", "Why the medication was prescribed, when present.", "SNOMED-CT", ""),
    ("medications", "REASONDESCRIPTION"): ("string", "Display text for REASONCODE.", "", ""),
    ("observations", "DATE"): ("timestamp", "When the observation was recorded, UTC.", "", ""),
    ("observations", "PATIENT"): ("uuid", "Patient. This table has no primary key of its own.", "", "FK patients.Id"),
    ("observations", "ENCOUNTER"): ("uuid", "Encounter. The public wiki allows this to be blank. Treat a blank as a data-quality finding, not as a dropped row, until Process decides.", "", "FK encounters.Id"),
    ("observations", "CATEGORY"): ("string", "Observation category, such as vital-signs or laboratory.", "", ""),
    ("observations", "CODE"): ("string", "Observation or lab code.", "LOINC", ""),
    ("observations", "DESCRIPTION"): ("string", "Display text for CODE.", "", ""),
    ("observations", "VALUE"): ("string", "Result. Numeric when TYPE is numeric. Can be long text for questionnaires.", "", ""),
    ("observations", "UNITS"): ("string", "Unit of VALUE. Blank for some text results.", "", ""),
    ("observations", "TYPE"): ("string", "numeric or text. Use this before casting VALUE.", "", ""),
    ("organizations", "Id"): ("uuid", "Organization identifier. Clinic grain for this study.", "", "PK"),
    ("organizations", "NAME"): ("string", "Organization name.", "", ""),
    ("organizations", "ADDRESS"): ("string", "Street address.", "", ""),
    ("organizations", "CITY"): ("string", "City.", "", ""),
    ("organizations", "STATE"): ("string", "State abbreviation.", "", ""),
    ("organizations", "ZIP"): ("string", "ZIP code.", "", ""),
    ("organizations", "LAT"): ("numeric", "Latitude.", "", ""),
    ("organizations", "LON"): ("numeric", "Longitude.", "", ""),
    ("organizations", "PHONE"): ("string", "Phone. Sometimes more than one number in the field.", "", ""),
    ("organizations", "REVENUE"): ("numeric", "Simulated lifetime revenue.", "", ""),
    ("organizations", "UTILIZATION"): ("numeric", "Encounter count at this organization across the simulation.", "", ""),
    ("organizations", "NPI"): ("string", "National Provider Identifier for the organization. Present in this export. The wiki page checked on 14 October 2026 does not list it.", "NPI", ""),
    ("patients", "Id"): ("uuid", "Patient identifier.", "", "PK"),
    ("patients", "BIRTHDATE"): ("date", "Date of birth.", "", ""),
    ("patients", "DEATHDATE"): ("date", "Date of death. Blank when the patient is alive at the end of the simulation.", "", ""),
    ("patients", "SSN"): ("string", "Synthetic Social Security number. Not a real identifier. Still treated as a direct identifier and kept out of git.", "", ""),
    ("patients", "DRIVERS"): ("string", "Synthetic driver license number.", "", ""),
    ("patients", "PASSPORT"): ("string", "Synthetic passport number.", "", ""),
    ("patients", "PREFIX"): ("string", "Name prefix.", "", ""),
    ("patients", "FIRST"): ("string", "Given name. Synthetic, with a generator suffix.", "", ""),
    ("patients", "MIDDLE"): ("string", "Middle name.", "", ""),
    ("patients", "LAST"): ("string", "Family name. Synthetic.", "", ""),
    ("patients", "SUFFIX"): ("string", "Name suffix.", "", ""),
    ("patients", "MAIDEN"): ("string", "Maiden name.", "", ""),
    ("patients", "MARITAL"): ("string", "M married or S single.", "", ""),
    ("patients", "RACE"): ("string", "Race description generated by Synthea. Not an OMB or CDC code.", "", ""),
    ("patients", "ETHNICITY"): ("string", "Ethnicity description generated by Synthea. Not an OMB or CDC code.", "", ""),
    ("patients", "GENDER"): ("string", "M or F.", "", ""),
    ("patients", "BIRTHPLACE"): ("string", "Town of birth.", "", ""),
    ("patients", "ADDRESS"): ("string", "Street address. Synthetic direct identifier.", "", ""),
    ("patients", "CITY"): ("string", "City.", "", ""),
    ("patients", "STATE"): ("string", "State.", "", ""),
    ("patients", "COUNTY"): ("string", "County.", "", ""),
    ("patients", "FIPS"): ("string", "County FIPS code.", "FIPS", ""),
    ("patients", "ZIP"): ("string", "ZIP code.", "", ""),
    ("patients", "LAT"): ("numeric", "Latitude of the address.", "", ""),
    ("patients", "LON"): ("numeric", "Longitude of the address.", "", ""),
    ("patients", "HEALTHCARE_EXPENSES"): ("numeric", "Lifetime amount paid by the patient in the simulation.", "", ""),
    ("patients", "HEALTHCARE_COVERAGE"): ("numeric", "Lifetime amount paid by payers in the simulation.", "", ""),
    ("patients", "INCOME"): ("numeric", "Annual income in the simulation.", "", ""),
    ("payer_transitions", "PATIENT"): ("uuid", "Patient. This table has no primary key of its own.", "", "FK patients.Id"),
    ("payer_transitions", "MEMBERID"): ("uuid", "Member id. Often blank in this export.", "", ""),
    ("payer_transitions", "START_DATE"): ("timestamp", "Coverage start. The wiki still calls this a year column named START_YEAR. This export stores a timestamp.", "", ""),
    ("payer_transitions", "END_DATE"): ("timestamp", "Coverage end. The wiki still calls this END_YEAR. This export stores a timestamp, and none of the values are blank.", "", ""),
    ("payer_transitions", "PAYER"): ("uuid", "Payer for the span.", "", "FK payers.Id"),
    ("payer_transitions", "SECONDARY_PAYER"): ("uuid", "Secondary payer, when present.", "", "FK payers.Id"),
    ("payer_transitions", "PLAN_OWNERSHIP"): ("string", "Who holds the policy: Self, Spouse, Guardian, or blank. Not an institutional-status flag.", "", ""),
    ("payer_transitions", "OWNER_NAME"): ("string", "Name of the policy holder. Synthetic direct identifier when filled.", "", ""),
    ("payers", "Id"): ("uuid", "Payer identifier.", "", "PK"),
    ("payers", "NAME"): ("string", "Payer name, including Medicare, Medicaid, Dual Eligible, commercial names, and NO_INSURANCE.", "", ""),
    ("payers", "OWNERSHIP"): ("string", "GOVERNMENT, PRIVATE, or NO_INSURANCE. This is the organization, not the member's plan type.", "", ""),
    ("payers", "ADDRESS"): ("string", "Street address. Blank for every payer in this export.", "", ""),
    ("payers", "CITY"): ("string", "City. Blank in this export.", "", ""),
    ("payers", "STATE_HEADQUARTERED"): ("string", "State. Blank in this export.", "", ""),
    ("payers", "ZIP"): ("string", "ZIP code. Blank in this export.", "", ""),
    ("payers", "PHONE"): ("string", "Phone. Blank in this export.", "", ""),
    ("payers", "AMOUNT_COVERED"): ("numeric", "Simulated amount paid to organizations.", "", ""),
    ("payers", "AMOUNT_UNCOVERED"): ("numeric", "Simulated amount left to patients.", "", ""),
    ("payers", "REVENUE"): ("numeric", "Simulated payer revenue.", "", ""),
    ("payers", "COVERED_ENCOUNTERS"): ("numeric", "Encounters this payer paid for.", "", ""),
    ("payers", "UNCOVERED_ENCOUNTERS"): ("numeric", "Encounters left to the patient.", "", ""),
    ("payers", "COVERED_MEDICATIONS"): ("numeric", "Medications this payer paid for.", "", ""),
    ("payers", "UNCOVERED_MEDICATIONS"): ("numeric", "Medications left to the patient.", "", ""),
    ("payers", "COVERED_PROCEDURES"): ("numeric", "Procedures this payer paid for.", "", ""),
    ("payers", "UNCOVERED_PROCEDURES"): ("numeric", "Procedures left to the patient.", "", ""),
    ("payers", "COVERED_IMMUNIZATIONS"): ("numeric", "Immunizations this payer paid for.", "", ""),
    ("payers", "UNCOVERED_IMMUNIZATIONS"): ("numeric", "Immunizations left to the patient.", "", ""),
    ("payers", "UNIQUE_CUSTOMERS"): ("numeric", "Distinct patients enrolled during the simulation.", "", ""),
    ("payers", "QOLS_AVG"): ("numeric", "Average quality-of-life score among enrolled patients.", "", ""),
    ("payers", "MEMBER_MONTHS"): ("numeric", "Member months in the simulation.", "", ""),
    ("procedures", "START"): ("timestamp", "When the procedure started.", "", ""),
    ("procedures", "STOP"): ("timestamp", "When the procedure ended.", "", ""),
    ("procedures", "PATIENT"): ("uuid", "Patient. This table has no primary key of its own.", "", "FK patients.Id"),
    ("procedures", "ENCOUNTER"): ("uuid", "Encounter.", "", "FK encounters.Id"),
    ("procedures", "SYSTEM"): ("string", "Terminology of CODE. Observed value in this export is SNOMED-CT.", "SNOMED-CT", ""),
    ("procedures", "CODE"): ("string", "Procedure code.", "SNOMED-CT", ""),
    ("procedures", "DESCRIPTION"): ("string", "Display text for CODE.", "", ""),
    ("procedures", "BASE_COST"): ("numeric", "Line cost.", "", ""),
    ("procedures", "REASONCODE"): ("string", "Why the procedure was done, when present.", "SNOMED-CT", ""),
    ("procedures", "REASONDESCRIPTION"): ("string", "Display text for REASONCODE.", "", ""),
    ("providers", "Id"): ("uuid", "Clinician identifier.", "", "PK"),
    ("providers", "ORGANIZATION"): ("uuid", "Organization that employs the clinician.", "", "FK organizations.Id"),
    ("providers", "NAME"): ("string", "Clinician name. Synthetic.", "", ""),
    ("providers", "GENDER"): ("string", "M or F.", "", ""),
    ("providers", "SPECIALITY"): ("string", "Specialty text. The generator spells the column SPECIALITY.", "", ""),
    ("providers", "ADDRESS"): ("string", "Street address.", "", ""),
    ("providers", "CITY"): ("string", "City.", "", ""),
    ("providers", "STATE"): ("string", "State.", "", ""),
    ("providers", "ZIP"): ("string", "ZIP code.", "", ""),
    ("providers", "LAT"): ("numeric", "Latitude.", "", ""),
    ("providers", "LON"): ("numeric", "Longitude.", "", ""),
    ("providers", "ENCOUNTERS"): ("numeric", "Encounter count for this clinician across the simulation.", "", ""),
    ("providers", "PROCEDURES"): ("numeric", "Procedure count for this clinician across the simulation.", "", ""),
    ("providers", "NPI"): ("string", "National Provider Identifier. Present in this export. The wiki page checked on 14 October 2026 does not list it.", "NPI", ""),
    ("supplies", "DATE"): ("date", "Date the supply was used.", "", ""),
    ("supplies", "PATIENT"): ("uuid", "Patient. This table has no primary key of its own.", "", "FK patients.Id"),
    ("supplies", "ENCOUNTER"): ("uuid", "Encounter.", "", "FK encounters.Id"),
    ("supplies", "CODE"): ("string", "Supply type.", "SNOMED-CT", ""),
    ("supplies", "DESCRIPTION"): ("string", "Display text for CODE.", "", ""),
    ("supplies", "QUANTITY"): ("numeric", "Quantity used.", "", ""),
}


def csv_dir() -> Path:
    if RAW.exists():
        return RAW
    if FALLBACK.exists():
        return FALLBACK
    print(f"Missing {RAW} and {FALLBACK}.", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    folder = csv_dir()
    rows = []
    missing = []
    seen = set()
    for path in sorted(folder.glob("*.csv")):
        table = path.stem
        with path.open(newline="") as handle:
            header = next(csv.reader(handle))
        for column in header:
            key = (table, column)
            seen.add(key)
            if key not in FIELDS:
                missing.append(f"{table}.{column}")
                continue
            kind, meaning, system, key_role = FIELDS[key]
            rows.append({
                "table_name": table,
                "column_name": column,
                "data_type": kind,
                "meaning": meaning,
                "code_system": system,
                "key": key_role,
            })
    extra = sorted(f"{table}.{column}" for (table, column) in FIELDS if (table, column) not in seen)
    if missing or extra:
        print("Dictionary does not match the files.", file=sys.stderr)
        for name in missing:
            print(f"  in file, not in dictionary: {name}", file=sys.stderr)
        for name in extra:
            print(f"  in dictionary, not in file: {name}", file=sys.stderr)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["table_name", "column_name", "data_type", "meaning", "code_system", "key"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} columns to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
