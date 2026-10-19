"""Budgeted simulated annealing and uniform random search for UAV placements."""
from dataclasses import dataclass, field
import math
import random
import statistics
import time
from typing import Optional, Callable
from .model import Problem, Positions, Evaluation, evaluate, finite, validate_positions


@dataclass(frozen=True)
class SAConfig:
    budget: int = 5000
    move_scale: float = 0.05
    calibration_samples: int = 100
    target_acceptance: float = 0.8
    temperature_multiplier: float = 1.0
    final_temperature_ratio: float = 0.01
    energy_weight: float = 0.1
    penalty_weight: float = 10000.0
    max_initialization_attempts: int = 10000
    trace_interval: int = 25
    operator: str = 'mixed'
    constraint_mode: str = 'feasible'

    def __post_init__(self):
        for name in ('budget','calibration_samples','max_initialization_attempts','trace_interval'):
            v = getattr(self,name)
            if type(v) is not int or v < (0 if name == 'calibration_samples' else 1):
                raise ValueError(f'invalid {name}')
        for name in ('move_scale','temperature_multiplier','energy_weight','penalty_weight',
                     'target_acceptance','final_temperature_ratio'):
            finite(getattr(self,name),name)
        if self.move_scale <= 0 or self.temperature_multiplier <= 0:
            raise ValueError('move_scale and temperature_multiplier must be positive')
        if min(self.energy_weight,self.penalty_weight) < 0:
            raise ValueError('objective coefficients must be nonnegative')
        if not 0 < self.target_acceptance < 1 or not 0 < self.final_temperature_ratio <= 1:
            raise ValueError('invalid target acceptance or final temperature ratio')
        if self.operator not in ('3d','altitude','mixed') or self.constraint_mode not in ('feasible','penalized'):
            raise ValueError('unknown operator or constraint mode')


class BudgetEvaluator:
    """Single gateway for every complete algorithmic candidate evaluation."""
    def __init__(self, problem: Problem, config: SAConfig):
        self.problem, self.config = problem, config
        self.used = 0
        self.phase_counts = {'initialization':0,'calibration':0,'search':0}

    def evaluate(self, positions: Positions, phase: str) -> Evaluation:
        if self.used >= self.config.budget:
            raise RuntimeError('evaluation budget exhausted')
        if phase not in self.phase_counts:
            raise ValueError('unknown evaluation phase')
        scored = evaluate(self.problem,positions,self.config.energy_weight,self.config.penalty_weight)
        self.used += 1
        self.phase_counts[phase] += 1
        return scored


def reflect(value: float, lo: float, hi: float) -> float:
    """Triangular-wave reflection handles arbitrarily many boundary crossings."""
    for v in (value,lo,hi): finite(v,'reflection coordinate')
    if lo > hi: raise ValueError('reversed reflection bounds')
    if lo == hi: return lo
    width = hi-lo
    folded = (value-lo) % (2*width)
    return lo + (folded if folded <= width else 2*width-folded)


def propose(problem: Problem, positions: Positions, rng: random.Random,
            move_scale: float, operator: str = '3d') -> Positions:
    if finite(move_scale,'move_scale') <= 0 or operator not in ('3d','altitude','mixed'):
        raise ValueError('invalid neighborhood configuration')
    # One selection draw, then one UAV selection and one uniform draw per moved
    # axis, including fixed axes. Reflection never retries or draws again.
    if operator == 'mixed':
        operator = '3d' if rng.random() < .8 else 'altitude'
    index = rng.randrange(problem.num_uavs)
    point = list(positions[index])
    for axis in (range(3) if operator == '3d' else (2,)):
        lo,hi = problem.bounds[axis]
        point[axis] = reflect(point[axis]+rng.uniform(-1,1)*move_scale*(hi-lo),lo,hi)
    return positions[:index] + (tuple(point),) + positions[index+1:]


