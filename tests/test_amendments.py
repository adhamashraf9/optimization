import csv
from dataclasses import asdict
import json
import math
from pathlib import Path
import random
import tempfile
import unittest

from milestone3.search import SAConfig, BudgetEvaluator, solve_sa, random_search, propose, initialize
from milestone3.benchmark import run_benchmark
from milestone3.export import write_run
from tests.test_model import problem


class AmendmentTests(unittest.TestCase):
    def test_cooling_depends_on_evaluations_not_acceptance(self):
        initial=((0.,0.,10.),)
        cfg=SAConfig(budget=7,calibration_samples=2,trace_interval=1)
        for bad_every in (1,2,100):
            calls=[0]
            def neighbor(*args):
                calls[0]+=1
                return ((200.,0.,10.),) if calls[0]%bad_every==0 else initial
            r=solve_sa(problem(),cfg,0,initial=initial,neighbor=neighbor)
            search=[t for t in r.trace if t.phase=='search']
            self.assertEqual(r.phase_counts,{'initialization':1,'calibration':2,'search':4})
            self.assertEqual([t.evaluation for t in search],[4,5,6,7])
            for t,want in zip(search,[1.,.2154434690031884,.0464158883361278,.01]):
                self.assertAlmostEqual(t.temperature,want)
            self.assertEqual(r.evaluations,7)
        single=solve_sa(problem(),SAConfig(budget=2,trace_interval=1),0,initial=initial)
        self.assertEqual(single.phase_counts['calibration'],0)
        self.assertEqual(single.trace[-1].temperature,single.initial_temperature)

    def test_exhausted_initial_budget_is_explicit_failure(self):
        for solver in (solve_sa,random_search):
            r=solver(problem(),SAConfig(budget=1),0)
            self.assertEqual(r.status,'insufficient_search_budget')
            self.assertEqual(r.phase_counts['search'],0)
            self.assertFalse(any(t.phase=='search' for t in r.trace))

    def test_failed_evaluation_is_not_counted_as_completed(self):
        controller=BudgetEvaluator(problem(),SAConfig(budget=2))
        with self.assertRaises(ValueError): controller.evaluate(((0.,0.,math.nan),),'search')
        self.assertEqual(controller.used,0)

    def test_cheap_checks_are_separate(self):
        p=problem(bounds=((0.,0.),(0.,0.),(10.,10.)),r_comm=100.)
        init=initialize(p,random.Random(0),10)
        self.assertEqual(init.attempts,1)
        self.assertEqual(init.checks,4)  # three bounds checks plus one anchor distance
        r=solve_sa(p,SAConfig(budget=8),0)
        self.assertEqual(r.initialization_checks,4)
        self.assertEqual(sum(r.phase_counts.values()),8)

    def test_mixture_reproducible_and_draw_order(self):
        p=problem(); x=((1.,2.,20.),)
        class FixedRNG:
            def __init__(self,select): self.select=select; self.calls=[]
            def random(self): self.calls.append('operator'); return self.select
            def randrange(self,n): self.calls.append('uav'); return 0
            def uniform(self,a,b): self.calls.append('offset'); return .5
        translation=FixedRNG(.79)
        altitude=FixedRNG(.8)
        self.assertEqual(propose(p,x,translation,.05,'mixed'),((6.,7.,20.75),))
        self.assertEqual(translation.calls,['operator','uav','offset','offset','offset'])
        self.assertEqual(propose(p,x,altitude,.05,'mixed'),((1.,2.,20.75),))
        self.assertEqual(altitude.calls,['operator','uav','offset'])
        cfg=SAConfig(budget=100,operator='mixed')
        self.assertEqual(solve_sa(p,cfg,101).best_positions,solve_sa(p,cfg,101).best_positions)

    def test_oracle_cost_is_separate(self):
        r=run_benchmark(100,(1,2))
        self.assertEqual(r['oracle_evaluations'],16)
        self.assertEqual(r['oracle_feasible_placements'],12)
        self.assertEqual(r['oracle_optimal_score'],-16.)
        self.assertGreaterEqual(r['oracle_runtime_seconds'],0.)
        self.assertTrue(all(t['evaluations']==100 for t in r['trials']))
        self.assertTrue(all(t['elapsed_seconds']>=0 for t in r['trials']))

    def test_required_exports_and_metrics(self):
        p=problem(2); cfg=SAConfig(budget=12,trace_interval=1)
        r=solve_sa(p,cfg,0)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'run'
            write_run(path,p,cfg,'sa_feasible',0,r)
            for name in ('configuration.json','metrics.json','initial_placement.csv',
                         'final_placement.csv','initial_edges.csv','final_edges.csv',
                         'convergence.csv','targets.csv'):
                self.assertTrue((path/name).exists(),name)
            metrics=json.loads((path/'metrics.json').read_text())
            self.assertEqual(metrics['total_evaluations'],12)
            self.assertEqual(metrics['initialization_evaluations']+metrics['calibration_evaluations']+
                             metrics['search_evaluations'],12)
            self.assertEqual(metrics['neighbor_proposals'],11)
            self.assertEqual(metrics['infeasible_evaluated_proposals'],r.proposals-r.feasible_proposals)
            with (path/'initial_placement.csv').open() as f: rows=list(csv.DictReader(f))
            self.assertEqual([(float(v['x']),float(v['y']),float(v['z'])) for v in rows],list(r.initial_positions))
            self.assertTrue(all(v['gcs_reachable']=='1' for v in rows))
            with (path/'final_edges.csv').open() as f: edges=list(csv.DictReader(f))
            self.assertEqual(len(edges),len(r.best_evaluation.edges))
            self.assertTrue(all(v['eligible']=='1' and v['gcs_reachable']=='1' for v in edges))
            self.assertTrue(all(0 <= float(v['distance']) <= p.r_comm for v in edges))

    def test_failed_initialization_has_no_fabricated_placement(self):
        p=problem(r_comm=1.); cfg=SAConfig(budget=5,max_initialization_attempts=3)
        r=solve_sa(p,cfg,0)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'failure'; write_run(path,p,cfg,'sa_feasible',0,r)
            self.assertEqual(json.loads((path/'metrics.json').read_text())['status'],'initialization_failed')
            self.assertFalse((path/'initial_placement.csv').exists())


if __name__=='__main__': unittest.main()
