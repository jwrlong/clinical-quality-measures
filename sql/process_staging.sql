-- Staging and the patient-period table for the Riverbend study.
-- Source tables are the study warehouse loaded from data_raw. This script
-- does not update those tables. Dates are converted to UTC before they are
-- compared with date-only birth and death fields.

DROP SCHEMA IF EXISTS staging CASCADE;
DROP SCHEMA IF EXISTS analytic CASCADE;
CREATE SCHEMA staging;
CREATE SCHEMA analytic;

CREATE TABLE staging.patients AS
SELECT
    *,
    coalesce(DEATHDATE IS NOT NULL AND DEATHDATE < BIRTHDATE, false) AS death_before_birth,
    coalesce(DEATHDATE IS NOT NULL AND DEATHDATE < DATE '2026-01-01', false) AS died_before_period,
    coalesce(DEATHDATE BETWEEN DATE '2026-01-01' AND DATE '2026-10-13', false) AS died_during_period
FROM patients;

CREATE TABLE staging.organizations AS
SELECT * FROM organizations;

CREATE TABLE staging.providers AS
SELECT * FROM providers;

CREATE TABLE staging.payers AS
SELECT * FROM payers;

CREATE TABLE staging.payer_transitions AS
SELECT
    *,
    CAST(timezone('UTC', START_DATE) AS TIMESTAMP) AS start_utc,
    CAST(timezone('UTC', END_DATE) AS TIMESTAMP) AS end_utc
FROM payer_transitions;

CREATE TABLE staging.encounters AS
SELECT
    e.*,
    CAST(timezone('UTC', e.START) AS TIMESTAMP) AS start_utc,
    CAST(timezone('UTC', e.STOP) AS TIMESTAMP) AS stop_utc,
    CAST(timezone('UTC', e.START) AS DATE) AS start_date,
    CAST(timezone('UTC', e.STOP) AS DATE) AS stop_date,
    p.DEATHDATE IS NOT NULL
        AND CAST(timezone('UTC', e.START) AS DATE) > p.DEATHDATE AS after_death,
    CAST(timezone('UTC', e.START) AS DATE) > DATE '2026-10-13' AS outside_window
FROM encounters e
JOIN staging.patients p ON e.PATIENT = p.Id;

CREATE TABLE staging.conditions AS
SELECT * FROM conditions;

CREATE TABLE staging.procedures AS
SELECT
    *,
    CAST(timezone('UTC', START) AS TIMESTAMP) AS start_utc,
    CAST(timezone('UTC', STOP) AS TIMESTAMP) AS stop_utc
FROM procedures;

CREATE TABLE staging.medications AS
SELECT
    *,
    CAST(timezone('UTC', START) AS TIMESTAMP) AS start_utc,
    CAST(timezone('UTC', STOP) AS TIMESTAMP) AS stop_utc,
    STOP IS NOT NULL AND timezone('UTC', STOP) < timezone('UTC', START) AS negative_duration
FROM medications;

CREATE TABLE staging.observations AS
WITH inverted AS (
    SELECT PATIENT, DATE
    FROM observations
    WHERE CODE IN ('8480-6', '8462-4')
    GROUP BY PATIENT, DATE
    HAVING max(CASE WHEN CODE = '8480-6' THEN TRY_CAST(VALUE AS DOUBLE) END)
         < max(CASE WHEN CODE = '8462-4' THEN TRY_CAST(VALUE AS DOUBLE) END)
)
SELECT
    o.*,
    TRY_CAST(o.VALUE AS DOUBLE) AS value_numeric,
    CAST(timezone('UTC', o.DATE) AS TIMESTAMP) AS observed_at_utc,
    CAST(timezone('UTC', o.DATE) AS DATE) AS observed_date,
    o.ENCOUNTER IS NULL OR o.ENCOUNTER = '' AS encounter_missing,
    p.DEATHDATE IS NOT NULL
        AND CAST(timezone('UTC', o.DATE) AS DATE) > p.DEATHDATE AS after_death,
    CAST(timezone('UTC', o.DATE) AS DATE) > DATE '2026-10-13' AS outside_window,
    (
        (o.CODE = '8480-6' AND TRY_CAST(o.VALUE AS DOUBLE) IS NOT NULL
            AND (TRY_CAST(o.VALUE AS DOUBLE) < 70 OR TRY_CAST(o.VALUE AS DOUBLE) > 250))
        OR (o.CODE = '8462-4' AND TRY_CAST(o.VALUE AS DOUBLE) IS NOT NULL
            AND (TRY_CAST(o.VALUE AS DOUBLE) < 40 OR TRY_CAST(o.VALUE AS DOUBLE) > 150))
        OR (o.CODE = '4548-4' AND TRY_CAST(o.VALUE AS DOUBLE) IS NOT NULL
            AND (TRY_CAST(o.VALUE AS DOUBLE) < 3 OR TRY_CAST(o.VALUE AS DOUBLE) > 20))
        OR (o.CODE IN ('8480-6', '8462-4') AND i.PATIENT IS NOT NULL)
    ) AS implausible_value
