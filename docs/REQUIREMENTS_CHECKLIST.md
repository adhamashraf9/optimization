# Milestone 3 requirements and evidence

Basis: the supplied MCTR 1021 Milestone 3 brief. The final report is an adaptation of the team's supplied GUC LaTeX template.

| Requirement | Evidence in this package | Status |
|---|---|---|
| Implement SA for the project problem | `milestone3/model.py`, `milestone3/search.py`; report Chapters 3–4 | Included |
| Explain problem-specific algorithm choices | Pseudocode, initializer, operator mixture, reflection, calibration, cooling and budget accounting; code walkthrough | Included |
| Different sizes and complexity | Small/medium/large, clustered and separated inputs and saved runs | Included |
| Visualize solutions | 27 supplied MATLAB PNGs; report includes 22 figures; plotting source included | Included |
| Validate results | 43 tests, 63 historical reference evaluations, exact 16-placement benchmark, frozen 105-run artifact audit | Included |
| Discuss numerical and graphical results | Report tables, paired differences, convergence, power/coverage tradeoffs, failure of SA to dominate on the small case | Included |
| Discuss algorithm parameters | Five-setting, two-parameter sensitivity study with five seeds | Included |
| Runnable code without packages/toolboxes | Python standard library for M3; base MATLAB only for plots; no pip step | Included; packaged copy verified as recorded in verification logs |
| Clear code documentation | Inline comments/docstrings plus function-by-function `CODE_WALKTHROUGH.md` and README | Included |
| Progress report in supplied template | `report/Team47_Milestone3_Report.pdf` and complete editable LaTeX ZIP | Included |
| Code for cases and results | Implementation, serialized cases, generation functions, frozen config and complete final artifacts | Included |
| Narrated video of code running and visualized results | Recording outline in `video/`; actual recording not provided at assembly | **Outstanding** |

## Validation scope

The exact benchmark is a custom restricted form of the UAV problem with a proven optimum, not a reproduction of published literature. The report states this explicitly. The brief requests comparison with literature or known benchmark problems; acceptance of a custom exact benchmark remains a course interpretation unless already confirmed with the teaching team. Do not claim a published comparison that was not performed.

The final report and figures have been prepared; this does not by itself complete the narrated-video deliverable. Add the actual recording before claiming that every submission item is complete.

## Preservation and portability

Frozen source/case bytes and existing results have not been edited. The package excludes exploratory runs, caches, local compiler binaries and the historical NumPy-dependent M2 script. M2 reference fixtures remain included and require no NumPy. New demonstration and reproduction runs must use new output paths.

The manuscript uses the team's provided names and IDs. The team should confirm these and follow any portal-specific naming, upload-size and file-format rules. Deadline stated in the brief: 19 October 2026, 23:59.
