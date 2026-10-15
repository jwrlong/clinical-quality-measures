-- Study measures for Riverbend. Not an official HEDIS calculation.
-- Condition codes are cast to varchar because DuckDB loaded SNOMED codes as integers.

DROP TABLE IF EXISTS analytic.bp_person;
DROP TABLE IF EXISTS analytic.gsd_person;

CREATE TABLE analytic.bp_person AS
WITH htn AS (
    SELECT
        PATIENT,
        min(START) AS onset,
        bool_or(STOP IS NULL OR STOP >= DATE '2025-01-01') AS overlaps_window
    FROM staging.conditions
    WHERE cast(CODE AS VARCHAR) = '59621000'
    GROUP BY PATIENT
),
hospice AS (
    SELECT DISTINCT PATIENT
    FROM staging.encounters
    WHERE ENCOUNTERCLASS = 'hospice'
      AND start_date BETWEEN DATE '2026-01-01' AND DATE '2026-10-13'
      AND NOT after_death
),
readings AS (
    SELECT
        o.PATIENT,
        o.observed_date,
        min(CASE WHEN o.CODE = '8480-6' THEN o.value_numeric END) AS systolic,
        min(CASE WHEN o.CODE = '8462-4' THEN o.value_numeric END) AS diastolic
    FROM analytic.observation_eligible o
    JOIN staging.encounters e ON o.ENCOUNTER = e.Id
    WHERE o.CODE IN ('8480-6', '8462-4')
      AND e.ENCOUNTERCLASS IN ('ambulatory', 'wellness', 'outpatient', 'virtual', 'urgentcare')
    GROUP BY o.PATIENT, o.observed_date
    HAVING min(CASE WHEN o.CODE = '8480-6' THEN o.value_numeric END) IS NOT NULL
       AND min(CASE WHEN o.CODE = '8462-4' THEN o.value_numeric END) IS NOT NULL
),
latest AS (
    SELECT
        r.PATIENT,
        r.observed_date,
        r.systolic,
        r.diastolic,
        row_number() OVER (PARTITION BY r.PATIENT ORDER BY r.observed_date DESC) AS rn
    FROM readings r
    JOIN htn h ON r.PATIENT = h.PATIENT
    WHERE r.observed_date >= h.onset
      AND r.observed_date BETWEEN DATE '2026-01-01' AND DATE '2026-10-13'
)
SELECT
    p.patient_id,
    p.organization_id,
    p.age_on_2026_12_31 AS age,
    p.age_on_2026_10_13 AS age_at_extract_end,
    p.gender,
    p.race,
    p.ethnicity,
    p.age_on_2026_12_31 BETWEEN 18 AND 85 AS age_ok,
    h.PATIENT IS NOT NULL AND h.onset <= DATE '2026-06-30' AND h.overlaps_window AS htn_active,
    h.PATIENT IS NOT NULL AND h.onset BETWEEN DATE '2025-01-01' AND DATE '2026-06-30' AS htn_onset_in_window,
    p.died_during_period,
    hospice.PATIENT IS NOT NULL AS hospice,
    b.observed_date AS bp_date,
    b.systolic,
    b.diastolic,
    b.PATIENT IS NOT NULL AS has_bp,
    b.PATIENT IS NOT NULL AND b.systolic < 140 AND b.diastolic < 90 AS controlled
FROM analytic.patient_period p
LEFT JOIN htn h ON p.patient_id = h.PATIENT
LEFT JOIN hospice ON p.patient_id = hospice.PATIENT
LEFT JOIN latest b ON p.patient_id = b.PATIENT AND b.rn = 1;

CREATE TABLE analytic.gsd_person AS
WITH dm AS (
    SELECT
        PATIENT,
        min(START) AS onset,
        bool_or(STOP IS NULL OR STOP >= DATE '2025-01-01') AS overlaps_window
    FROM staging.conditions
    WHERE cast(CODE AS VARCHAR) = '44054006'
    GROUP BY PATIENT
),
hospice AS (
    SELECT DISTINCT PATIENT
    FROM staging.encounters
    WHERE ENCOUNTERCLASS = 'hospice'
      AND start_date BETWEEN DATE '2026-01-01' AND DATE '2026-10-13'
      AND NOT after_death
),
results AS (
    SELECT
        PATIENT,
        observed_date,
        min(value_numeric) AS a1c
    FROM analytic.observation_eligible
    WHERE CODE = '4548-4'
      AND observed_date BETWEEN DATE '2026-01-01' AND DATE '2026-10-13'
    GROUP BY PATIENT, observed_date
),
latest AS (
    SELECT
        PATIENT,
        observed_date,
        a1c,
        row_number() OVER (PARTITION BY PATIENT ORDER BY observed_date DESC) AS rn
    FROM results
)
SELECT
    p.patient_id,
    p.organization_id,
    p.age_on_2026_12_31 AS age,
    p.gender,
    p.race,
    p.ethnicity,
    p.age_on_2026_12_31 BETWEEN 18 AND 75 AS age_ok,
    d.PATIENT IS NOT NULL AND d.onset <= DATE '2026-10-13' AND d.overlaps_window AS dm_active,
    d.PATIENT IS NOT NULL AND d.onset BETWEEN DATE '2025-01-01' AND DATE '2026-10-13' AS dm_onset_in_window,
    p.died_during_period,
    hospice.PATIENT IS NOT NULL AS hospice,
    a.observed_date AS a1c_date,
    a.a1c,
    a.PATIENT IS NOT NULL AS has_a1c,
    a.PATIENT IS NOT NULL AND a.a1c < 8 AS under_8,
    a.PATIENT IS NOT NULL AND a.a1c > 9 AS over_9_value
FROM analytic.patient_period p
LEFT JOIN dm d ON p.patient_id = d.PATIENT
LEFT JOIN hospice ON p.patient_id = hospice.PATIENT
LEFT JOIN latest a ON p.patient_id = a.PATIENT AND a.rn = 1;
