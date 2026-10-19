import csv
import json
from pathlib import Path
import tempfile
import unittest
from milestone3.cases import make_case
from milestone3.search import SAConfig, SearchResult, solve_sa
from milestone3.experiments import run_comparison, summarize, run_study, sensitivity_configs
from milestone3.export import write_run


class ExperimentTests(unittest.TestCase):
    def test_paired_budget_and_summary(self):
        runs = run_comparison(make_case('small',101),SAConfig(budget=40),(0,1))
        self.assertEqual(len(runs),4)
        self.assertTrue(all(r.evaluations == 40 for _,_,r in runs))
        for seed in (0,1):
            initial = [r.initial_positions for _,s,r in runs if s == seed]
            self.assertTrue(all(p == initial[0] for p in initial))
        summary = summarize(runs)
        self.assertEqual(len(summary),2)
        self.assertTrue(all(s['successful_runs']==2 for s in summary))

    def test_failed_and_single_run_statistics(self):
        fail = SearchResult(phase_counts={'initialization':0,'calibration':0,'search':0})
        s = summarize([('sa_feasible',0,fail)])[0]
        self.assertEqual(s['feasible_run_rate'],0)
        self.assertIsNone(s['mean_fitness'])
        r = solve_sa(make_case('small',101),SAConfig(budget=2),0)
        s = summarize([('sa_feasible',0,r),('sa_feasible',1,fail)])[0]
        self.assertEqual(s['feasible_run_rate'],.5)
        self.assertEqual(s['std_fitness'],0)
        self.assertEqual(s['mean_fitness'],r.best_evaluation.fitness)

    def test_export_roundtrip_failure_and_overwrite(self):
        p,cfg = make_case('small',101),SAConfig(budget=20)
        r = solve_sa(p,cfg,0)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'space in path'
            write_run(path,p,cfg,'sa_feasible',0,r)
            data=json.loads((path/'result.json').read_text())
            self.assertEqual(data['best_evaluation']['fitness'],r.best_evaluation.fitness)
            with (path/'positions.csv').open() as f:
                self.assertEqual(len(list(csv.DictReader(f))),4)
            self.assertTrue((path/'initial_positions.csv').exists())
            with self.assertRaises(FileExistsError): write_run(path,p,cfg,'sa_feasible',0,r)
            failed = Path(d)/'failure'
            write_run(failed,p,cfg,'sa_feasible',1,SearchResult())
            self.assertFalse((failed/'positions.csv').exists())
            self.assertIn('null',(failed/'result.json').read_text())

    def test_study_and_sensitivity_configuration(self):
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/'study'
            run_study(output,[make_case('small',101)],
                      [('sa_feasible',SAConfig(budget=5))],(0,1),progress=False)
            manifest=json.loads((output/'manifest.json').read_text())
            self.assertTrue(manifest['complete'])
            with (output/'runs.csv').open() as f: self.assertEqual(len(list(csv.DictReader(f))),2)
            with self.assertRaises(FileExistsError):
                run_study(output,[],[],(),progress=False)
        configs=sensitivity_configs(SAConfig(budget=10))
        self.assertEqual(len(configs),5)
        self.assertEqual({(c.temperature_multiplier,c.move_scale) for _,c in configs},
                         {(1.,.05),(.5,.05),(2.,.05),(1.,.025),(1.,.10)})


if __name__ == '__main__': unittest.main()
