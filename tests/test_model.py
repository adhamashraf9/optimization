import json
import math
from dataclasses import replace
from pathlib import Path
import unittest

from milestone3.model import Problem, evaluate


def problem(n=1, **kwargs):
    values = dict(num_uavs=n, targets=((0., 0.),), weights=(1.,),
                  gcs=(0., 0., 0.), bounds=((-100., 100.), (-100., 100.), (10., 40.)))
    values.update(kwargs)
    return Problem(**values)


class ModelTests(unittest.TestCase):
    def test_overlap_and_power(self):
        r = evaluate(problem(2), ((0., 0., 10.), (0., 0., 20.)))
        self.assertEqual(r.coverage, 1)
        self.assertEqual(r.power, 215)
        self.assertEqual(r.covered_targets, (True,))

    def test_footprint_and_empty_targets(self):
        p = problem(targets=((9., 0.), (11., 0.)), weights=(2., 3.))
        self.assertEqual(evaluate(p, ((0., 0., 10.),)).coverage, 2)
        empty = evaluate(problem(targets=(), weights=()), ((0., 0., 10.),))
        self.assertEqual(empty.coverage, 0)
        self.assertIsNone(empty.coverage_fraction)

    def test_mesh_and_disconnected_cluster(self):
        p = problem(2, r_comm=15., d_min=5.)
        self.assertTrue(evaluate(p, ((0., 0., 10.), (0., 0., 20.))).feasible)
        r = evaluate(p, ((50., 0., 10.), (50., 0., 20.)))
        self.assertEqual(r.violations['connectivity'], 2)
        self.assertEqual(r.connected_uavs, ())

    def test_bounds_collision_and_exact_contact(self):
        self.assertEqual(evaluate(problem(), ((101., 0., 45.),)).violations['bounds'], 6)
        p = problem(2, d_min=5., r_comm=20.)
        self.assertEqual(evaluate(p, ((0., 0., 10.), (0., 0., 12.))).violations['collision'], 3)
        self.assertTrue(evaluate(p, ((0., 0., 10.), (0., 0., 20.))).feasible)
        self.assertFalse(evaluate(problem(r_comm=10.), ((0., 0., 10.0001),)).feasible)

    def test_exact_coverage_boundary_uses_computed_radius(self):
        radius = 10 * math.tan(math.radians(45))
        p = problem(targets=((radius, 0.), (math.nextafter(radius, math.inf), 0.)), weights=(1., 1.))
        self.assertEqual(evaluate(p, ((0., 0., 10.),)).covered_targets, (True, False))

    def test_invalid_inputs(self):
        for kw in [dict(num_uavs=0), dict(num_uavs=True), dict(weights=(-1.,)),
                   dict(weights=(0.,)), dict(weights=(math.nan,)), dict(weights=(math.inf,)), dict(targets=((0.,),)),
                   dict(bounds=((2., 1.), (0., 1.), (0., 1.))),
                   dict(bounds=((0., 1.), (0., 1.), (-1., 2.))), dict(r_comm=0.),
                   dict(d_min=-1.), dict(beam_angle_deg=90.), dict(p_base=-1.),
                   dict(gcs=(0., math.inf, 0.)), dict(beta_power=-1.)]:
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                problem(**kw)
        for positions in [(), ((0., 1.),), ((0., 0., math.nan),), (0., 0., 10.)]:
            with self.subTest(positions=positions), self.assertRaises(ValueError):
                evaluate(problem(), positions)
        with self.assertRaises(ValueError):
            evaluate(problem(), ((0., 0., 10.),), energy_weight=math.inf)

    def test_reference_parity(self):
        fixture = json.loads((Path(__file__).parent / 'fixtures/m2_reference.json').read_text())
        p = Problem.from_dict(fixture['problem'])
        self.assertGreaterEqual(len(fixture['samples']), 50)
        for sample in fixture['samples']:
            r = evaluate(p, sample['positions'])
            expected = sample['evaluation']
            for field in ['coverage', 'power', 'fitness']:
                self.assertTrue(math.isclose(getattr(r, field), expected[field], rel_tol=1e-12, abs_tol=1e-8), field)
            self.assertEqual(r.feasible, expected['feasible'])
            for key in r.violations:
                self.assertAlmostEqual(r.violations[key], expected['violations'][key], places=9)


if __name__ == '__main__':
    unittest.main()
