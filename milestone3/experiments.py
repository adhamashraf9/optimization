"""Paired, budget-matched experiments and failure-aware statistics."""
from dataclasses import asdict, replace
import json
from pathlib import Path
import statistics
import time
from .search import solve_sa, random_search
from .export import write_run, write_csv, write_json


def comparison_configs(config):
    return [('sa_feasible',replace(config,constraint_mode='feasible')),
            ('random',config)]


def sensitivity_configs(config):
    """Approved five distinct one-factor-at-a-time configurations."""
    return [('baseline',config),
            ('temperature_0.5',replace(config,temperature_multiplier=.5)),
            ('temperature_2',replace(config,temperature_multiplier=2.)),
            ('move_0.025',replace(config,move_scale=.025)),
            ('move_0.1',replace(config,move_scale=.1))]


def run_comparison(problem, config, seeds):
    return [(method,seed,(random_search if method=='random' else solve_sa)(problem,cfg,seed))
            for method,cfg in comparison_configs(config) for seed in seeds]


def summarize(runs):
    rows=[]
    for method in dict.fromkeys(m for m,_,_ in runs):
        all_results=[r for m,_,r in runs if m==method]
        success=[r for r in all_results if r.status=='completed' and r.best_evaluation is not None and r.best_evaluation.feasible]
        row={'method':method,'attempted_runs':len(all_results),'successful_runs':len(success),
             'feasible_run_rate':len(success)/len(all_results),
             'initialization_failures':sum(r.status=='initialization_failed' for r in all_results)}
        for key,getter in [('fitness',lambda r:r.best_evaluation.fitness),
                           ('coverage',lambda r:r.best_evaluation.coverage),
                           ('coverage_fraction',lambda r:r.best_evaluation.coverage_fraction),
                           ('covered_count',lambda r:sum(r.best_evaluation.covered_targets)),
                           ('power',lambda r:r.best_evaluation.power)]:
            values=[getter(r) for r in success if getter(r) is not None]
            row['mean_'+key]=statistics.mean(values) if values else None
            row['std_'+key]=statistics.stdev(values) if len(values)>1 else (0. if values else None)
        scores=[r.best_evaluation.fitness for r in success]
        row['best_fitness']=max(scores) if scores else None
        row['worst_fitness']=min(scores) if scores else None
        for key,getter in [('runtime',lambda r:r.elapsed_seconds),('evaluations',lambda r:r.evaluations),
                           ('initialization_attempts',lambda r:r.initialization_attempts),
                           ('initialization_seconds',lambda r:r.initialization_seconds)]:
            row['mean_'+key]=statistics.mean(getter(r) for r in all_results)
        proposals=sum(r.search_proposals for r in all_results)
        row['feasible_proposal_rate']=sum(r.feasible_search_proposals for r in all_results)/proposals if proposals else None
        row['acceptance_rate']=(sum(r.accepted_moves for r in all_results)/proposals
                                if proposals and method!='random' else None)
        rows.append(row)
    return rows


def run_study(output, cases, configs, seeds, progress=True, *, budget_by_case=None,
              experiment_metadata=None, guard=None):
    cases,configs,seeds=list(cases),list(configs),list(seeds)
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    manifest={'complete':False,'cases':[p.metadata.get('name','case') for p in cases],
              'configs':{name:asdict(cfg) for name,cfg in configs},'seeds':seeds,
              'experiment':experiment_metadata or {},
              'case_configs':{p.metadata.get('name','case'):{label:asdict(replace(cfg,
                  budget=(budget_by_case or {}).get(p.metadata.get('name','case'),cfg.budget)))
                  for label,cfg in configs} for p in cases},
              'note':'Quality statistics conditional on feasible results; failures retained. No resampling of rejected candidates.'}
    write_json(output/'manifest.json',manifest)
    run_rows,summary_rows=[],[]
    for problem in cases:
        name=problem.metadata.get('name','case')
        results=[]
        for method,config in configs:
            config=replace(config,budget=(budget_by_case or {}).get(name,config.budget))
            for seed in seeds:
                if guard is not None: guard()
                result=(random_search if method=='random' else solve_sa)(problem,config,seed)
                if guard is not None: guard()
                directory=output/name/method/f'seed_{seed}'
                write_run(directory,problem,config,method,seed,result,experiment_metadata)
                results.append((method,seed,result))
                best=result.best_evaluation
                row={'case':name,'method':method,'seed':seed,'status':result.status,
                     'configuration_hash':(experiment_metadata or {}).get('configuration_hash'),
                     'run_directory':directory.relative_to(output).as_posix(),'num_uavs':problem.num_uavs,
                     'num_targets':len(problem.targets),'budget':config.budget,'evaluations':result.evaluations,
                     'fitness':best.fitness if best else None,'coverage':best.coverage if best else None,
                     'coverage_fraction':best.coverage_fraction if best else None,
                     'covered_count':sum(best.covered_targets) if best else None,'power':best.power if best else None,
                     'power_per_uav':best.power/problem.num_uavs if best else None,
                     'bounds_violation':best.violations['bounds'] if best else None,
                     'collision_violation':best.violations['collision'] if best else None,
                     'connectivity_violation':best.violations['connectivity'] if best else None,
                     'initial_fitness':result.initial_evaluation.fitness if result.initial_evaluation else None,
                     'runtime':result.elapsed_seconds,'initialization_attempts':result.initialization_attempts,
                     'initialization_checks':result.initialization_checks,
                     'total_evaluations':result.evaluations,'neighbor_proposals':result.proposals,
                     'infeasible_evaluated_proposals':result.proposals-result.feasible_proposals,
                     'elapsed_seconds':result.elapsed_seconds,
                     'initialization_seconds':result.initialization_seconds,
                     'proposals':result.proposals,'feasible_proposals':result.feasible_proposals,
                     'search_proposals':result.search_proposals,'accepted_moves':result.accepted_moves,
                     'rejected_moves':result.search_proposals-result.accepted_moves if method!='random' else None,
                     'initial_temperature':result.initial_temperature,'calibration_fallback':result.calibration_fallback,
                     'initialization_evaluations':result.phase_counts.get('initialization',0),
                     'calibration_evaluations':result.phase_counts.get('calibration',0),
                     'search_evaluations':result.phase_counts.get('search',0)}
                run_rows.append(row)
                if progress:
                    print(f'{name} {method} seed={seed} evaluations={result.evaluations} fitness={row["fitness"]} status={result.status}',flush=True)
        for row in summarize(results):
            summary_rows.append({'case':name,'num_uavs':problem.num_uavs,'num_targets':len(problem.targets),
                                 **row,'mean_power_per_uav':row['mean_power']/problem.num_uavs if row['mean_power'] is not None else None})
    write_csv(output/'runs.csv',run_rows)
    write_csv(output/'summary.csv',summary_rows)
    manifest['complete']=True
    # This is our own newly created manifest, not an existing user result.
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False),encoding='utf-8')
    return summary_rows
