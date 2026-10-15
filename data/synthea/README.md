# Synthea extract

This is the analysis dataset for the profile in `docs/data-profile.md`. The patients are synthetic. Synthea generated them. They are not records from a health system, a payer, or CMS.

The run used Synthea `d9d07a6`, seed 2026, clinician seed 2026, reference date 13 October 2026, state Massachusetts, and 10 years of history. The generator was asked for 2,000 living patients. The patient file contains 2,285 people, living and deceased. Clinical rows stop on 13 October 2026, so measurement year 2026 is incomplete.

The CSV and FHIR files are produced locally and are gitignored. An untouched clone for the Riverbend study lives in `data_raw/synthea/`. Do not clean either copy in place. The source note for that study is `docs/data-sources.md`. `observations.csv` is about 270 MB, and `claims_transactions.csv` is about 890 MB. The profile does not read claims, claim transactions, or imaging studies. The metadata JSON in `metadata/` is small and records the seed.

Java on this machine is Homebrew OpenJDK, which is keg-only. The binary that completed the run was `/opt/homebrew/opt/openjdk/bin/java`. Any Java 17 or newer on the path will do. The jar belongs in `tools/synthea-with-dependencies.jar` and is also gitignored.

From the repository root:

```
java -jar tools/synthea-with-dependencies.jar -s 2026 -cs 2026 -r 20261013 -p 2000 \
  --exporter.csv.export=true --exporter.fhir.export=false --exporter.ccda.export=false \
  --exporter.baseDirectory=data/synthea --exporter.years_of_history=10 \
  --generate.thread_pool_size=1 Massachusetts
python3 src/profile_synthea.py
```

The same seed and reference date reproduce the population. `src/profile_synthea.py` writes `docs/data-profile.md` and `outputs/synthea_results.json`.
