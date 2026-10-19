# Code walkthrough

This guide complements the inline comments and docstrings in the frozen source. The source is preserved byte for byte so the final experiment's source hashes remain valid.

## Execution flow

`__main__.py` parses arguments → `cases.py` loads a validated problem → `experiments.py` selects methods and seeds → `search.py` generates candidates → `model.py` scores candidates through `BudgetEvaluator` → `export.py` saves cached results → `validation.py` audits the saved artifacts. `final_experiments.py` wraps this flow with frozen definitions and source/case hashes.

## model.py — problem definition and scoring

- `finite` and `coordinates` reject malformed or nonfinite numeric data.
- `Problem` is the validated case definition. It stores fleet size, targets, positive priorities, bounds, radio range, separation and power parameters.
- `Evaluation` stores coverage, power, individual violation terms, feasibility, fitness, coverage flags and graph edges.
- `validate_positions` checks the fleet shape and coordinate types.
- `evaluate` computes footprint membership and unique weighted coverage, sums hovering power, measures bounds and separation violations, builds eligible communication edges, and traverses the graph from the GCS. Disconnected UAV count is the connectivity penalty. Fitness uses the original coefficients; feasibility requires zero violation.

## search.py — construction and optimization

- `SAConfig` validates budgets, move scale, temperature settings, operator and constraint mode.
- `BudgetEvaluator` is the single gateway for complete algorithmic evaluations. Its phase counts separate initial scoring, calibration and search. Failed evaluator calls do not increment completed-call counts.
- `reflect` folds an out-of-bounds coordinate back into its interval without resampling.
- `propose` chooses the move type and UAV, then draws an offset for each moved axis. In the mixed operator, 80% of proposals move x/y/z and 20% only z.
- `accept` implements the maximizing Metropolis rule: improvements and ties are accepted; a loss can be accepted with probability `exp(delta / temperature)`.
- `initialize` incrementally adds UAVs near the GCS or an already connected UAV. It checks bounds, anchor distance and separation before appending a point, with a bounded attempt count and partial restarts. These local checks are counted independently of full scoring.
- `TraceRow` describes sampled progress. `SearchResult` distinguishes initial, best feasible, best penalized and last visited states and stores all counters.
- `_run` owns one seeded RNG and the budget. It constructs and scores an initial fleet, calibrates temperature around that unchanged fleet, executes budgeted proposals, tracks the best feasible candidate, and records final accounting. The local `track` function maintains archives; `record` samples traces. Infeasible search proposals still consume evaluations and advance cooling.
- `solve_sa` and `random_search` are public entry points. The random baseline uses the same initializer but independently samples whole fleets for its remaining budget.

## cases.py — inputs

`make_case` generates uniform or clipped clustered targets and priority weights with a dedicated layout seed. `save_case` writes a versioned JSON schema without overwriting; `load_case` validates that schema; `generate_cases` creates the named cases. Final experiments load the saved case definitions rather than silently regenerating layouts.

## experiments.py — repeated runs and statistics

`comparison_configs` selects feasible SA and random search. `sensitivity_configs` creates the five one-factor-at-a-time settings. `run_comparison` pairs methods and seeds. `summarize` computes means and sample standard deviations for successful feasible incumbents, keeping failure rates and runtime accounting explicit. `run_study` creates a new output directory, writes an incomplete manifest first, runs the configured cases/methods/seeds, exports each run, then saves aggregate CSVs and marks the manifest complete. Frozen runs supply guards around each solver invocation.

## export.py — output files

`write_json` and `write_csv` create files exclusively. `placement_files` writes coordinates, footprint radii, target coverage and communication edges. `write_run` exports the exact case/configuration, interpreter metadata, counters, calibration losses and traces. It uses cached evaluations: serialization does not consume optimizer budget. Required names and compatibility aliases contain equivalent data. No placement is fabricated after initialization failure.

## benchmark.py — exact reference

`tiny_instance` specifies two UAVs and four sites. `enumerate_grid` exhaustively scores all 16 ordered fleets and counts oracle work separately. `grid_neighbor` confines SA to the same domain. `run_benchmark` compares each run with the exact optimum and exports its absolute gap, hit flag, budget and runtime. This certifies the finite benchmark only.

## validation.py — consistency audit

`verify_study` checks manifest completeness, unique run keys, path containment, case/config/seed metadata, budget totals, traces and cooling, required aliases, saved initial/best feasibility, target flags, edge geometry and aggregate statistics. It recomputes through the same model evaluator, outside optimizer budgets, so it checks consistency rather than independent physical model validity.

## final_experiments.py — frozen final study

`build_configuration` defines the 105-run scope, budgets, RNG rules and source/case hashes. `freeze` writes the configuration and digest without overwriting. `validate_freeze` detects changes to the config, algorithm version, sources or cases. `verify_final_study` binds manifests and run cases to the frozen definitions. `run_final` checks destinations and runs each study with before/after guards, then audits results. The command-line interface exposes `freeze`, `run` and `verify`.

## __main__.py and __init__.py

`parse_seeds` accepts unique comma-separated seeds or a half-open range. `main` validates arguments and dispatches demo, pilot, comparison, sensitivity or benchmark workflows. It returns failure for unsuccessful studies. `__init__.py` identifies algorithm version 1.1.0.

## MATLAB and tests

`check_plot_inputs.m` validates imported CSV fields and referenced data. `plot_milestone3.m` plots saved deployments, footprints, eligible edges, fitness/temperature traces, statistical comparisons and descriptive size trends. `test_plot_import.m` checks imports including paths containing spaces. The launcher finds the package root automatically and selects a fresh output directory. Python tests cover model boundaries and reference parity, neighborhood behavior, cooling, budgets, deterministic seeds, exports, exact benchmarking and frozen-input tampering.
