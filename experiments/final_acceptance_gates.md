# Final v1 acceptance gates (before experiment launch)

Approved amendments supersede the earlier 270-run exploratory design. Source
version: 1.1.0. All gates below were checked before freezing final settings.

- [x] Cooling follows evaluated search-candidate count, including infeasible
  rejections; tests vary rejection rates and cover zero/one search evaluations.
- [x] Full evaluation counts are centralized; failed evaluation calls do not
  increment counters. Initialization/calibration/search sum to the declared budget.
- [x] Cheap initialization geometry checks and construction attempts are separate.
- [x] Calibration reserves one search evaluation; budget one reports explicit
  `insufficient_search_budget`, excluded from successful-run statistics.
- [x] Oracle counts/runtime/feasible placements/optimum are separate from SA cost.
- [x] Negative, zero, NaN and infinite target weights are rejected.
- [x] Exact original initialization and best feasible placement are exported,
  with GCS reachability and every eligible communication edge and its distance.
- [x] The approved simpler operator mixture is frozen: 80% one-UAV 3D translation,
  20% altitude-only, 0% coordinated. Exact RNG consumption is documented in config.
- [x] Main 60, sensitivity 25, challenging 20: total 105 runs. Sensitivity is five
  distinct OFAT configurations on the same medium instance. No outcome-based tuning.
- [x] Configuration/case/source hashes, run metadata and before/after-run guards
  are implemented and tested, including tampering and incomplete-run handling.
- [x] `python -B -S -m unittest discover -s tests -v`: 43 tests passed in 1.691 s.
  Tests use only Python's standard library; temporary-file access was approved.
- [x] Independent read-only review found no Critical/Important findings. Its minor
  request for source-hash and run-guard regressions was implemented and passed.
- [x] Runtime pilot completed, seed 0, 1,000 evaluations per case. Solver seconds:
  small 0.106, medium 0.239, large 0.765, clustered 0.194, separated 0.388,
  historical reference 0.109. Proposed budgets are practical; retain 2,000/4,000/
  5,000 for small/medium/large and 4,000 for sensitivity/challenging cases.

Pilot evidence is in `results/amendment_pilot`. No budget revision was needed.
Challenging runs use seeds 300–304, distinct from main 100–109 and sensitivity
200–204. Earlier `results/comparison` and `results/sensitivity` remain exploratory.
Freeze command must complete before the run command; its `.sha256` sidecar records
the exact frozen bytes. If any source/settings need correction later, use a new
configuration version and result directory.

MATLAB runtime and rendered-figure checks remain outstanding because MATLAB is
unavailable. This does not change any Python computation or acceptance gate above.
