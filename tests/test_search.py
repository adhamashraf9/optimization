import math
import random
import unittest
from dataclasses import asdict, replace
from unittest.mock import patch
from milestone3.model import evaluate
from milestone3.search import (SAConfig, BudgetEvaluator, reflect, propose, accept,
                               initialize, solve_sa, random_search)
from tests.test_model import problem


class SearchTests(unittest.TestCase):
    def test_reflection(self):
        self.assertEqual(reflect(37., 0., 10.), 3.)
        self.assertEqual(reflect(-23., 0., 10.), 3.)
        self.assertEqual(reflect(500., 4., 4.), 4.)

    def test_moves(self):
        p = problem(2)
        x = ((0., 0., 10.), (20., 0., 20.))
        for operator in ('3d', 'altitude'):
            y = propose(p, x, random.Random(2), .3, operator)
            self.assertEqual(sum(a != b for a, b in zip(x, y)), 1)
            self.assertTrue(all(lo <= v <= hi for pos in y for v, (lo, hi) in zip(pos,p.bounds)))
            if operator == 'altitude':
                self.assertEqual([p[:2] for p in x], [p[:2] for p in y])
        self.assertEqual(x[0], (0., 0., 10.))

    def test_metropolis(self):
        class RNG:
            def __init__(self, value): self.value = value
            def random(self): return self.value
        self.assertTrue(accept(0., 1., RNG(.99)))
        self.assertTrue(accept(-1., 1., RNG(.2)))
        self.assertFalse(accept(-1., 1., RNG(.9)))
        with self.assertRaises(ValueError): accept(1., 0., RNG(.1))

    def test_initialization_finite_and_feasible(self):
        p = problem(4, r_comm=40., d_min=5.)
        result = initialize(p, random.Random(0), 1000)
        self.assertTrue(evaluate(p, result.positions).feasible)
        failure = initialize(problem(r_comm=1.), random.Random(0), 50)
        self.assertIsNone(failure.positions)
        self.assertLessEqual(failure.attempts, 50)

    def test_budget_guard(self):
        b = BudgetEvaluator(problem(), SAConfig(budget=1))
        b.evaluate(((0.,0.,10.),), 'initialization')
        with self.assertRaises(RuntimeError): b.evaluate(((0.,0.,10.),), 'search')
        self.assertEqual(b.used, 1)

    def test_initializer_accepts_feasible_fixed_axes(self):
        for bounds in [((-20.,20.),(0.,0.),(10.,20.)),
                       ((0.,0.),(0.,0.),(10.,10.))]:
            p=problem(bounds=bounds,r_comm=100.)
            self.assertTrue(evaluate(p,((0.,0.,10.),)).feasible)
            for solver in (solve_sa,random_search):
                r=solver(p,SAConfig(budget=5,max_initialization_attempts=1000),0)
                self.assertEqual(r.status,'completed')
                self.assertEqual(r.evaluations,5)
                self.assertTrue(r.best_evaluation.feasible)

    def test_solver_budgets_and_repeatability(self):
        for budget in (1, 2, 100):
            for mode in ('feasible', 'penalized'):
                cfg = SAConfig(budget=budget, constraint_mode=mode, trace_interval=1)
                a = solve_sa(problem(), cfg, 7)
                b = solve_sa(problem(), cfg, 7)
                self.assertEqual(a.evaluations, budget)
                self.assertEqual(sum(a.phase_counts.values()), budget)
                self.assertTrue(a.best_evaluation.feasible)
                self.assertEqual(a.best_positions, b.best_positions)
                self.assertEqual([r.best_fitness for r in a.trace], [r.best_fitness for r in b.trace])
                self.assertEqual(a.initial_positions, random_search(problem(),cfg,7).initial_positions)
                self.assertEqual(random_search(problem(),cfg,7).evaluations, budget)

    def test_calibration_and_cooling(self):
        x = ((0.,0.,10.),)
        def worse(p, state, rng, scale): return ((0.,0.,20.),)
        cfg = SAConfig(budget=8, calibration_samples=3, trace_interval=1)
        r = solve_sa(problem(),cfg,0,initial=x,neighbor=worse)
        self.assertAlmostEqual(r.initial_temperature, .5/-math.log(.8))
        self.assertEqual(len(r.calibration_losses), 3)
        search = [t for t in r.trace if t.phase == 'search']
        self.assertAlmostEqual(search[-1].temperature, r.initial_temperature*.01)
        no_loss = solve_sa(problem(),cfg,0,initial=x,neighbor=lambda *args: x)
        self.assertEqual(no_loss.initial_temperature, 1.)
        self.assertTrue(no_loss.calibration_fallback)

    def test_feasible_mode_filters_calibration_penalties(self):
        x = ((0.,0.,10.),)
        cfg = SAConfig(budget=10,trace_interval=1)
        r = solve_sa(problem(),cfg,1,initial=x,neighbor=lambda *args: ((200.,0.,10.),))
        self.assertEqual(r.initial_temperature, 1.)
        self.assertEqual(r.accepted_moves, 0)
        self.assertEqual(r.feasible_proposals, 0)
        self.assertEqual(r.final_positions,x)

    def test_best_feasible_separate_from_infeasible_high_score(self):
        p = problem(targets=((40.000005,0.),), weights=(1.,))
        x = ((0.,0.,40.),)
        candidate = ((0.,0.,40.00001),)
        cfg = SAConfig(budget=2,calibration_samples=0,constraint_mode='penalized')
        r = solve_sa(p,cfg,1,initial=x,neighbor=lambda *args: candidate)
        self.assertGreater(r.final_evaluation.fitness,r.best_evaluation.fitness)
        self.assertFalse(r.final_evaluation.feasible)
        self.assertEqual(r.best_positions,x)

    def test_calibration_candidates_update_best(self):
        x = ((0.,0.,30.),)
        cfg = SAConfig(budget=4,calibration_samples=1)
        calls = iter([((0.,0.,10.),),x,x])
        r = solve_sa(problem(),cfg,0,initial=x,neighbor=lambda *args: next(calls))
        self.assertEqual(r.best_positions,((0.,0.,10.),))

    def test_failures_and_invalid_config(self):
        r = solve_sa(problem(r_comm=1.),SAConfig(budget=2,max_initialization_attempts=10),0)
        self.assertEqual(r.status,'initialization_failed')
        self.assertIsNone(r.best_positions)
        self.assertEqual(r.evaluations,0)
        for kw in [dict(budget=0),dict(budget=True),dict(move_scale=0),dict(operator='bad'),
                   dict(constraint_mode='bad'),dict(target_acceptance=1),dict(final_temperature_ratio=0),
                   dict(temperature_multiplier=math.nan),dict(trace_interval=0)]:
            with self.subTest(kw=kw), self.assertRaises(ValueError): SAConfig(**kw)


if __name__ == '__main__': unittest.main()
