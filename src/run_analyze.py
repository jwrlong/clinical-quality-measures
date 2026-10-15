"""Study rates for blood pressure control and glycemic status.

These are not HEDIS results. The published event requires diagnosis dates
the export does not store. The rates below use an active problem list and
say so in the summary.
"""

import math
from datetime import date
from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "warehouse" / "riverbend.duckdb"
SQL = ROOT / "sql" / "analyze_measures.sql"
OUT = ROOT / "outputs"
FIG = OUT / "figures"
SUMMARY = ROOT / "docs" / "analysis-summary.md"

RAW_PATIENTS = 2285
DIED_BEFORE = 277


def wilson(k, n, z=1.96):
    if n == 0:
        return None, None, None
    p = k / n
    z2 = z * z
    denom = 1 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    margin = z * math.sqrt((p * (1 - p) / n) + z2 / (4 * n * n)) / denom
    return p, max(0.0, center - margin), min(1.0, center + margin)


def pct(k, n):
    if n == 0:
        return "—"
    return f"{100 * k / n:.1f}%"


def ci_text(k, n):
    p, lo, hi = wilson(k, n)
    if p is None:
        return "—"
    return f"{100 * p:.1f}% ({100 * lo:.1f}–{100 * hi:.1f})"


def rate_row(label, group, frame, numer_col):
    rows = []
    for name, part in frame.groupby(group, dropna=False):
        n = len(part)
        k = int(part[numer_col].sum())
        p, lo, hi = wilson(k, n)
        rows.append(
            {
                "measure": label,
                "group": group,
                "level": "unknown" if pd.isna(name) else str(name),
                "n": n,
                "numerator": k,
                "rate": None if p is None else round(p, 4),
                "ci_low": None if lo is None else round(lo, 4),
                "ci_high": None if hi is None else round(hi, 4),
            }
        )
    return rows


def flow_counts(frame, condition_col):
    pool = frame
    age = pool[pool["age_ok"]]
    cond = age[age[condition_col]]
    alive = cond[~cond["died_during_period"]]
    denom = alive[~alive["hospice"]]
    return {
        "in_window": len(pool),
        "removed_age": len(pool) - len(age),
        "age_ok": len(age),
        "removed_condition": len(age) - len(cond),
        "with_condition": len(cond),
        "removed_death": len(cond) - len(alive),
        "alive": len(alive),
        "removed_hospice": len(alive) - len(denom),
        "denominator": len(denom),
    }


