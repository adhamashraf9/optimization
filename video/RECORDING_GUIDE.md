# Milestone 3 narrated demonstration outline

This is an outline, not an actual recording. Target duration: 3–5 minutes.

## 0:00–0:35 — Problem and model

Show the repository and explain: choose 3D UAV positions to cover weighted static
targets, limit hovering power, avoid collisions, and preserve a multi-hop GCS link.
Show `milestone3/model.py`. State that M2 equations are preserved and all new Python
code uses the standard library. Power is measured in watts, not joules.

## 0:35–1:10 — Verification

Run `python -B -S -m unittest discover -s tests -v` and show its actual outcome.
Explain the 63 historical reference placements and the exhaustive 16-placement
grid benchmark. Show `results/final_v1_benchmark/benchmark.json`: its optimum is certified
only on that finite domain. Do not describe continuous SA as globally optimal.

## 1:10–2:00 — Live seeded search

Run a fresh output directory, for example:

```powershell
python -B -S -m milestone3 demo --seed 0 --budget 2000 --output results/recording-demo
```

Explain the 80% translation / 20% altitude one-UAV mixture, reflected flight bounds, feasible-only rejection,
Metropolis acceptance and cooling. Show result.json, actual feasibility and exact
evaluation count. Explain that calibration and initial scoring consume budget.

## 2:00–3:00 — MATLAB deployment and convergence

After successfully running MATLAB scripts, display the recorded initial placement
and best feasible placement, coverage circles, weighted targets, GCS and saved links.
Show convergence and temperature. Describe target size, coverage colors, coordinate
units, and multi-hop paths. If MATLAB has not run, resolve that before recording;
do not present a proposed figure as a generated result.

## 3:00–4:15 — Comparisons and sensitivity

Show the frozen configuration hash and `results/final_v1` data. Main comparison:
three sizes, ten seeds, budgets 2,000/4,000/5,000. Compare feasible SA and uniform
random search; describe all observed results, including a case where SA loses.
Sensitivity: same medium instance, five OFAT configurations, five seeds each.
Challenging cases: clustered and separated, five seeds per method. Total 105 runs.
Use actual summary.csv figures. Explain
the difference between returned-solution feasibility and feasible proposal rate.
Use mean and sample standard deviation, not just the best-seed deployment plot.

## 4:15–4:45 — Limitations and deliverables

Mention static targets, idealized radio range, no interference, fixed fleet size,
and stochastic local search. Altitude-only cannot reposition UAVs horizontally.
Point to CSV/JSON inputs and metadata for reproduction. State that the grid optimum
does not certify larger continuous cases and no numerical literature superiority is
claimed. Finish with the tested code, actual figures, and completed course report.

## Recording checklist

- Use a new output directory and show successful command exit/output.
- Confirm the unit-test count matches the latest run, not an earlier script.
- Keep terminal text and MATLAB legends readable.
- Record narration and actual code execution; review the saved video afterward.
- Transfer report material into the course template and include figure captions.
