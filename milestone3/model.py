"""Milestone 2 geometry and penalties, implemented with the standard library.

All coordinates are metres, power is watts. Coverage and connectivity use inclusive
distance comparisons without adding a tolerance that changes the feasible region.
"""
from dataclasses import dataclass, field, asdict
import math
from typing import Optional

Position = tuple[float, float, float]
Positions = tuple[Position, ...]


def finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{label} must be a finite number')
    return float(value)


def coordinates(values, size, label):
    try:
        if len(values) != size:
            raise ValueError(f'{label} must have {size} coordinates')
        return tuple(finite(v, label) for v in values)
    except TypeError as exc:
        raise ValueError(f'{label} must be a coordinate sequence') from exc


@dataclass(frozen=True)
class Problem:
    num_uavs: int
    targets: tuple[tuple[float, float], ...]
    weights: tuple[float, ...]
    gcs: Position
    bounds: tuple[tuple[float, float], ...]
    r_comm: float = 150.0
    d_min: float = 10.0
    beam_angle_deg: float = 45.0
    p_base: float = 100.0
    beta_power: float = 0.5
    metadata: dict = field(default_factory=dict, compare=False)

    def __post_init__(self):
        if type(self.num_uavs) is not int or self.num_uavs < 1:
            raise ValueError('num_uavs must be a positive integer')
        try:
            targets = tuple(coordinates(t, 2, 'target') for t in self.targets)
            weights = tuple(finite(w, 'weight') for w in self.weights)
            bounds = tuple(coordinates(b, 2, 'bounds') for b in self.bounds)
        except TypeError as exc:
            raise ValueError('targets, weights and bounds must be sequences') from exc
        if len(targets) != len(weights) or any(w <= 0 for w in weights):
            raise ValueError('one positive weight is required per target')
        if len(bounds) != 3 or any(lo > hi for lo, hi in bounds) or bounds[2][0] < 0:
            raise ValueError('three ordered bounds with nonnegative altitude are required')
        for name in ('r_comm', 'd_min', 'beam_angle_deg', 'p_base', 'beta_power'):
            object.__setattr__(self, name, finite(getattr(self, name), name))
        if self.r_comm <= 0 or min(self.d_min, self.p_base, self.beta_power) < 0:
            raise ValueError('invalid range, separation or power parameters')
        if not 0 < self.beam_angle_deg < 90:
            raise ValueError('beam_angle_deg must be strictly between 0 and 90')
        for name, value in [('targets', targets), ('weights', weights), ('bounds', bounds),
                            ('gcs', coordinates(self.gcs, 3, 'gcs'))]:
            object.__setattr__(self, name, value)

    @classmethod
    def from_dict(cls, data):
        try:
            return cls(**data)
        except (TypeError, KeyError) as exc:
            raise ValueError(f'invalid problem schema: {exc}') from exc

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class Evaluation:
    coverage: float
    total_weight: float
    coverage_fraction: Optional[float]
    power: float
    violations: dict[str, float]
    feasible: bool
    fitness: float
    covered_targets: tuple[bool, ...]
    connected_uavs: tuple[int, ...]
    edges: tuple[tuple[int, int], ...]

    @property
    def total_violation(self):
        return sum(self.violations.values())


def validate_positions(problem: Problem, positions) -> Positions:
    try:
        if len(positions) != problem.num_uavs:
            raise ValueError(f'expected {problem.num_uavs} UAV positions')
        return tuple(coordinates(p, 3, 'position') for p in positions)
    except TypeError as exc:
        raise ValueError('positions must be a sequence of coordinate triples') from exc


def evaluate(problem: Problem, positions: Positions, energy_weight: float = 0.1,
             penalty_weight: float = 10000.0) -> Evaluation:
    """Score one complete placement; geometrically infeasible positions are valid inputs."""
    positions = validate_positions(problem, positions)
    energy_weight = finite(energy_weight, 'energy_weight')
    penalty_weight = finite(penalty_weight, 'penalty_weight')
    if min(energy_weight, penalty_weight) < 0:
        raise ValueError('objective coefficients must be nonnegative')
    tangent = math.tan(math.radians(problem.beam_angle_deg))
    covered = tuple(any(math.hypot(p[0]-t[0], p[1]-t[1]) <= p[2]*tangent
                        for p in positions) for t in problem.targets)
    coverage = sum(w for w, hit in zip(problem.weights, covered) if hit)
    total = sum(problem.weights)
    power = sum(problem.p_base + problem.beta_power*p[2] for p in positions)
    bounds = sum(max(0., lo-v) + max(0., v-hi)
                 for p in positions for v, (lo, hi) in zip(p, problem.bounds))
    collision = sum(max(0., problem.d_min-math.dist(positions[i], positions[j]))
                    for i in range(problem.num_uavs) for j in range(i+1, problem.num_uavs))
    nodes = positions + (problem.gcs,)
    adjacency = [[] for _ in nodes]
    edges = []
    for i in range(len(nodes)):
        for j in range(i+1, len(nodes)):
            if math.dist(nodes[i], nodes[j]) <= problem.r_comm:
                adjacency[i].append(j)
                adjacency[j].append(i)
                edges.append((i, j))
    visited = {problem.num_uavs}
    stack = [problem.num_uavs]
    while stack:
        for node in adjacency[stack.pop()]:
            if node not in visited:
                visited.add(node)
                stack.append(node)
    violations = {'bounds': bounds, 'collision': collision,
                  'connectivity': float(problem.num_uavs-len(visited)+1)}
    violation = sum(violations.values())
    score = coverage - energy_weight*power - penalty_weight*violation
    if not all(math.isfinite(v) for v in (coverage, total, power, violation, score)):
        raise ValueError('numerical overflow while evaluating placement')
    return Evaluation(coverage, total, coverage/total if total else None, power,
                      violations, violation == 0., score, covered,
                      tuple(i for i in range(problem.num_uavs) if i in visited), tuple(edges))