def main():
    con = duckdb.connect(str(DB))
    script = SQL.read_text()
    for statement in [part.strip() for part in script.split(";") if part.strip()]:
        con.execute(statement)

    bp = con.execute("SELECT * FROM analytic.bp_person").fetchdf()
    gsd = con.execute("SELECT * FROM analytic.gsd_person").fetchdf()
    for frame in (bp, gsd):
        for col in ("age_ok", "died_during_period", "hospice", "has_bp", "controlled"):
            if col in frame.columns:
                frame[col] = frame[col].fillna(False).astype(bool)
        for col in ("htn_active", "htn_onset_in_window", "dm_active", "dm_onset_in_window", "has_a1c", "under_8", "over_9_value"):
            if col in frame.columns:
                frame[col] = frame[col].fillna(False).astype(bool)

    bp_flow = flow_counts(bp, "htn_active")
    gsd_flow = flow_counts(gsd, "dm_active")
    bp_den = bp[bp["age_ok"] & bp["htn_active"] & ~bp["died_during_period"] & ~bp["hospice"]].copy()
    gsd_den = gsd[gsd["age_ok"] & gsd["dm_active"] & ~gsd["died_during_period"] & ~gsd["hospice"]].copy()
    bp_den["controlled"] = bp_den["controlled"].astype(bool)
    gsd_den["under_8"] = gsd_den["under_8"].astype(bool)
    gsd_den["poor"] = (~gsd_den["has_a1c"]) | gsd_den["over_9_value"]
    gsd_den["middle"] = gsd_den["has_a1c"] & ~gsd_den["under_8"] & ~gsd_den["over_9_value"]

    literal_htn = con.execute(
        """
        WITH visits AS (
            SELECT c.PATIENT, e.start_date
            FROM staging.conditions c
            JOIN staging.encounters e ON c.ENCOUNTER = e.Id
            JOIN analytic.patient_period p ON c.PATIENT = p.patient_id
            WHERE cast(c.CODE AS VARCHAR) = '59621000'
              AND e.ENCOUNTERCLASS IN ('ambulatory', 'wellness', 'outpatient', 'virtual')
              AND e.start_date BETWEEN DATE '2025-01-01' AND DATE '2026-06-30'
              AND NOT e.after_death
        )
        SELECT count(*) FROM (
            SELECT PATIENT FROM visits GROUP BY PATIENT HAVING count(DISTINCT start_date) >= 2
        )
        """
    ).fetchone()[0]
    literal_dm = con.execute(
        """
        WITH visits AS (
            SELECT c.PATIENT, e.start_date
            FROM staging.conditions c
            JOIN staging.encounters e ON c.ENCOUNTER = e.Id
            JOIN analytic.patient_period p ON c.PATIENT = p.patient_id
            WHERE cast(c.CODE AS VARCHAR) = '44054006'
              AND e.ENCOUNTERCLASS <> 'laboratory'
              AND e.start_date BETWEEN DATE '2025-01-01' AND DATE '2026-10-13'
              AND NOT e.after_death
        )
        SELECT count(*) FROM (
            SELECT PATIENT FROM visits GROUP BY PATIENT HAVING count(DISTINCT start_date) >= 2
        )
        """
    ).fetchone()[0]

    bp_sens = bp[bp["age_ok"] & bp["htn_onset_in_window"] & ~bp["died_during_period"] & ~bp["hospice"]]
    gsd_sens = gsd[gsd["age_ok"] & gsd["dm_onset_in_window"] & ~gsd["died_during_period"] & ~gsd["hospice"]]

    def band(age):
        if age < 45:
            return "18–44"
        if age < 65:
            return "45–64"
        return "65 and older"

    bp_den["age_band"] = bp_den["age"].map(band)
    gsd_den["age_band"] = gsd_den["age"].map(band)

    rows = []
    rows.append(
        {
            "measure": "bp_control",
            "group": "overall",
            "level": "network",
            "n": len(bp_den),
            "numerator": int(bp_den["controlled"].sum()),
            "rate": None,
            "ci_low": None,
            "ci_high": None,
        }
    )
    p, lo, hi = wilson(rows[-1]["numerator"], rows[-1]["n"])
    rows[-1].update(rate=None if p is None else round(p, 4), ci_low=None if lo is None else round(lo, 4), ci_high=None if hi is None else round(hi, 4))
    rows += rate_row("bp_control", "gender", bp_den, "controlled")
    rows += rate_row("bp_control", "age_band", bp_den, "controlled")
    rows += rate_row("bp_control", "race", bp_den, "controlled")
    rows += rate_row("bp_control", "ethnicity", bp_den, "controlled")
    g_under = {
        "measure": "glycemic_under_8",
        "group": "overall",
        "level": "network",
        "n": len(gsd_den),
        "numerator": int(gsd_den["under_8"].sum()),
    }
    p, lo, hi = wilson(g_under["numerator"], g_under["n"])
    g_under.update(rate=None if p is None else round(p, 4), ci_low=None if lo is None else round(lo, 4), ci_high=None if hi is None else round(hi, 4))
    g_poor = {
        "measure": "glycemic_over_9",
        "group": "overall",
        "level": "network",
        "n": len(gsd_den),
        "numerator": int(gsd_den["poor"].sum()),
    }
    p, lo, hi = wilson(g_poor["numerator"], g_poor["n"])
    g_poor.update(rate=None if p is None else round(p, 4), ci_low=None if lo is None else round(lo, 4), ci_high=None if hi is None else round(hi, 4))
    rows += [g_under, g_poor]
    rows += rate_row("glycemic_under_8", "gender", gsd_den, "under_8")
    rows += rate_row("glycemic_under_8", "age_band", gsd_den, "under_8")
    rows += rate_row("glycemic_under_8", "race", gsd_den, "under_8")
    rows += rate_row("glycemic_over_9", "gender", gsd_den, "poor")
    rows += rate_row("glycemic_over_9", "age_band", gsd_den, "poor")
    rows += rate_row("glycemic_over_9", "race", gsd_den, "poor")

    org_names = con.execute("SELECT Id, NAME FROM organizations").fetchdf().set_index("Id")["NAME"]

    def clinic_table(frame, numer_col, measure):
        out = []
        for org, part in frame.groupby("organization_id", dropna=False):
            n = len(part)
            k = int(part[numer_col].sum())
            p, lo, hi = wilson(k, n)
            name = "No encounter in the window" if pd.isna(org) else str(org_names.get(org, org))
            out.append(
                {
                    "measure": measure,
                    "organization_id": None if pd.isna(org) else org,
                    "organization": name,
                    "n": n,
                    "numerator": k,
                    "rate": p,
                    "ci_low": lo,
                    "ci_high": hi,
                }
            )
        return pd.DataFrame(out).sort_values(["n", "organization"], ascending=[False, True])

    bp_clinics = clinic_table(bp_den, "controlled", "bp_control")
    gsd_clinics = clinic_table(gsd_den, "under_8", "glycemic_under_8")
    for table, network_rate in (
        (bp_clinics, rows[0]["rate"]),
        (gsd_clinics, g_under["rate"]),
    ):
        if network_rate is None:
            table["ci_excludes_network"] = False
        else:
            table["ci_excludes_network"] = (table["ci_high"] < network_rate) | (table["ci_low"] > network_rate)

    test = fit_clinic_test(bp_den)

    quarters = quarterly(con, bp_den["patient_id"].tolist())
    gsd_quarters = quarterly_a1c(con, gsd_den["patient_id"].tolist())

    bp_k = int(bp_den["controlled"].sum())
    bp_n = len(bp_den)
    bp_missing = int((~bp_den["has_bp"]).sum())
    bp_high = int((bp_den["has_bp"] & ~bp_den["controlled"]).sum())
    g_n = len(gsd_den)
    g_under_k = int(gsd_den["under_8"].sum())
    g_poor_k = int(gsd_den["poor"].sum())
    g_missing = int((~gsd_den["has_a1c"]).sum())
    g_middle = int(gsd_den["middle"].sum())
    g_over_value = int(gsd_den["over_9_value"].sum())

    sens_bp_k = int(bp_sens["controlled"].sum()) if len(bp_sens) else 0
    sens_g_k = int(gsd_sens["under_8"].sum()) if len(gsd_sens) else 0
    sens_g_poor = int(((~gsd_sens["has_a1c"]) | gsd_sens["over_9_value"]).sum()) if len(gsd_sens) else 0

    rates = pd.DataFrame(rows)
    rates.to_csv(OUT / "analysis_rates.csv", index=False)
    bp_clinics.to_csv(OUT / "bp_clinic_rates.csv", index=False)
    gsd_clinics.to_csv(OUT / "gsd_clinic_rates.csv", index=False)

    draw_flow(bp_flow, gsd_flow, bp_k, bp_missing, bp_high, g_under_k, g_missing, g_middle, g_over_value, g_n)
    draw_forest(
        bp_clinics, rows[0]["rate"], "Blood pressure: which clinics differ from the network?",
        FIG / "bp_clinic_forest.png", min_n=5,
        xlabel="Share with systolic under 140 and diastolic under 90",
        note="Each line is the range a clinic of this size can support. A line that crosses the red network rate is not a clear difference. Clinics with fewer than 5 patients are in the clinic file.",
    )
    draw_forest(
        gsd_clinics, g_under["rate"], "Diabetes: which clinics differ from the network?",
        FIG / "gsd_clinic_forest.png", min_n=3,
        xlabel="Share with A1c under 8%",
        note="No clinic has 10 or more patients, so every line is wide. Clinics with fewer than 3 patients are in the clinic file.",
    )
    draw_trend(
        quarters, FIG / "bp_trend.png",
        "Blood pressure control among patients who already have a reading",
        "Share controlled",
    )
    draw_trend(
        gsd_quarters, FIG / "gsd_trend.png",
        "A1c under 8% among patients who already have a result",
        "Share under 8%",
    )

    bp_real = bp_clinics[bp_clinics["organization_id"].notna()]
    gsd_real = gsd_clinics[gsd_clinics["organization_id"].notna()]
    n_bp_orgs = len(bp_real)
    n_bp_ge30 = int((bp_real["n"] >= 30).sum())
    n_bp_ge10 = int((bp_real["n"] >= 10).sum())
    n_bp_ge5 = int((bp_real["n"] >= 5).sum())
    n_bp_cross = int(bp_real["ci_excludes_network"].fillna(False).sum())
    cross_n = bp_real.loc[bp_real["ci_excludes_network"].fillna(False), "n"]
    n_bp_cross_smallest = int(cross_n.min()) if len(cross_n) else None
    n_g_orgs = len(gsd_real)
    n_g_ge10 = int((gsd_real["n"] >= 10).sum())
    n_g_ge3 = int((gsd_real["n"] >= 3).sum())
    largest_bp = int(bp_real["n"].max()) if len(bp_real) else 0
    largest_g = int(gsd_real["n"].max()) if len(gsd_real) else 0
    bp_unattributed = int(bp_clinics.loc[bp_clinics["organization_id"].isna(), "n"].sum())
    gsd_unattributed = int(gsd_clinics.loc[gsd_clinics["organization_id"].isna(), "n"].sum())

    text = render(
        literal_htn,
        literal_dm,
        bp_flow,
        gsd_flow,
        bp_n,
        bp_k,
        bp_missing,
        bp_high,
        g_n,
        g_under_k,
        g_poor_k,
        g_missing,
        g_middle,
        g_over_value,
        bp_sens,
        sens_bp_k,
        gsd_sens,
        sens_g_k,
        sens_g_poor,
        rates,
        n_bp_orgs,
        n_bp_ge30,
        n_bp_ge10,
        n_bp_ge5,
        n_bp_cross,
        n_bp_cross_smallest,
        n_g_orgs,
        n_g_ge10,
        n_g_ge3,
        largest_bp,
        largest_g,
        bp_unattributed,
        gsd_unattributed,
        test,
        quarters,
        gsd_quarters,
    )
    SUMMARY.write_text(text)
    print(f"bp denominator {bp_n} controlled {bp_k} missing {bp_missing}")
    print(f"gsd denominator {g_n} under 8 {g_under_k} over 9 or missing {g_poor_k}")
    print(f"wrote {SUMMARY}")
    con.close()


