# Outputs

`synthea_results.json` is the machine-readable summary of the Synthea profile. `docs/data-profile.md` is the narrative from the same run. Those two files are the analysis output.

`measure_results.json` and `hand_built_profile.md` are the earlier summary of the hand-built files in `data/synthetic/`. They are not the analysis result. `src/profile_measures.py` refreshes those two files only.
