"""Exact finite-domain oracle. Its optimum does not certify the continuous problem."""
from itertools import product
from dataclasses import asdict
import time
from .model import Problem, evaluate
from .search import SAConfig, solve_sa


def tiny_instance():
    p = Problem(2,((0.,0.),(20.,0.)),(2.,3.),(0.,0.,0.),
                ((0.,20.),(0.,0.),(10.,20.)),r_comm=40.,d_min=5.)
    sites = ((0.,0.,10.),(20.,0.,10.),(0.,0.,20.),(20.,0.,20.))
    return p,sites,(sites[2],sites[3])


def enumerate_grid(problem, sites, energy_weight=0.1, penalty_weight=10000., *, with_cost=False):
    started = time.perf_counter()
    best,score,count = None,None,0
    feasible_count = 0
    for positions in product(sites,repeat=problem.num_uavs):
        value = evaluate(problem,positions,energy_weight,penalty_weight)
        count += 1
        feasible_count += int(value.feasible)
        if value.feasible and (score is None or value.fitness > score.fitness):
            best,score = positions,value
    if best is None: raise ValueError('no feasible placement in finite grid')
    if with_cost:
        return best,score,{'oracle_evaluations':count,'oracle_runtime_seconds':time.perf_counter()-started,
                           'oracle_optimal_score':score.fitness,'oracle_feasible_placements':feasible_count}
    return best,score,count


def grid_neighbor(sites):
    sites = tuple(sites)
    if not sites: raise ValueError('grid sites must not be empty')
    def move(problem,positions,rng,scale):
        index = rng.randrange(problem.num_uavs)
        return positions[:index]+(rng.choice(sites),)+positions[index+1:]
    return move


def run_benchmark(budget=500,seeds=tuple(range(10))):
    problem,sites,initial = tiny_instance()
    best,score,cost = enumerate_grid(problem,sites,with_cost=True)
    trials = []
    for seed in seeds:
        result = solve_sa(problem,SAConfig(budget=budget),seed,
                          neighbor=grid_neighbor(sites),initial=initial)
        gap = score.fitness-result.best_evaluation.fitness
        trials.append({'seed':seed,'fitness':result.best_evaluation.fitness,
                       'absolute_gap':gap,'hit_optimum':abs(gap)<1e-10,
                       'evaluations':result.evaluations,'elapsed_seconds':result.elapsed_seconds,
                       'status':result.status})
    return {'scope':'finite grid only; not a continuous global optimum',
            'problem':problem.to_dict(),'sites':sites,'initial_positions':initial,
            'optimal_positions':best,'optimal_evaluation':asdict(score),
            **cost,'trials':trials,
            'hit_rate':sum(t['hit_optimum'] for t in trials)/len(trials) if trials else None}
