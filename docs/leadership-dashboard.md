# Leadership quality dashboard

**Portfolio note.** Independent demonstration for an illustrative regional health system with 3 hospitals and about 15 outpatient clinics. The layout below is a specification for clinical leadership. Figures in the sketch are placeholders, not performance results.

**Measurement year.** 1 January 2026 through 31 December 2026.
**Audience.** Chief medical officer, quality leadership, hospital chiefs, and clinic medical directors.
**Companion documents.** `docs/measure-specifications.md`, `docs/data-profile.md`, and `docs/data-gap-memo.md`.

## What this page is for

One screen answers three questions: where the system stands on the two contract measures and the hospital harm measure, whether a change is large enough to act on, and whether the rate moved because care changed or because a result never became a discrete value.

The page shows the same definitions as the measure specifications. It does not invent a second version of any measure for display.

## Front page

```
Quality performance
2026 year to date, through [monthly close]
Population label: Payer-aligned  |  EHR clinic rate
Figures below are layout placeholders.

+---------------------------+---------------------------+---------------------------+
| CBP                       | GSD                       | CMS816v5                  |
| Controlling High BP       | Glycemic status           | Severe hypoglycemia       |
| HEDIS · clinics           | HEDIS · clinics           | CMS eCQM · hospitals      |
|                           |                           |                           |
| [rate] controlled         | [rate] over 9.0%          | [rate] of hospitalizations|
| Higher is better          | Lower is better           | Lower is better           |
| [n] / [denominator]       | [n] / [denominator]       | [n] / [denominator]       |
|                           | Also under 8.0%: [rate]   | Pooled across 3 hospitals |
| No usable BP: [share]     | Of the over-9.0% rate,    | One stay counts once      |
|                           | no usable result: [share] |                           |
| Contract target: [exhibit]| Contract target: [exhibit]|                           |
+---------------------------+---------------------------+---------------------------+

Trend, January through [close month]
  CBP controlled          [monthly line, higher is better]
  GSD over 9.0%           [monthly line, lower is better]
  CMS816v5                [monthly line, lower is better]

Where to look
  Clinics, CBP and GSD     Five lowest and five highest this month
                           Full clinic list on drill
  Hospitals, CMS816v5      All three, same definition, each with its own denominator

Trust
  Missing discrete results are shown next to the rate they inflate.
  Method: population label, close date, and the measure specification.
```

## How each measure is shown

**CBP.** The tile is the percentage controlled: latest eligible blood pressure in 2026 under 140/90. The denominator is adults who meet the HEDIS population rules in the specification. “No usable BP” is the share of that denominator with no distinct systolic and diastolic the rules can use. Those patients sit inside “not controlled.” The share is on the tile so a documentation gap is not read as a sudden change in control.

**GSD.** The tile leadership acts on is glycemic status over 9.0%, because a missing result counts there. The same tile shows the under 8.0% rate. A result from 8.0% through 9.0% is in neither rate, and hiding the second rate makes that middle group look like failure or success. The over-9.0% tile splits “result over 9.0%” from “no usable result.” Both rates use one denominator and one data method.

**CMS816v5.** The tile is the pooled percentage of qualifying hospitalizations with at least one severe hypoglycemic harm event. Pooled means the sum of numerator hospitalizations over the sum of denominator hospitalizations. An unweighted average of the three hospital rates is not displayed. Each hospital is shown underneath with its own denominator. The page states that one stay counts once. A count of every glucose under 40 mg/dL can exist on drill only, labeled as an internal safety tally, not as CMS816v5.

## Rules that keep the page honest

- **Population label.** If payer membership and dispensing files are loaded, the HEDIS tiles are labeled payer-aligned. If they are not, the tiles are labeled EHR clinic rate. The two labels are never shown as one number.
- **Contract target.** The target slot is filled from the payer exhibit. An empty exhibit leaves the slot blank. No internal goal is drawn on the chart in place of a contract target.
- **CMS816v5 has no target line** unless CMS or the board has adopted one in writing. The direction is stated: lower is better.
- **Monthly close.** The front page updates after the monthly close. A mid-month extract can be used in drill and is labeled preliminary.
- **Small denominators.** A clinic or a hospital with a denominator under 30 displays the count and suppresses the sparkline. The rate remains visible as a fraction so a single event cannot look like a trend.
- **Direction.** Each tile states whether a higher or a lower rate is better. GSD’s two rates state both directions.
- **Unformable denominator.** When the extract cannot build the denominator in the specification, the tile says the rate cannot be calculated and shows the count that failed. It does not display 0% or a stand-in population as the contract rate.

## Drill

From a tile, leadership can open:

- The monthly trend for that measure, with the denominator printed under each point.
- Clinic rates for CBP and GSD, all clinics, sorted by the rate on the tile. GSD drill keeps the split between a result over 9.0% and no usable result.
- Hospital rates for CMS816v5, including the number of numerator stays.
- The method note: measurement year, population label, and a link to the specification section for that measure.

Exclusion lists, value set identifiers, and enrollment-gap detail stay in the specification. They are not on the front page.

## What the page refuses to do

The page does not combine CBP, GSD, and CMS816v5 into one score. The programs, settings, and directions differ. It does not color a cell red or green from a threshold the contract or CMS has not set. It does not show a rate movement in the same month the logic changed, without a note that the definition changed.

## Synthea run

The layout above is the page. This section is the only place it is filled in. The counts come from the Synthea extract profiled in `docs/data-profile.md`. Seed 2026, Massachusetts, history through 13 October 2026. The measurement year is incomplete. The file is a statewide synthetic population, with 946 organizations, so there is no clinic ranking and no three-hospital comparison. No contract target is filled in, because this project has no payer exhibit.

```
Quality performance
Synthea extract, through 13 October 2026
Not a health-system result

+---------------------------+---------------------------+---------------------------+
| CBP                       | GSD                       | CMS816v5                  |
| Rate cannot be calculated | Rate cannot be calculated | Rate cannot be calculated |
| HEDIS · encounter dx      | HEDIS · encounter dx      | CMS eCQM · hospitals      |
|                           |                           |                           |
| 0 patients have the       | 0 patients have two       | 60 adult stays end in     |
| hypertension code on two  | diabetes diagnosis dates  | 2026                      |
| qualifying encounters     | in any non-lab setting    | Glucose under 40 mg/dL: 0 |
| 514 have the condition    | 4 meet diagnosis plus a   | Lowest glucose on those   |
| active in the window      | medication course         | stays: 64.8 mg/dL         |
| Contract target: —        | Contract target: —        | Administration time:      |
|                           |                           | not in the file           |
+---------------------------+---------------------------+---------------------------+
```

The blood-pressure and A1c values that Synthea writes are discrete numbers. The HEDIS denominators still fail, because the diagnosis is stored once, at onset, and is not coded on the later visits. Publishing 0% would read as perfect or as failure, depending on the measure. The tile stays blank and shows the count that failed.

A problem-list recount is in the profile and is labeled as a different measure. It is not placed on these tiles. CMS816v5 is not scored: this file has no glucose under 40 mg/dL, and medication rows are courses rather than administration events.