def fit_clinic_test(bp_den):
    result = {"status": "not_run", "detail": ""}
    try:
        import statsmodels.formula.api as smf
        from scipy import stats
    except ImportError as exc:
        result["status"] = "missing_library"
        result["detail"] = f"The clinic test was not run because {exc.name} is not installed."
        return result
    if len(bp_den) < 30 or bp_den["controlled"].nunique() < 2:
        result["status"] = "too_small"
        result["detail"] = "The blood-pressure denominator is too small, or every patient has the same outcome, so a regression was not fit."
        return result
    sizes = bp_den.groupby("organization_id").size()
    keep = sizes[sizes >= 30].index
    model_frame = bp_den[bp_den["organization_id"].isin(keep)].copy()
    age_model = smf.logit("controlled ~ age", data=bp_den.assign(controlled=bp_den["controlled"].astype(int))).fit(disp=False)
    age_or = math.exp(age_model.params["age"])
    age_p = float(age_model.pvalues["age"])
    result["age_or"] = age_or
    result["age_p"] = age_p
    result["age_n"] = len(bp_den)
    if model_frame["organization_id"].nunique() < 2:
        result["status"] = "age_only"
        result["detail"] = (
            f"Fewer than two clinics have 30 or more patients in the blood-pressure denominator "
            f"(largest clinic n = {int(sizes.max()) if len(sizes) else 0}). "
            f"A clinic comparison after age adjustment is not estimable. "
            f"An age-only model on the {len(bp_den)} denominator patients gives an odds ratio of {age_or:.3f} per year of age (p = {age_p:.3f})."
        )
        return result
    full = smf.logit(
        "controlled ~ age + C(organization_id)",
        data=model_frame.assign(controlled=model_frame["controlled"].astype(int)),
    ).fit(disp=False)
    age_on_subset = smf.logit(
        "controlled ~ age",
        data=model_frame.assign(controlled=model_frame["controlled"].astype(int)),
    ).fit(disp=False)
    lr = 2 * (full.llf - age_on_subset.llf)
    df = int(full.df_model - age_on_subset.df_model)
    pval = float(stats.chi2.sf(lr, df)) if df > 0 else None
    result["status"] = "clinic"
    result["lr"] = lr
    result["df"] = df
    result["p"] = pval
    result["n_clinics"] = int(model_frame["organization_id"].nunique())
    result["n_patients"] = len(model_frame)
    result["detail"] = (
        f"Among {result['n_clinics']} clinics with at least 30 denominator patients "
        f"({result['n_patients']} patients), a logistic model with clinic indicators was compared with a model that has age only. "
        f"Likelihood-ratio statistic {lr:.2f} on {df} degrees of freedom, p = {pval:.3f}. "
        f"On the full denominator, the age-only odds ratio is {age_or:.3f} per year (p = {age_p:.3f})."
    )
    return result