FROM observations o
JOIN staging.patients p ON o.PATIENT = p.Id
LEFT JOIN inverted i ON o.PATIENT = i.PATIENT AND o.DATE = i.DATE;

-- Facts eligible for a later measure. Staging still holds the flagged rows.
CREATE TABLE analytic.observation_eligible AS
SELECT *
FROM staging.observations
WHERE NOT encounter_missing
  AND NOT after_death
  AND NOT outside_window
  AND NOT implausible_value
  AND observed_date BETWEEN DATE '2026-01-01' AND DATE '2026-10-13';

CREATE TABLE analytic.patient_period AS
WITH cohort AS (
    SELECT *
    FROM staging.patients
    WHERE NOT died_before_period
),
enc AS (
    SELECT PATIENT, ORGANIZATION, count(*) AS n_enc, max(start_utc) AS last_start
    FROM staging.encounters
    WHERE start_date BETWEEN DATE '2026-01-01' AND DATE '2026-10-13'
      AND NOT after_death
      AND NOT outside_window
    GROUP BY PATIENT, ORGANIZATION
),
ranked AS (
    SELECT
        PATIENT,
        ORGANIZATION,
        row_number() OVER (
            PARTITION BY PATIENT
            ORDER BY n_enc DESC, last_start DESC
        ) AS rn
    FROM enc
),
enc_totals AS (
    SELECT PATIENT, sum(n_enc) AS n_encounters, count(*) AS n_organizations
    FROM enc
    GROUP BY PATIENT
),
obs AS (
    SELECT
        PATIENT,
        count(*) FILTER (WHERE CODE = '8480-6') AS n_systolic,
        count(*) FILTER (WHERE CODE = '8462-4') AS n_diastolic,
        count(*) FILTER (WHERE CODE = '4548-4') AS n_a1c
    FROM analytic.observation_eligible
    GROUP BY PATIENT
)
SELECT
    c.Id AS patient_id,
    c.BIRTHDATE AS birth_date,
    c.DEATHDATE AS death_date,
    c.GENDER AS gender,
    c.RACE AS race,
    c.ETHNICITY AS ethnicity,
    CASE
        WHEN (month(DATE '2026-10-13'), day(DATE '2026-10-13')) < (month(c.BIRTHDATE), day(c.BIRTHDATE))
        THEN date_diff('year', c.BIRTHDATE, DATE '2026-10-13') - 1
        ELSE date_diff('year', c.BIRTHDATE, DATE '2026-10-13')
    END AS age_on_2026_10_13,
    CASE
        WHEN (month(DATE '2026-12-31'), day(DATE '2026-12-31')) < (month(c.BIRTHDATE), day(c.BIRTHDATE))
        THEN date_diff('year', c.BIRTHDATE, DATE '2026-12-31') - 1
        ELSE date_diff('year', c.BIRTHDATE, DATE '2026-12-31')
    END AS age_on_2026_12_31,
    c.died_during_period,
    r.ORGANIZATION AS organization_id,
    coalesce(t.n_encounters, 0) AS n_encounters,
    coalesce(t.n_organizations, 0) AS n_organizations,
    coalesce(o.n_systolic, 0) AS n_systolic,
    coalesce(o.n_diastolic, 0) AS n_diastolic,
    coalesce(o.n_a1c, 0) AS n_a1c
FROM cohort c
LEFT JOIN ranked r ON c.Id = r.PATIENT AND r.rn = 1
LEFT JOIN enc_totals t ON c.Id = t.PATIENT
LEFT JOIN obs o ON c.Id = o.PATIENT;
