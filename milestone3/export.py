"""Inspectable outputs. Serialization uses cached evaluations, never rescoring."""
import csv
from dataclasses import asdict, fields
import json
import math
from pathlib import Path
import platform
import sys
from . import __version__
from .cases import save_case
from .search import TraceRow


def write_json(path, data):
    with Path(path).open('x',encoding='utf-8') as f:
        json.dump(data,f,indent=2,allow_nan=False)


def write_csv(path, rows, columns=None):
    rows = list(rows)
    if columns is None: columns = list(rows[0]) if rows else []
    with Path(path).open('x',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def placement_files(directory, problem, positions, evaluation, prefix=''):
    tangent=math.tan(math.radians(problem.beam_angle_deg))
    reachable=set(evaluation.connected_uavs) | {problem.num_uavs}
    placement_rows=[dict(id=i,x=p[0],y=p[1],z=p[2],radius=p[2]*tangent,
                         gcs_reachable=int(i in reachable)) for i,p in enumerate(positions)]
    write_csv(directory/f'{prefix}positions.csv',placement_rows)
    write_csv(directory/('initial_placement.csv' if prefix else 'final_placement.csv'),placement_rows)
    write_csv(directory/f'{prefix}targets.csv',
              [dict(id=i,x=t[0],y=t[1],weight=w,covered=int(hit))
               for i,(t,w,hit) in enumerate(zip(problem.targets,problem.weights,evaluation.covered_targets))],
              ['id','x','y','weight','covered'])
    nodes=positions+(problem.gcs,)
    edge_rows=[dict(from_id=i,to_id=j,x1=nodes[i][0],y1=nodes[i][1],z1=nodes[i][2],
                   x2=nodes[j][0],y2=nodes[j][1],z2=nodes[j][2],distance=math.dist(nodes[i],nodes[j]),
                   eligible=int(math.dist(nodes[i],nodes[j])<=problem.r_comm),
                   gcs_reachable=int(i in reachable and j in reachable)) for i,j in evaluation.edges]
    columns=['from_id','to_id','x1','y1','z1','x2','y2','z2','distance','eligible','gcs_reachable']
    write_csv(directory/f'{prefix}edges.csv',edge_rows,columns)
    if not prefix: write_csv(directory/'final_edges.csv',edge_rows,columns)


def write_run(directory, problem, config, method, seed, result, experiment_metadata=None):
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=False)
    save_case(problem,directory/'case.json')
    configuration={'schema_version':2,'algorithm_version':__version__,'method':method,'seed':seed,
                   'config':asdict(config),'python':sys.version,'platform':platform.platform(),
                   'experiment':experiment_metadata or {}}
    write_json(directory/'config.json',configuration)
    write_json(directory/'configuration.json',configuration)
    write_json(directory/'result.json',asdict(result))
    metrics={'status':result.status,'total_evaluations':result.evaluations,
             'initialization_evaluations':result.phase_counts.get('initialization',0),
             'calibration_evaluations':result.phase_counts.get('calibration',0),
             'search_evaluations':result.phase_counts.get('search',0),
             'initialization_checks':result.initialization_checks,
             'initialization_attempts':result.initialization_attempts,
             'neighbor_proposals':result.proposals,
             'infeasible_evaluated_proposals':result.proposals-result.feasible_proposals,
             'accepted_moves':result.accepted_moves,'elapsed_seconds':result.elapsed_seconds,
             'initial_temperature':result.initial_temperature,'calibration_losses':result.calibration_losses,
             'calibration_fallback':result.calibration_fallback,
             'initial_evaluation':asdict(result.initial_evaluation) if result.initial_evaluation else None,
             'best_evaluation':asdict(result.best_evaluation) if result.best_evaluation else None,
             'experiment':experiment_metadata or {}}
    write_json(directory/'metrics.json',metrics)
    trace_rows=[asdict(t) for t in result.trace]
    trace_columns=[f.name for f in fields(TraceRow)]
    write_csv(directory/'trace.csv',trace_rows,trace_columns)
    write_csv(directory/'convergence.csv',trace_rows,trace_columns)
    if result.initial_positions is not None:
        placement_files(directory,problem,result.initial_positions,result.initial_evaluation,'initial_')
    if result.best_positions is not None:
        placement_files(directory,problem,result.best_positions,result.best_evaluation)