def quarterly(con, patient_ids):
    if not patient_ids:
        return []
    con.register("bp_ids", pd.DataFrame({"patient_id": patient_ids}))
    readings = con.execute(
        """
        WITH htn AS (
            SELECT PATIENT, min(START) AS onset
            FROM staging.conditions
            WHERE cast(CODE AS VARCHAR) = '59621000'
            GROUP BY PATIENT
        )
        SELECT o.PATIENT AS patient_id, o.observed_date,
               min(CASE WHEN o.CODE = '8480-6' THEN o.value_numeric END) AS systolic,
               min(CASE WHEN o.CODE = '8462-4' THEN o.value_numeric END) AS diastolic
        FROM analytic.observation_eligible o
        JOIN staging.encounters e ON o.ENCOUNTER = e.Id
        JOIN htn h ON o.PATIENT = h.PATIENT
        JOIN bp_ids d ON o.PATIENT = d.patient_id
        WHERE o.CODE IN ('8480-6', '8462-4')
          AND e.ENCOUNTERCLASS IN ('ambulatory', 'wellness', 'outpatient', 'virtual', 'urgentcare')
          AND o.observed_date >= h.onset
        GROUP BY o.PATIENT, o.observed_date
        HAVING min(CASE WHEN o.CODE = '8480-6' THEN o.value_numeric END) IS NOT NULL
           AND min(CASE WHEN o.CODE = '8462-4' THEN o.value_numeric END) IS NOT NULL
        """
    ).fetchdf()
    ends = [
        ("Through 31 Mar", date(2026, 3, 31)),
        ("Through 30 Jun", date(2026, 6, 30)),
        ("Through 30 Sep", date(2026, 9, 30)),
        ("Through 13 Oct", date(2026, 10, 13)),
    ]
    denom_n = len(patient_ids)
    points = []
    if readings.empty:
        for label, _ in ends:
            points.append({"label": label, "n_measured": 0, "k": 0, "n_denom": denom_n, "rate": None, "lo": None, "hi": None})
        return points
    readings["observed_date"] = pd.to_datetime(readings["observed_date"]).dt.date
    for label, end in ends:
        part = readings[readings["observed_date"] <= end]
        latest = part.sort_values("observed_date").groupby("patient_id").tail(1)
        k = int(((latest["systolic"] < 140) & (latest["diastolic"] < 90)).sum())
        n = len(latest)
        p, lo, hi = wilson(k, n)
        points.append({"label": label, "n_measured": n, "k": k, "n_denom": denom_n, "rate": p, "lo": lo, "hi": hi})
    return points


