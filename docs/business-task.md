# Business task

**Portfolio note.** Independent demonstration for Riverbend Community Health Network, a fictional nonprofit network of safety-net clinics. The patients in the extract are synthetic. Nothing in this case is a clinical finding about real people, and nothing here is an official HEDIS or CMS submission.

**Date.** 14 October 2026.
**From.** Research data analytics.
**For.** Dr. Maya Okafor, Director of Clinical Quality, and Tom Reyes, Research Operations Manager.

## The task

Riverbend needs a patient-level dataset, and two quality rates, before a quality-improvement study can start. The rates are blood pressure control and diabetes glycemic status, overall and by clinic, each with a confidence interval. The dataset has to be reproducible from the Synthea extract already generated for this project, and every cleaning decision has to be logged. Each rate has to say where it follows a published specification and where it simplifies one, because the licensed HEDIS specification is not what this study implements.

The decision this dataset supports is whether the research team has a base it can defend: a known population, a known measurement period, and rates whose uncertainty is visible when a clinic is small.

## Who uses it

| Person | What they need in order to trust the work |
| --- | --- |
| Dr. Maya Okafor, Director of Clinical Quality | The denominator, the numerator, the exclusions, and a plain statement of each simplification. She has to be able to explain a clinic rate to a manager without calling it HEDIS. |
| Tom Reyes, Research Operations Manager | The source, the license, the generator seed, the data dictionary, the cleaning log, and the SQL that builds the tables. Another analyst should be able to rebuild the file from those pieces. |
| Clinic managers | The rate, the network comparison, and the interval. A small clinic whose interval crosses the network rate is not a performance ranking. |
| The research team that inherits the file | One row per patient for the measurement period, with the keys and code systems written down, so a later study does not have to rediscover the joins. |

## What this case is not

The specifications, leadership dashboard, and data-gap memo already in this repository answer a different assignment: contract and hospital reporting for an illustrative regional health system. This case is the research dataset underneath a quality study. The two measures overlap in subject, blood pressure and glycemic status. The population, the audience, and the claim do not. This study will not report CMS816v5, and it will not label a simplified rate as HEDIS.

## Boundary already known from the extract

The Synthea file on disk is Massachusetts, seed 2026, reference date 13 October 2026, 2,285 patients. Measurement year 2026 stops on 13 October. Hypertension and type 2 diabetes are stored once, at onset. A literal reading of the published encounter rules produces an empty blood-pressure denominator and four diabetes patients on the diagnosis-plus-dispense path. The study definitions have to record that limit and the simplification used to form a rate. They do not get to hide it inside a percentage.