def accept(delta: float, temperature: float, rng: random.Random) -> bool:
    finite(delta,'score change')
    if finite(temperature,'temperature') <= 0:
        raise ValueError('temperature must be positive')
    return delta >= 0 or rng.random() < math.exp(delta/temperature)


@dataclass(frozen=True)
class InitialResult:
    positions: Optional[Positions]
    attempts: int
    checks: int = 0


def initialize(problem: Problem, rng: random.Random, max_attempts: int = 10000) -> InitialResult:
    """Construct a GCS-connected fleet; attempts count partial geometric proposals.

    Local distance checks are not complete fitness evaluations. A completed fleet
    is scored exactly once by BudgetEvaluator in the solver.
    """
    if type(max_attempts) is not int or max_attempts < 1: raise ValueError('invalid attempt limit')
    points = []
    checks = 0
    for attempt in range(1,max_attempts+1):
        if attempt % 500 == 0: points = []
        anchor = rng.choice([problem.gcs]+points)
        # Fixed axes are valid model inputs: sampling a continuous coordinate and
        # then requiring exact equality would reject every feasible proposal.
        candidate = tuple(lo if lo == hi else anchor[a]+rng.uniform(-problem.r_comm,problem.r_comm)
                          for a,(lo,hi) in enumerate(problem.bounds))
        valid = True
        for v,(lo,hi) in zip(candidate,problem.bounds):
            checks += 1
            if not lo <= v <= hi:
                valid = False
                break
        if not valid: continue
        checks += 1
        if math.dist(candidate,anchor) > problem.r_comm: continue
        for p in points:
            checks += 1
            if math.dist(candidate,p) < problem.d_min:
                valid = False
                break
        if not valid: continue
        points.append(candidate)
        if len(points) == problem.num_uavs: return InitialResult(tuple(points),attempt,checks)
    return InitialResult(None,max_attempts,checks)


@dataclass(frozen=True)
class TraceRow:
    phase: str
    evaluation: int
    temperature: Optional[float]
    current_fitness: float
    current_violation: float
    best_fitness: Optional[float]
    best_coverage: Optional[float]
    best_power: Optional[float]
    accepted_moves: int
    search_proposals: int
    feasible_search_proposals: int
    elapsed_seconds: float


@dataclass
class SearchResult:
    status: str = 'initialization_failed'
    initial_positions: Optional[Positions] = None
    initial_evaluation: Optional[Evaluation] = None
    best_positions: Optional[Positions] = None
    best_evaluation: Optional[Evaluation] = None
    final_positions: Optional[Positions] = None
    final_evaluation: Optional[Evaluation] = None
    best_penalized_positions: Optional[Positions] = None
    best_penalized_evaluation: Optional[Evaluation] = None
    trace: list[TraceRow] = field(default_factory=list)
    evaluations: int = 0
    phase_counts: dict = field(default_factory=dict)
    initialization_attempts: int = 0
    initialization_checks: int = 0
    initialization_seconds: float = 0.
    initial_temperature: Optional[float] = None
    calibration_losses: list[float] = field(default_factory=list)
    calibration_fallback: bool = False
    proposals: int = 0
    feasible_proposals: int = 0
    search_proposals: int = 0
    feasible_search_proposals: int = 0
    accepted_moves: int = 0
    elapsed_seconds: float = 0.