def quarterly_a1c(con, patient_ids):
    ends = [
        ("Through 31 Mar", date(2026, 3, 31)),
        ("Through 30 Jun", date(2026, 6, 30)),
        ("Through 30 Sep", date(2026, 9, 30)),
        ("Through 13 Oct", date(2026, 10, 13)),
    ]
    denom_n = len(patient_ids)
    if not patient_ids:
        return [{"label": label, "n_measured": 0, "k": 0, "n_denom": denom_n, "rate": None, "lo": None, "hi": None} for label, _ in ends]
    con.register("gsd_ids", pd.DataFrame({"patient_id": patient_ids}))
    readings = con.execute(
        """
        SELECT o.PATIENT AS patient_id, o.observed_date, min(o.value_numeric) AS a1c
        FROM analytic.observation_eligible o
        JOIN gsd_ids d ON o.PATIENT = d.patient_id
        WHERE o.CODE = '4548-4'
          AND o.observed_date BETWEEN DATE '2026-01-01' AND DATE '2026-10-13'
        GROUP BY o.PATIENT, o.observed_date
        """
    ).fetchdf()
    points = []
    if readings.empty:
        for label, _ in ends:
            points.append({"label": label, "n_measured": 0, "k": 0, "n_denom": denom_n, "rate": None, "lo": None, "hi": None})
        return points
    readings["observed_date"] = pd.to_datetime(readings["observed_date"]).dt.date
    for label, end in ends:
        part = readings[readings["observed_date"] <= end]
        latest = part.sort_values("observed_date").groupby("patient_id").tail(1)
        k = int((latest["a1c"] < 8).sum())
        n = len(latest)
        p, lo, hi = wilson(k, n)
        points.append({"label": label, "n_measured": n, "k": k, "n_denom": denom_n, "rate": p, "lo": lo, "hi": hi})
    return points


def draw_flow(bp_flow, gsd_flow, bp_k, bp_missing, bp_high, g_under_k, g_missing, g_middle, g_over_value, g_n):
    fig, axes = plt.subplots(1, 2, figsize=(13.2, 8.4))
    panels = [
        (
            axes[0],
            "Blood pressure",
            [
                ("Patients in the export", RAW_PATIENTS),
                ("Alive on 1 Jan 2026", bp_flow["in_window"]),
                ("Age 18–85 on 31 Dec 2026", bp_flow["age_ok"]),
                ("Active hypertension", bp_flow["with_condition"]),
                ("Alive through 13 Oct 2026", bp_flow["alive"]),
                ("Denominator", bp_flow["denominator"]),
            ],
            [
                ("died before 2026", DIED_BEFORE),
                ("outside the age range", bp_flow["removed_age"]),
                ("no active hypertension", bp_flow["removed_condition"]),
                ("died during the window", bp_flow["removed_death"]),
                ("hospice encounter", bp_flow["removed_hospice"]),
            ],
            [
                ("Controlled, under 140 and 90", bp_k),
                ("Reading at or above 140 or 90", bp_high),
                ("No usable reading", bp_missing),
            ],
        ),
        (
            axes[1],
            "Glycemic status",
            [
                ("Patients in the export", RAW_PATIENTS),
                ("Alive on 1 Jan 2026", gsd_flow["in_window"]),
                ("Age 18–75 on 31 Dec 2026", gsd_flow["age_ok"]),
                ("Active type 2 diabetes", gsd_flow["with_condition"]),
                ("Alive through 13 Oct 2026", gsd_flow["alive"]),
                ("Denominator", gsd_flow["denominator"]),
            ],
            [
                ("died before 2026", DIED_BEFORE),
                ("outside the age range", gsd_flow["removed_age"]),
                ("no active diabetes", gsd_flow["removed_condition"]),
                ("died during the window", gsd_flow["removed_death"]),
                ("hospice encounter", gsd_flow["removed_hospice"]),
            ],
            [
                ("Most recent A1c under 8%", g_under_k),
                ("A1c from 8% through 9%", g_middle),
                ("A1c over 9%", g_over_value),
                ("No A1c in the window", g_missing),
            ],
        ),
    ]
    for ax, title, steps, removed, split in panels:
        ax.set_xlim(0, 14)
        ax.set_ylim(-2.4, len(steps) * 1.15 + 0.4)
        ax.axis("off")
        ax.set_title(title, loc="left", fontsize=12, pad=10)
        for i, (label, n) in enumerate(steps):
            y = (len(steps) - 1 - i) * 1.15
            ax.add_patch(plt.Rectangle((0.15, y), 6.6, 0.85, color="#1f4e79", zorder=2))
            ax.text(0.35, y + 0.42, label, va="center", ha="left", color="white", fontsize=8.5, zorder=3)
            ax.text(6.55, y + 0.42, f"{n:,}", va="center", ha="right", color="white", fontsize=9, zorder=3)
            if i < len(removed):
                rlabel, rn = removed[i]
                ax.text(6.9, y + 0.42, f"−{rn:,}  {rlabel}", va="center", ha="left", color="#9c2f2f", fontsize=8)
        ax.text(0.15, -0.35, "Denominator split", fontsize=8.5, color="#333333")
        for j, (label, n) in enumerate(split):
            ax.text(0.15, -0.8 - j * 0.38, f"{label}: {n:,}", fontsize=8, color="#333333")
    fig.suptitle("Who reaches the denominator, and how the numerator splits", fontsize=13)
    fig.tight_layout()
    fig.savefig(FIG / "cohort_flow.png", dpi=140)
    plt.close(fig)
    if g_n != gsd_flow["denominator"]:
        raise SystemExit("Glycemic denominator split does not match the flow")
    if bp_k + bp_missing + bp_high != bp_flow["denominator"]:
        raise SystemExit("Blood-pressure numerator split does not match the flow")


