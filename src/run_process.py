"""Run the Process SQL, then write the cleaning log and the two figures.

The SQL in sql/process_staging.sql builds staging and analytic. This script
checks referential integrity, records every decision, and draws the missingness
heatmap and the patient-cohort waterfall.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "warehouse" / "riverbend.duckdb"
SQL = ROOT / "sql" / "process_staging.sql"
LOG_CSV = ROOT / "outputs" / "cleaning_log.csv"
NULL_CSV = ROOT / "outputs" / "null_rates.csv"
LOG_MD = ROOT / "docs" / "cleaning-log.md"
FIG_DIR = ROOT / "outputs" / "figures"

STUDY_TABLES = (
    "patients",
    "organizations",
    "providers",
    "payers",
    "encounters",
    "conditions",
    "observations",
    "medications",
    "procedures",
    "payer_transitions",
)

ORPHAN_CHECKS = {
    "encounters.PATIENT": "SELECT count(*) FROM encounters e LEFT JOIN patients p ON e.PATIENT = p.Id WHERE p.Id IS NULL",
    "encounters.ORGANIZATION": "SELECT count(*) FROM encounters e LEFT JOIN organizations o ON e.ORGANIZATION = o.Id WHERE o.Id IS NULL",
    "encounters.PROVIDER": "SELECT count(*) FROM encounters e LEFT JOIN providers pr ON e.PROVIDER = pr.Id WHERE pr.Id IS NULL",
    "encounters.PAYER": "SELECT count(*) FROM encounters e LEFT JOIN payers py ON e.PAYER = py.Id WHERE py.Id IS NULL",
    "conditions.PATIENT": "SELECT count(*) FROM conditions c LEFT JOIN patients p ON c.PATIENT = p.Id WHERE p.Id IS NULL",
    "conditions.ENCOUNTER": "SELECT count(*) FROM conditions c LEFT JOIN encounters e ON c.ENCOUNTER = e.Id WHERE e.Id IS NULL",
    "observations.PATIENT": "SELECT count(*) FROM observations o LEFT JOIN patients p ON o.PATIENT = p.Id WHERE p.Id IS NULL",
    "observations.ENCOUNTER when populated": "SELECT count(*) FROM observations o LEFT JOIN encounters e ON o.ENCOUNTER = e.Id WHERE o.ENCOUNTER IS NOT NULL AND o.ENCOUNTER <> '' AND e.Id IS NULL",
    "medications.PATIENT": "SELECT count(*) FROM medications m LEFT JOIN patients p ON m.PATIENT = p.Id WHERE p.Id IS NULL",
    "medications.ENCOUNTER": "SELECT count(*) FROM medications m LEFT JOIN encounters e ON m.ENCOUNTER = e.Id WHERE e.Id IS NULL",
    "procedures.PATIENT": "SELECT count(*) FROM procedures r LEFT JOIN patients p ON r.PATIENT = p.Id WHERE p.Id IS NULL",
    "procedures.ENCOUNTER": "SELECT count(*) FROM procedures r LEFT JOIN encounters e ON r.ENCOUNTER = e.Id WHERE e.Id IS NULL",
    "payer_transitions.PATIENT": "SELECT count(*) FROM payer_transitions t LEFT JOIN patients p ON t.PATIENT = p.Id WHERE p.Id IS NULL",
    "payer_transitions.PAYER": "SELECT count(*) FROM payer_transitions t LEFT JOIN payers py ON t.PAYER = py.Id WHERE py.Id IS NULL",
    "providers.ORGANIZATION": "SELECT count(*) FROM providers pr LEFT JOIN organizations o ON pr.ORGANIZATION = o.Id WHERE o.Id IS NULL",
}


def split_sql(text: str) -> list[str]:
    statements = []
    for chunk in text.split(";"):
        lines = [line for line in chunk.splitlines() if not line.strip().startswith("--")]
        statement = "\n".join(lines).strip()
        if statement:
            statements.append(statement)
    return statements


def one(connection, sql: str):
    return connection.execute(sql).fetchone()[0]


def null_rates(connection) -> list[dict]:
    rows = []
    for table in STUDY_TABLES:
        columns = [row[0] for row in connection.execute(f"DESCRIBE {table}").fetchall()]
        total = one(connection, f"SELECT count(*) FROM {table}")
        for column in columns:
            empty = one(
                connection,
                f"""
                SELECT count(*) FROM {table}
                WHERE {column} IS NULL OR CAST({column} AS VARCHAR) = ''
                """,
            )
            rows.append({
                "table_name": table,
                "column_name": column,
                "rows": total,
                "empty_rows": empty,
                "empty_pct": round(100 * empty / total, 1) if total else 0,
            })
    return rows


def write_log(connection) -> list[dict]:
    raw_patients = one(connection, "SELECT count(*) FROM patients")
    died_before = one(connection, "SELECT count(*) FROM staging.patients WHERE died_before_period")
    died_during = one(connection, "SELECT count(*) FROM staging.patients WHERE died_during_period")
    cohort = one(connection, "SELECT count(*) FROM analytic.patient_period")
    blank_encounter = one(connection, "SELECT count(*) FROM staging.observations WHERE encounter_missing")
    blank_measure = one(
        connection,
        """
        SELECT count(*) FROM staging.observations
        WHERE encounter_missing AND CODE IN ('8480-6', '8462-4', '4548-4')
        """,
    )
    after_death_enc = one(connection, "SELECT count(*) FROM staging.encounters WHERE after_death")
    after_death_obs = one(connection, "SELECT count(*) FROM staging.observations WHERE after_death")
    outside_enc = one(connection, "SELECT count(*) FROM staging.encounters WHERE outside_window")
    outside_obs = one(connection, "SELECT count(*) FROM staging.observations WHERE outside_window")
    negative_meds = one(connection, "SELECT count(*) FROM staging.medications WHERE negative_duration")
    low_sys = one(connection, "SELECT count(*) FROM staging.observations WHERE CODE = '8480-6' AND value_numeric < 70")
    low_dia = one(connection, "SELECT count(*) FROM staging.observations WHERE CODE = '8462-4' AND value_numeric < 40")
    low_a1c = one(connection, "SELECT count(*) FROM staging.observations WHERE CODE = '4548-4' AND value_numeric < 3")
    inverted = one(
        connection,
        """
        SELECT count(*) FROM staging.observations
        WHERE CODE IN ('8480-6', '8462-4') AND implausible_value
          AND value_numeric BETWEEN 40 AND 250
          AND NOT (CODE = '8480-6' AND (value_numeric < 70 OR value_numeric > 250))
          AND NOT (CODE = '8462-4' AND (value_numeric < 40 OR value_numeric > 150))
        """,
    )
    multi_obs = one(connection, "SELECT count(*) FROM analytic.patient_period WHERE n_systolic > 1")
    multi_org = one(connection, "SELECT count(*) FROM analytic.patient_period WHERE n_organizations > 1")
    rows = [
        {
            "issue": "Duplicate primary keys on patients, organizations, providers, payers, and encounters",
            "how_found": "count(*) compared with count(DISTINCT id) in sql/process_staging.sql inputs",
            "rows_affected": 0,
            "decision": "Retain every row",
            "reason": "No duplicate identifiers. Encounter joins cannot multiply a patient through a repeated encounter id.",
        },
        {
            "issue": "Foreign key present but unmatched",
            "how_found": "LEFT JOIN anti-joins in src/run_process.py",
            "rows_affected": 0,
            "decision": "Retain every row",
            "reason": "Every populated patient, encounter, organization, provider, and payer key finds its parent.",
        },
        {
            "issue": "Death date before birth date",
            "how_found": "staging.patients.death_before_birth",
            "rows_affected": 0,
            "decision": "Retain every row",
            "reason": "No patient has a death date earlier than the birth date.",
        },
        {
            "issue": "Patient died before the measurement period",
            "how_found": "staging.patients.died_before_period, death date before 2026-01-01",
            "rows_affected": died_before,
            "decision": "Exclude from analytic.patient_period",
            "reason": "The study window is 1 January 2026 through 13 October 2026. A person who died before it is not in the cohort. The row stays in staging.patients.",
        },
        {
            "issue": "Patient died during the measurement period",
            "how_found": "staging.patients.died_during_period",
            "rows_affected": died_during,
            "decision": "Keep in analytic.patient_period",
            "reason": "Death during the window is a measure-specific exclusion. Analyze applies it. Process only marks the row.",
        },
        {
            "issue": "Encounter starts after the death date",
            "how_found": "staging.encounters.after_death, UTC start date after DEATHDATE",
            "rows_affected": after_death_enc,
            "decision": "Flag and keep. Exclude from organization attribution and from analytic.observation_eligible",
            "reason": "The gap is 1 to 14 days. The row may be a generator artifact. Deleting it would hide the defect.",
        },
        {
            "issue": "Observation dated after the death date",
            "how_found": "staging.observations.after_death",
            "rows_affected": after_death_obs,
            "decision": "Flag and keep. Exclude from analytic.observation_eligible",
            "reason": "Same defect as encounters after death. The value remains available for audit.",
        },
        {
            "issue": "Observation has no encounter id",
            "how_found": "staging.observations.encounter_missing",
            "rows_affected": blank_encounter,
            "decision": "Flag and keep. Exclude from analytic.observation_eligible",
            "reason": f"Category is blank on the same rows. Blood pressure and A1c codes account for {blank_measure} of them, so the two study measures do not lose a result here.",
        },
        {
            "issue": "Medication stop timestamp is before the start",
            "how_found": "staging.medications.negative_duration, 48 to 144 hours",
            "rows_affected": negative_meds,
            "decision": "Flag and keep. Do not use STOP as the course end on these rows",
            "reason": "A negative duration is not a real course length. The start timestamp is still a prescription date.",
        },
        {
            "issue": "Systolic value outside 70 to 250 mmHg",
            "how_found": "staging.observations, LOINC 8480-6",
            "rows_affected": low_sys,
            "decision": "Flag implausible_value and exclude from analytic.observation_eligible",
            "reason": "Study plausibility bound, not a HEDIS rule. The lowest value in the file is 40.5.",
        },
        {
            "issue": "Diastolic value outside 40 to 150 mmHg",
            "how_found": "staging.observations, LOINC 8462-4",
            "rows_affected": low_dia,
            "decision": "Flag implausible_value and exclude from analytic.observation_eligible",
            "reason": "Study plausibility bound. The lowest value in the file is 18.",
        },
        {
            "issue": "Systolic lower than diastolic at the same timestamp",
            "how_found": "Pair of LOINC 8480-6 and 8462-4 grouped by patient and timestamp",
            "rows_affected": inverted,
            "decision": "Flag both readings implausible and exclude them from analytic.observation_eligible",
            "reason": "An inverted pair cannot be a blood pressure. Rows already outside the numeric bounds are counted in the two rows above.",
        },
        {
            "issue": "A1c below 3%",
            "how_found": "staging.observations, LOINC 4548-4",
            "rows_affected": low_a1c,
            "decision": "Flag implausible_value and exclude from analytic.observation_eligible",
            "reason": "Study plausibility bound. No A1c in the file is above 20%. Values under 3% are not used as glycemic results.",
        },
        {
            "issue": "Clinical timestamp after the generator reference date",
            "how_found": "UTC date after 2026-10-13",
            "rows_affected": outside_enc + outside_obs,
            "decision": "Flag outside_window and exclude from the measurement period",
            "reason": f"Encounters dated after 13 October 2026: {outside_enc}. Observations dated after that day: {outside_obs}. The reference date remains the end of the window.",
        },
        {
            "issue": "Several blood pressure readings for one patient in the window",
            "how_found": "analytic.patient_period.n_systolic",
            "rows_affected": multi_obs,
            "decision": "Keep every reading in staging. Do not collapse them in Process",
            "reason": "The later measure query selects the most recent eligible reading with a window function. Collapsing now would hide the choice.",
        },
        {
            "issue": "Patient seen at more than one organization in the window",
            "how_found": "analytic.patient_period.n_organizations",
            "rows_affected": multi_org,
            "decision": "Attribute the patient to the organization with the most in-window encounters, breaking ties with the latest encounter",
            "reason": "The file is a statewide set of organizations, not a single clinic panel. The rule is explicit so a later clinic rate is not an accident of join order.",
        },
    ]
    if raw_patients - died_before != cohort:
        print(
            f"Cohort arithmetic failed: {raw_patients} - {died_before} != {cohort}",
            file=sys.stderr,
        )
        sys.exit(1)
    LOG_CSV.parent.mkdir(parents=True, exist_ok=True)
    with LOG_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["issue", "how_found", "rows_affected", "decision", "reason"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    return rows, raw_patients, died_before, cohort


def write_markdown(rows, raw_patients, died_before, cohort) -> None:
    lines = [
        "# Cleaning log",
        "",
        "**Portfolio note.** Riverbend Community Health Network is fictional. The rows are synthetic Synthea patients. This log covers the study warehouse only.",
        "",
        "**Measurement period.** 1 January 2026 through 13 October 2026. The end date is the Synthea reference date. Staging keeps the full history. `analytic.patient_period` is one row per patient who had not died before the period opened.",
        "",
        "**What was not done.** No raw CSV was edited. No missing death date, name part, reason code, or payer address was imputed. Those nulls are real properties of the export. Official HEDIS value sets were not applied. Plausibility bounds below are study rules.",
        "",
        "**Several observations.** Staging keeps every blood pressure and A1c. The analytic patient row stores how many eligible readings the patient has. The measure phase selects the most recent eligible reading. It does not average them.",
        "",
        f"**Cohort.** {raw_patients} patients in the export, {died_before} removed from the analytic table because they died before 1 January 2026, {cohort} patients in `analytic.patient_period`.",
        "",
        "| Issue | How it was found | Rows affected | Decision | Reason |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['issue']} | {row['how_found']} | {row['rows_affected']} | {row['decision']} | {row['reason']} |"
        )
    lines.extend([
        "",
        "Figures: `outputs/figures/missing_data_heatmap.png` and `outputs/figures/cleaning_waterfall.png`. Column-level null rates are in `outputs/null_rates.csv`. The SQL is `sql/process_staging.sql`.",
        "",
    ])
    LOG_MD.write_text("\n".join(lines))


def draw(null_rows, raw_patients, died_before, cohort) -> None:
    import matplotlib.pyplot as plt

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    present = [row for row in null_rows if row["empty_pct"] > 0]
    present.sort(key=lambda row: (row["table_name"], -row["empty_pct"]))
    labels = [f"{row['table_name']}.{row['column_name']}" for row in present]
    values = [row["empty_pct"] for row in present]
    figure, axis = plt.subplots(figsize=(8, max(6, 0.28 * len(present))))
    image = axis.imshow([[value] for value in values], aspect="auto", cmap="YlOrRd", vmin=0, vmax=100)
    axis.set_yticks(range(len(labels)))
    axis.set_yticklabels(labels, fontsize=8)
    axis.set_xticks([0])
    axis.set_xticklabels(["Empty percent"])
    axis.set_title("Where fields are empty in the study tables")
    for index, value in enumerate(values):
        axis.text(0, index, f"{value:.1f}", ha="center", va="center", fontsize=7)
    figure.colorbar(image, ax=axis, fraction=0.03, pad=0.04)
    figure.tight_layout()
    figure.savefig(FIG_DIR / "missing_data_heatmap.png", dpi=150)
    plt.close(figure)

    steps = [
        ("Patients in the export", raw_patients),
        ("Duplicate identifiers", 0),
        ("Death before birth", 0),
        ("Died before 1 Jan 2026", -died_before),
        ("Analytic cohort", cohort),
    ]
    figure, axis = plt.subplots(figsize=(9, 5))
    cumulative = 0
    for index, (label, delta) in enumerate(steps):
        if index == 0 or index == len(steps) - 1:
            axis.bar(index, steps[index][1], color="#1f4e79")
            cumulative = steps[index][1]
        else:
            start = cumulative + delta if delta < 0 else cumulative
            axis.bar(index, abs(delta), bottom=start if delta < 0 else cumulative, color="#c2410c")
            cumulative = cumulative + delta
        shown = steps[index][1]
        axis.text(index, cumulative + 40, f"{shown:+d}" if index not in (0, len(steps) - 1) else str(shown), ha="center", fontsize=9)
    axis.set_xticks(range(len(steps)))
    axis.set_xticklabels([label for label, _ in steps], rotation=20, ha="right")
    axis.set_ylabel("Patients")
    axis.set_title("Patients kept for the measurement period")
    axis.set_ylim(0, raw_patients + 250)
    figure.tight_layout()
    figure.savefig(FIG_DIR / "cleaning_waterfall.png", dpi=150)
    plt.close(figure)


def main() -> int:
    if not DB.exists():
        print(f"Missing {DB}. Run src/load_study_warehouse.py first.", file=sys.stderr)
        return 1
    import duckdb

    connection = duckdb.connect(str(DB))
    for statement in split_sql(SQL.read_text()):
        connection.execute(statement)
    for name, sql in ORPHAN_CHECKS.items():
        found = one(connection, sql)
        if found:
            print(f"Referential integrity failed for {name}: {found}", file=sys.stderr)
            return 1
    rates = null_rates(connection)
    with NULL_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["table_name", "column_name", "rows", "empty_rows", "empty_pct"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rates)
    rows, raw_patients, died_before, cohort = write_log(connection)
    write_markdown(rows, raw_patients, died_before, cohort)
    draw(rates, raw_patients, died_before, cohort)
    print(f"analytic patients {cohort}")
    print(f"eligible observations {one(connection, 'SELECT count(*) FROM analytic.observation_eligible')}")
    connection.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