def _run(problem, config, seed, method, neighbor=None, initial=None):
    if type(seed) is not int: raise ValueError('seed must be an integer')
    start = time.perf_counter()
    rng = random.Random(seed)
    budget = BudgetEvaluator(problem,config)
    result = SearchResult()
    if initial is None:
        init = initialize(problem,rng,config.max_initialization_attempts)
        current = init.positions
        result.initialization_attempts = init.attempts
        result.initialization_checks = init.checks
    else:
        current = validate_positions(problem,initial)
    result.initialization_seconds = time.perf_counter()-start
    if current is None:
        result.phase_counts = dict(budget.phase_counts)
        result.elapsed_seconds = time.perf_counter()-start
        return result
    current_eval = budget.evaluate(current,'initialization')
    if not current_eval.feasible: raise ValueError('initial placement must be feasible')
    result.initial_positions, result.initial_evaluation = current, current_eval

    def track(candidate, scored):
        if scored.feasible and (result.best_evaluation is None or scored.fitness > result.best_evaluation.fitness):
            result.best_positions,result.best_evaluation = candidate,scored
        if result.best_penalized_evaluation is None or scored.fitness > result.best_penalized_evaluation.fitness:
            result.best_penalized_positions,result.best_penalized_evaluation = candidate,scored

    def record(phase,temperature=None,force=False):
        if force or budget.used % config.trace_interval == 0 or budget.used == config.budget:
            best = result.best_evaluation
            result.trace.append(TraceRow(phase,budget.used,temperature,current_eval.fitness,
                current_eval.total_violation,best.fitness if best else None,
                best.coverage if best else None,best.power if best else None,
                result.accepted_moves,result.search_proposals,result.feasible_search_proposals,
                time.perf_counter()-start))

    track(current,current_eval)
    record('initialization',force=True)
    move = neighbor or (lambda p,x,r,s: propose(p,x,r,s,config.operator))
    if method == 'sa':
        count = max(0,min(config.calibration_samples,config.budget-budget.used-1))
        for _ in range(count):
            candidate = validate_positions(problem,move(problem,current,rng,config.move_scale))
            scored = budget.evaluate(candidate,'calibration')
            result.proposals += 1
            result.feasible_proposals += int(scored.feasible)
            track(candidate,scored)
            delta = scored.fitness-current_eval.fitness
            if delta < 0 and (scored.feasible or config.constraint_mode == 'penalized'):
                result.calibration_losses.append(-delta)
            record('calibration')
        result.calibration_fallback = not result.calibration_losses
        t0 = (-statistics.mean(result.calibration_losses)/math.log(config.target_acceptance)
              if result.calibration_losses else 1.) * config.temperature_multiplier
        if not math.isfinite(t0) or t0 <= 0: raise ValueError('invalid calibrated temperature')
        result.initial_temperature = t0
    steps = config.budget-budget.used
    for step in range(steps):
        temperature = None
        if method == 'sa':
            temperature = result.initial_temperature * config.final_temperature_ratio**(step/max(1,steps-1))
            candidate = validate_positions(problem,move(problem,current,rng,config.move_scale))
        else:
            candidate = tuple(tuple(rng.uniform(lo,hi) for lo,hi in problem.bounds)
                              for _ in range(problem.num_uavs))
        scored = budget.evaluate(candidate,'search')
        result.proposals += 1
        result.search_proposals += 1
        result.feasible_proposals += int(scored.feasible)
        result.feasible_search_proposals += int(scored.feasible)
        track(candidate,scored)
        if method == 'random':
            current,current_eval = candidate,scored
        elif (scored.feasible or config.constraint_mode == 'penalized') and accept(scored.fitness-current_eval.fitness,temperature,rng):
            current,current_eval = candidate,scored
            result.accepted_moves += 1
        record('search',temperature,force=(step == 0))
    result.status = ('insufficient_search_budget' if steps == 0 else
                     'completed' if result.best_evaluation else 'no_feasible_solution')
    result.final_positions,result.final_evaluation = current,current_eval
    result.evaluations = budget.used
    result.phase_counts = dict(budget.phase_counts)
    result.elapsed_seconds = time.perf_counter()-start
    return result


def solve_sa(problem: Problem, config: SAConfig, seed: int, *,
             neighbor: Optional[Callable] = None, initial: Optional[Positions] = None) -> SearchResult:
    return _run(problem,config,seed,'sa',neighbor,initial)


def random_search(problem: Problem, config: SAConfig, seed: int) -> SearchResult:
    """Uniform in-bounds fleets, sharing the seeded feasible initializer with SA."""
    return _run(problem,config,seed,'random')