def draw_forest(clinics, network_rate, title, path, min_n, note, xlabel):
    plot = clinics[(clinics["organization_id"].notna()) & (clinics["n"] >= min_n)].sort_values("rate")
    fig, ax = plt.subplots(figsize=(9.2, max(3.8, 0.42 * max(len(plot), 1) + 1.6)))
    if plot.empty or network_rate is None:
        ax.text(0.5, 0.5, note, ha="center", va="center")
        ax.axis("off")
    else:
        y = range(len(plot))
        rates = plot["rate"].to_numpy()
        lo = plot["ci_low"].to_numpy()
        hi = plot["ci_high"].to_numpy()
        ax.errorbar(
            rates,
            list(y),
            xerr=[rates - lo, hi - rates],
            fmt="o",
            color="#1f4e79",
            ecolor="#7f97ad",
            capsize=3,
        )
        ax.axvline(network_rate, color="#9c2f2f", lw=1, label=f"Network {100 * network_rate:.1f}%")
        labels = [f"{name[:40]}  (n={n})" for name, n in zip(plot["organization"], plot["n"])]
        ax.set_yticks(list(y), labels, fontsize=8)
        ax.set_xlabel(xlabel)
        ax.set_xlim(-0.02, 1.06)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _pos: f"{100 * v:.0f}%"))
        ax.legend(frameon=False, loc="lower right")
        ax.text(0.0, -0.22, note, transform=ax.transAxes, fontsize=8, color="#444444", wrap=True)
    ax.set_title(title, loc="left")
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def draw_trend(quarters, path, title, ylabel):
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    xs = list(range(len(quarters)))
    rates = [q["rate"] if q["rate"] is not None else float("nan") for q in quarters]
    lo = [q["lo"] if q["lo"] is not None else float("nan") for q in quarters]
    hi = [q["hi"] if q["hi"] is not None else float("nan") for q in quarters]
    ax.fill_between(xs, lo, hi, color="#1f4e79", alpha=0.15, label="95% range")
    ax.plot(xs, rates, color="#1f4e79", marker="o")
    ax.set_xticks(xs, [f"{q['label']}\n(n={q['n_measured']})" for q in quarters])
    ax.set_ylim(-0.02, 1.06)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _pos: f"{100 * v:.0f}%"))
    ax.set_ylabel(ylabel)
    ax.set_title(title, loc="left")
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def render(
    literal_htn,
    literal_dm,
    bp_flow,
    gsd_flow,
    bp_n,
    bp_k,
    bp_missing,
    bp_high,
    g_n,
    g_under_k,
    g_poor_k,
    g_missing,
    g_middle,
    g_over_value,
    bp_sens,
    sens_bp_k,
    gsd_sens,
    sens_g_k,
    sens_g_poor,
    rates,
    n_bp_orgs,
    n_bp_ge30,
    n_bp_ge10,
    n_bp_ge5,
    n_bp_cross,
    n_bp_cross_smallest,
    n_g_orgs,
    n_g_ge10,
    n_g_ge3,
    largest_bp,
    largest_g,
    bp_unattributed,
    gsd_unattributed,
    test,
    quarters,
    gsd_quarters,
):
    def group_lines(measure, group):
        part = rates[(rates["measure"] == measure) & (rates["group"] == group)].sort_values("level")
        lines = []
        for rec in part.itertuples():
            lines.append(f"| {rec.level} | {rec.n} | {rec.numerator} | {ci_text(rec.numerator, rec.n)} |")
        return "\n".join(lines)

    q_lines = []
    for q in quarters:
        q_lines.append(
            f"| {q['label']} | {q['n_measured']} of {q['n_denom']} | {q['k']} | {ci_text(q['k'], q['n_measured'])} |"
        )
    g_lines = []
    for q in gsd_quarters:
        g_lines.append(
            f"| {q['label']} | {q['n_measured']} of {q['n_denom']} | {q['k']} | {ci_text(q['k'], q['n_measured'])} |"
        )
    if n_bp_cross == 0:
        cross_sentence = "Every blood-pressure clinic interval includes the network rate."
    elif n_bp_cross == 1:
        cross_sentence = (
            f"One blood-pressure clinic interval excludes the network rate, and that clinic has {n_bp_cross_smallest} patients."
        )
    else:
        cross_sentence = (
            f"{n_bp_cross} blood-pressure clinic intervals exclude the network rate. "
            f"The smallest of those clinics has {n_bp_cross_smallest} patients."
        )
    reach_30 = "No organization reaches 30 patients." if n_bp_ge30 == 0 else f"{n_bp_ge30} organizations reach 30 patients."
    glycemic_reach = (
        "No glycemic clinic reaches 10 patients."
        if n_g_ge10 == 0
        else f"{n_g_ge10} glycemic clinics reach 10 patients."
    )

    return f"""# Analysis summary

Riverbend Community Health Network. Measurement window 1 January 2026 through 13 October 2026, the last day this Synthea extract covers. Prepared 14 October 2026.

Portfolio note. Riverbend is an illustrative safety-net network. The rates in this note are a study definition applied to a public synthetic file. They are not HEDIS results, and they are not the hospital contract packet in `docs/leadership-dashboard.md`.

## What was measured

Blood pressure control follows the public structure of HEDIS Controlling High Blood Pressure: adults 18–85, essential hypertension, and a most recent blood pressure in the measurement year under 140 systolic and under 90 diastolic. A missing reading stays in the denominator and counts as not controlled.

Glycemic status follows the public structure of HEDIS Glycemic Status Assessment for Patients With Diabetes: adults 18–75 with diabetes, one denominator, and two results. Under 8% is the result where higher is better. Over 9% is the result where lower is better, and a missing A1c counts in the over-9 result. A result from 8.0% through 9.0% is in neither.

Both published denominators require two diagnosis dates of service, or, for glycemic status, one diagnosis date plus a dispensing event. This export stores each diagnosis once, at onset. Patients with the code on two different dates: **{literal_htn}** for essential hypertension (SNOMED 59621000) and **{literal_dm}** for type 2 diabetes (SNOMED 44054006). A literal published denominator cannot be formed.

The study denominator uses the problem list instead. Hypertension counts when the onset is on or before 30 June 2026 and the condition is still open on 1 January 2025. Diabetes counts when the onset is on or before 13 October 2026 and the condition is still open on 1 January 2025. Death during the window and a hospice encounter are removed. Pregnancy, end-stage renal disease, frailty, and institutional long-term care are not applied: this file has no value set for them and no institutional flag.

The numerator uses the most recent qualifying day. Blood pressure must fall on or after the hypertension onset, in an ambulatory, wellness, outpatient, virtual, or urgent-care encounter. Inpatient and emergency readings are left out. Home readings are left out because the file does not say whether the device was digital. When a day has more than one reading, the numerator uses the lower systolic and the lower diastolic. A1c uses the lower result when more than one falls on the same day. The window function that picks the latest day is in `sql/analyze_measures.sql`.

## Denominators

| Step | Blood pressure | Glycemic status |
| --- | ---: | ---: |
| Patients in the export | {RAW_PATIENTS} | {RAW_PATIENTS} |
| Died before 1 January 2026 | {DIED_BEFORE} | {DIED_BEFORE} |
| Outside the age range | {bp_flow['removed_age']} | {gsd_flow['removed_age']} |
| No active condition on the problem list | {bp_flow['removed_condition']} | {gsd_flow['removed_condition']} |
| Died during the window | {bp_flow['removed_death']} | {gsd_flow['removed_death']} |
| Hospice encounter | {bp_flow['removed_hospice']} | {gsd_flow['removed_hospice']} |
| Denominator | {bp_n} | {g_n} |

The figure is `outputs/figures/cohort_flow.png`.

## Results

Blood pressure. Denominator {bp_n}. Controlled {bp_k}, {ci_text(bp_k, bp_n)}. Reading at or above the threshold {bp_high}. No usable reading {bp_missing}. Those {bp_missing} patients stay in the denominator and count as not controlled.

Glycemic status. Denominator {g_n}. A1c under 8% {g_under_k}, {ci_text(g_under_k, g_n)}. A1c over 9% or no A1c {g_poor_k}, {ci_text(g_poor_k, g_n)}. Of that over-9 result, {g_over_value} have an A1c over 9% and {g_missing} have no A1c. A1c from 8% through 9%: {g_middle}, in neither result.

### Blood pressure by age and sex

| Group | Denominator | Controlled | Rate (95% interval) |
| --- | ---: | ---: | --- |
{group_lines('bp_control', 'age_band')}
{group_lines('bp_control', 'gender')}

### Glycemic status under 8% by age and sex

| Group | Denominator | Under 8% | Rate (95% interval) |
| --- | ---: | ---: | --- |
{group_lines('glycemic_under_8', 'age_band')}
{group_lines('glycemic_under_8', 'gender')}

Race and ethnicity rates are in `outputs/analysis_rates.csv`. Several race groups have denominators under 30, and those intervals are wide enough that a ranking would overstate a difference.

## Clinics

The {bp_n} blood-pressure patients are attributed to {n_bp_orgs} organizations. Another {bp_unattributed} have no encounter in the window, so they have no clinic and no reading, and they count as not controlled. {reach_30} {n_bp_ge10} have at least 10 patients, and {n_bp_ge5} have at least 5. The largest blood-pressure clinic denominator is {largest_bp}.

{cross_sentence} The {n_bp_ge10} clinics with 10 or more patients have intervals that include the network rate. A ranking of sites would treat noise as a difference.

Glycemic patients are attributed to {n_g_orgs} organizations, plus {gsd_unattributed} with no encounter in the window. The largest glycemic clinic denominator is {largest_g}. {glycemic_reach} {n_g_ge3} have at least 3 patients.

Clinic rates with intervals are in `outputs/bp_clinic_rates.csv` and `outputs/gsd_clinic_rates.csv`. The forest plots are `outputs/figures/bp_clinic_forest.png` (clinics with at least 5 patients) and `outputs/figures/gsd_clinic_forest.png` (clinics with at least 3).

## One test

{test['detail']}

## Sensitivity

The study denominator counts a condition that started years ago if it is still on the problem list. Restricting the denominator to an onset inside the identification window is the check on that choice.

| Rule | Blood pressure denominator | Controlled | Glycemic denominator | Under 8% | Over 9% or missing |
| --- | ---: | ---: | ---: | ---: | ---: |
| Active problem list | {bp_n} | {bp_k} ({pct(bp_k, bp_n)}) | {g_n} | {g_under_k} ({pct(g_under_k, g_n)}) | {g_poor_k} ({pct(g_poor_k, g_n)}) |
| Onset inside the identification window | {len(bp_sens)} | {sens_bp_k} ({pct(sens_bp_k, len(bp_sens))}) | {len(gsd_sens)} | {sens_g_k} ({pct(sens_g_k, len(gsd_sens))}) | {sens_g_poor} ({pct(sens_g_poor, len(gsd_sens))}) |

The identification window is 1 January 2025 through 30 June 2026 for hypertension, and 1 January 2025 through 13 October 2026 for diabetes. {len(bp_sens)} of the {bp_n} blood-pressure patients, and {len(gsd_sens)} of the {g_n} diabetes patients, have an onset inside that window. The study rates are carried by conditions that began before 2025.

## Direction across the window

The trend uses the same blood-pressure denominator and asks, at each quarter end, what share of patients who already have a reading are controlled. The interval is a Wilson interval on that measured group. Patients with no reading yet are not in the line. They remain in the denominator of the full-window rate above.

| Point | Patients with a reading | Controlled | Rate (95% interval) |
| --- | ---: | ---: | --- |
{chr(10).join(q_lines)}

The figure is `outputs/figures/bp_trend.png`.

The glycemic trend uses the same rule on the diabetes denominator: at each quarter end, the share under 8% among patients who already have an A1c. Patients with no result yet are outside the line and remain in the full-window denominator.

| Point | Patients with an A1c | Under 8% | Rate (95% interval) |
| --- | ---: | ---: | --- |
{chr(10).join(g_lines)}

The figure is `outputs/figures/gsd_trend.png`.

## Where these rates belong

These percentages stay in this study note. The contract dashboard still has no rate: {literal_htn} patients have two hypertension diagnosis dates, and {literal_dm} have two diabetes diagnosis dates. The rates above describe the active problem list and the readings in this file under a public-style numerator.
"""


if __name__ == "__main__":
    main()
