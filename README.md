# Team 47 — Milestone 3 submission

**Cooperative UAV Placement for Disaster-Zone Coverage**  
MCTR 1021 — Optimization Techniques for Multi-Cooperative Systems

## Start here

1. Extract the entire ZIP. Do not run files from inside the ZIP preview.
2. Open a terminal in the extracted `Team47_Milestone3_Submission` folder: this is the folder containing this README, `milestone3`, `cases` and `verify_submission.py`.
3. Use Python 3.9 or newer. No pip install, third-party Python package or optimization toolbox is required. The packaged code was exercised on Python 3.13.2; other supported versions were not executed here.
4. Read `report/Team47_Milestone3_Report.pdf` and open the supplied figures under `figures/submitted/`.
5. Run the verification command below.

```text
python -B -S verify_submission.py
```

On macOS/Linux, use `python3` if `python` is not available. On Windows, `py -3` can replace `python`. `-S` disables third-party site packages; `-B` avoids creating bytecode caches. The verifier uses the same interpreter for every subprocess.

**Expected verification:** file hashes match, 43 unit tests pass, and the frozen audit verifies 60 main, 25 sensitivity and 20 challenging runs. The verifier also runs a new 2,000-evaluation medium-case demonstration and a ten-seed exact-grid benchmark in a temporary folder, audits the demonstration exports, and checks the benchmark optimum −16. Temporary smoke results are removed automatically; the submitted final data is not changed.

## Run a demonstration and keep its output

Enter this as one command:

```text
python -B -S -m milestone3 demo --case cases/medium.json --budget 2000 --seed 0 --output results/demo-new
```

Look in `results/demo-new/medium/sa_feasible/seed_0/`. `metrics.json` contains feasibility and evaluation accounting; `initial_placement.csv` and `final_placement.csv` contain coordinates. **Final placement means the best feasible incumbent**, not the last visited state. `convergence.csv` contains sampled progress. Existing output directories are deliberately rejected: use `results/demo-new-2` for a second run.

Other commands:

```text
python -B -S -m milestone3 --help
python -B -S -m unittest discover -s tests -v
python -B -S -m milestone3.final_experiments verify
python -B -S -m milestone3 benchmark --budget 500 --seeds 0:10 --output results/benchmark-new
```

`0:10` denotes seeds 0 through 9. Invalid arguments and unsuccessful studies return a nonzero exit code. A failed initializer does not prove mathematical infeasibility.

## Generate MATLAB figures

The 27 supplied PNG figures are already included, so MATLAB is unnecessary to inspect the results. To regenerate figures, use base MATLAB R2020b or later, with no toolboxes:

1. Open `run_matlab_figures.m` from the extracted submission.
2. Click Run. The launcher locates the study data relative to itself.
3. Wait for the output-folder message and open the new `figures/<timestamp>/` folder.

Optional import regression check, from this folder as MATLAB's Current Folder:

```matlab
addpath('matlab');
test_plot_import(fullfile('results','final_v1','main'));
```

The original MATLAB-generated PNGs were supplied by the team and incorporated into the report. Their copying and report rendering were checked; MATLAB was not rerun during packaging, and its release was not independently recorded. Regeneration produces PNG and PDF figures in a fresh folder without overwriting submitted images.

## Reproduce the full final study

The saved `final_v1` study is immutable: do not run its `run` command into its existing output paths. Use these commands, each on one line, to create an independent version:

```text
python -B -S -m milestone3 pilot --budget 1000 --seeds 0 --output results/reproduction/pilot
python -B -S -m milestone3.final_experiments freeze --version reproduction_v1 --config experiments/reproduction_v1.json --pilot results/reproduction/pilot
python -B -S -m milestone3.final_experiments run --config experiments/reproduction_v1.json
python -B -S -m milestone3.final_experiments verify --config experiments/reproduction_v1.json
```

For another reproduction, choose a new pilot directory, configuration filename and version. Solver timings depend on machine and load. The original total solver runtime was approximately 113 seconds; this excludes export, plotting, the pilot, benchmark and audit.

## Study and interpretation

| Study | Instances | Budget per run | Seeds | Runs |
|---|---|---|---|---:|
| Main | 4/10, 8/50, 16/150 UAVs/targets | 2,000 / 4,000 / 5,000 | 100–109, two methods | 60 |
| Sensitivity | Same 8/50 medium instance | 4,000 | 200–204, five settings | 25 |
| Challenging | Clustered and separated 8/50 | 4,000 | 300–304, two methods | 20 |

The total is 105 runs and 400,000 complete optimizer evaluations. SA uses 80% one-UAV 3D moves and 20% altitude-only moves, reflected boundaries, scale 0.05, calibrated temperature and geometric cooling to 1% of initial temperature. Initialization scoring and up to 100 calibration evaluations count toward the budget. Cheap initialization checks are separate. SA and random search start from seed-paired feasible placements.

Fitness is maximized: `weighted coverage - 0.1 * power - 10000 * violation`. Power is watts, not joules. Targets contribute priority once, even under overlapping footprints. All saved incumbents satisfy bounds, separation and multi-hop GCS connectivity. SA improves mean fitness on medium, large, clustered and separated cases, but loses on the small case. Best-run deployment pictures are selected examples; tables use all runs. The custom exact grid certifies only its discrete domain, not a continuous global optimum or a published literature benchmark.

## Package contents

| Path | Purpose |
|---|---|
| `milestone3/` | Frozen standard-library implementation, with inline comments and docstrings |
| `cases/` | Exact target coordinates, priorities and model parameters |
| `tests/` | 43 tests plus historical reference fixture |
| `experiments/` | Frozen configuration, SHA-256 and pre-run acceptance evidence |
| `results/final_v1/` | Complete 105-run results, traces and summaries |
| `results/final_v1_benchmark/` | Exact-grid benchmark and ten SA trials |
| `results/amendment_pilot/` | Six-run pre-freeze pilot evidence |
| `matlab/`, `run_matlab_figures.m` | Figure generation and import checks |
| `figures/submitted/` | Team-supplied MATLAB PNGs |
| `report/` | Final PDF and complete editable LaTeX ZIP |
| `docs/CODE_WALKTHROUGH.md` | Explanation of each computational component |
| `docs/REQUIREMENTS_CHECKLIST.md` | Mapping to the actual milestone brief |
| `verification/` | Packaging verification logs |
| `video/` | Recording instructions; add the actual narrated video |
| `MANIFEST.sha256.json` | SHA-256 inventory for the assembled files |

Frozen source bytes are preserved so their hashes continue to bind the results to the implemented algorithm. No external dependency is needed to run the M3 code. The historical NumPy-based M2 script and unrelated exploratory runs are excluded; the standard-library M3 model and its reference fixture are included.

## Before uploading

The **narrated screen-recording video is still required** unless supplied separately. A written outline is not a recording. Add it to `video/` or upload it separately according to the portal. Review your team details and the portal's file naming/size instructions. The brief specifies 19 October 2026 at 23:59.

Do not edit frozen source files or case data to make hash checks pass. If you intentionally change the algorithm, use a new experiment version and new results, and update the report accordingly.
