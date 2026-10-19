import json
from pathlib import Path
import tempfile
import unittest
from milestone3.benchmark import tiny_instance, enumerate_grid, grid_neighbor, run_benchmark
from milestone3.cases import make_case, save_case, load_case, generate_cases
from milestone3.search import SAConfig, solve_sa


class BenchmarkCaseTests(unittest.TestCase):
    def test_exact_grid_optimum(self):
        p,sites,initial = tiny_instance()
        positions,score,count = enumerate_grid(p,sites)
        self.assertEqual(count,16)
        self.assertEqual(score.coverage,5)
        self.assertEqual(score.power,210)
        self.assertEqual(score.fitness,-16)
        self.assertTrue(score.feasible)
        for seed in range(10):
            r = solve_sa(p,SAConfig(budget=500),seed,neighbor=grid_neighbor(sites),initial=initial)
            self.assertTrue(all(x in sites for x in r.best_positions))
            self.assertLessEqual(r.best_evaluation.fitness,score.fitness+1e-10)
            self.assertEqual(r.evaluations,500)
            self.assertEqual(r.best_evaluation.fitness,-16)

    def test_benchmark_records_gaps(self):
        report = run_benchmark(100,(0,1))
        self.assertEqual(report['oracle_evaluations'],16)
        self.assertEqual(len(report['trials']),2)
        self.assertTrue(all(t['absolute_gap'] >= 0 for t in report['trials']))

    def test_case_roundtrip_and_determinism(self):
        for name,n,m in [('small',4,10),('medium',8,50),('large',16,150),
                         ('clustered',8,50),('separated',8,50),('tuning',8,50)]:
            p = make_case(name,101)
            self.assertEqual(p,make_case(name,101))
            self.assertEqual((p.num_uavs,len(p.targets)),(n,m))
            with tempfile.TemporaryDirectory() as d:
                path=Path(d)/'case.json'
                save_case(p,path)
                self.assertEqual(load_case(path),p)
                self.assertEqual(load_case(path).metadata,p.metadata)
        with self.assertRaises(ValueError): make_case('unknown',0)

    def test_malformed_case_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'case.json'
            path.write_text('{"schema_version":99}')
            with self.assertRaises(ValueError): load_case(path)
            with self.assertRaises(FileExistsError): save_case(make_case('small',0),path)


if __name__ == '__main__': unittest.main()
