"""Freeze and execute the approved 105-run study using standard-library tools.

python -B -S -m milestone3.final_experiments freeze --pilot results/amendment_pilot
python -B -S -m milestone3.final_experiments run
"""
import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys

from . import __version__
from .cases import load_case
from .search import SAConfig
from .experiments import comparison_configs, sensitivity_configs, run_study
from .export import write_json
from .validation import verify_study

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_CONFIG=ROOT/'experiments/final_experiment_config.json'


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_configuration(root, version, pilot_evidence):
    root=Path(root)
    if not version or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for c in version):
        raise ValueError('version must use lowercase letters, digits, underscores or hyphens')
    baseline=SAConfig(budget=4000)
    comparisons={k:asdict(v) for k,v in comparison_configs(baseline)}
    cases={name:{'path':f'cases/{name}.json','sha256':sha256(root/'cases'/f'{name}.json'),
                 'definition':json.loads(json.dumps(load_case(root/'cases'/f'{name}.json').to_dict()))}
           for name in ('small','medium','large','clustered','separated')}
    studies=[{'name':'main','cases':['small','medium','large'],
              'budgets':{'small':2000,'medium':4000,'large':5000},
              'seeds':list(range(100,110)),'configs':comparisons,'expected_runs':60},
             {'name':'sensitivity','cases':['medium'],'budgets':{'medium':4000},
              'seeds':list(range(200,205)),
              'configs':{k:asdict(v) for k,v in sensitivity_configs(baseline)},'expected_runs':25},
             {'name':'challenging','cases':['clustered','separated'],
              'budgets':{'clustered':4000,'separated':4000},
              'seeds':list(range(300,305)),'configs':comparisons,'expected_runs':20}]
    for study in studies: study['output']=f'results/{version}/{study["name"]}'
    return {'schema_version':1,'version':version,'algorithm_version':__version__,
            'created_utc':datetime.now(timezone.utc).isoformat(),'expected_runs':105,
            'pilot_evidence':pilot_evidence,'budget_revision':'None; proposed budgets retained after runtime pilot.',
            'cases':cases,'studies':studies,
            'source_hashes':{p.relative_to(root).as_posix():sha256(p) for p in sorted((root/'milestone3').glob('*.py'))},
            'algorithms':{'sa_feasible':'feasible-neighborhood simulated annealing',
                          'random':'uniform independent whole-fleet random search'},
            'objective':'maximize weighted unique coverage - 0.1 * total power; infeasible candidates rejected by primary SA',
            'constraints':'Full per-case definitions above specify bounds, 3D minimum separation, GCS connectivity, communication radius, power and coverage parameters.',
            'initialization':{'attempt_cap':10000,'partial_restart_every':500,
              'rules':'Choose anchor uniformly from GCS and placed UAVs. For each nonfixed x/y/z axis draw uniform(-r_comm,r_comm) about anchor; fixed axes consume no draw. Short-circuit bounds, anchor distance, then prior-UAV separation checks in order. Append valid point; restart partial fleet before attempt multiples of 500. Score complete fleet once.',
              'check_unit':'One executed scalar axis-bound or 3D pair-distance test; count short-circuited checks only when executed.'},
            'neighborhood':{'probabilities':{'3d':.8,'altitude':.2,'coordinated':0.},
              'fallback_reason':'Approved simpler distribution: coordinated operator not implemented or verified.',
              'rng':'Each run uses independent random.Random(integer_seed). Every SA candidate, including calibration: random()<0.8 chooses 3d, otherwise altitude; randrange(N) chooses UAV; uniform(-1,1) for each moved axis x,y,z or z, including fixed axes. Multiply by scale*axis_range; reflect. No construction failure, retries or preliminary search rejection. Full evaluation of every proposal. Infeasible rejection consumes no acceptance draw; feasible delta>=0 consumes no acceptance draw; delta<0 consumes one random() for exp(delta/T). Calibration consumes no acceptance draws. Ties accepted; best updates only on strict improvement.'},
            'temperature':{'target_acceptance':.8,'maximum_calibration_evaluations':100,
              'multiplier':1.,'final_ratio':.01,
              'calibration':'Neighbors of unchanged initial state; mean strictly downhill feasible score loss / -log(0.8), fallback 1.0, then multiplier. Calibration candidates can improve best feasible archive. Reserve at least one search evaluation.',
              'cooling':'T_j=T0*0.01**(j/(Bsearch-1)), j=0..Bsearch-1 evaluated search candidates. For Bsearch=1 use T0; for zero record insufficient_search_budget. Infeasible candidates advance j.'},
            'baseline_sampling':'Same seeded constructive initialization and one full initial evaluation as SA. No calibration. Each remaining evaluation samples all UAVs independently uniform in each x,y,z bound, in UAV/axis order, including fixed axes; no resampling on infeasibility. Keep best feasible including initialization.',
            'runtime':{'python':sys.version,'implementation':platform.python_implementation(),
                       'platform':platform.platform(),'packages':'Python standard library only; run with -B -S'}}


def freeze(path, data):
    path=Path(path)
    if path.exists() or path.with_suffix('.sha256').exists():
        raise FileExistsError('frozen configuration already exists; use a new version and path')
    path.parent.mkdir(parents=True,exist_ok=True)
    write_json(path,data)
    digest=sha256(path)
    with path.with_suffix('.sha256').open('x',encoding='ascii') as f: f.write(digest+'\n')
    return digest


def validate_freeze(path, root=ROOT):
    path,root=Path(path),Path(root)
    digest=sha256(path)
    if digest != path.with_suffix('.sha256').read_text().strip():
        raise ValueError('frozen configuration hash mismatch')
    data=json.loads(path.read_text(encoding='utf-8'))
    if data['algorithm_version'] != __version__: raise ValueError('algorithm version mismatch')
    for relative,expected in data['source_hashes'].items():
        if sha256(root/relative) != expected: raise ValueError('frozen source hash mismatch: '+relative)
    for case in data['cases'].values():
        if sha256(root/case['path']) != case['sha256']: raise ValueError('frozen case hash mismatch: '+case['path'])
        if json.loads(json.dumps(load_case(root/case['path']).to_dict())) != case['definition']:
            raise ValueError('case definition mismatch')
    return data,digest


def verify_final_study(root, study, data, digest):
    """Bind the artifact audit to the frozen study and exact case definitions."""
    directory=Path(root)/study['output']
    report=verify_study(directory)
    manifest=json.loads((directory/'manifest.json').read_text())
    expected={'configuration_hash':digest,'version':data['version'],'study':study['name']}
    for field in ('cases','configs','seeds'):
        if manifest[field] != study[field]: raise ValueError('manifest differs from freeze: '+field)
    if manifest['experiment'] != expected: raise ValueError('manifest frozen metadata mismatch')
    for case in study['cases']:
        configs={name:asdict(replace(SAConfig(**cfg),budget=study['budgets'][case]))
                 for name,cfg in study['configs'].items()}
        if manifest['case_configs'][case] != configs: raise ValueError('frozen case budget mismatch')
        for method in study['configs']:
            for seed in study['seeds']:
                path=directory/case/method/f'seed_{seed}'/'case.json'
                definition=json.loads(json.dumps(load_case(path).to_dict()))
                if definition != data['cases'][case]['definition']: raise ValueError('run case differs from freeze')
    if report['verified_runs'] != study['expected_runs']: raise ValueError('unexpected study size')
    return report


def run_final(path=DEFAULT_CONFIG, root=ROOT):
    root=Path(root)
    data,digest=validate_freeze(path,root)
    # Check every destination before writing anything; reruns require a new version.
    for study in data['studies']:
        if (root/study['output']).exists(): raise FileExistsError(study['output'])
    def guard():
        _,current=validate_freeze(path,root)
        if current != digest: raise ValueError('configuration changed during experiment')
    reports=[]
    for study in data['studies']:
        metadata={'configuration_hash':digest,'version':data['version'],'study':study['name']}
        run_study(root/study['output'],[load_case(root/data['cases'][n]['path']) for n in study['cases']],
                  [(name,SAConfig(**cfg)) for name,cfg in study['configs'].items()],study['seeds'],
                  budget_by_case=study['budgets'],experiment_metadata=metadata,guard=guard)
        report=verify_final_study(root,study,data,digest)
        reports.append({'study':study['name'],**report})
    guard()
    if sum(r['verified_runs'] for r in reports) != data['expected_runs']: raise ValueError('unexpected final run count')
    write_json(root/f'results/{data["version"]}/audit.json',
               {'configuration_hash':digest,'version':data['version'],'studies':reports})
    return reports


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['freeze','run','verify'])
    parser.add_argument('--config',type=Path,default=DEFAULT_CONFIG)
    parser.add_argument('--version',default='final_v1')
    parser.add_argument('--pilot',type=Path)
    args=parser.parse_args()
    try:
        if args.command=='freeze':
            if args.pilot is None: raise ValueError('--pilot is required before freezing')
            pilot=verify_study(args.pilot)
            evidence={'path':args.pilot.as_posix(),'audit':pilot,
                      'runs_sha256':sha256(args.pilot/'runs.csv')}
            print(freeze(args.config,build_configuration(ROOT,args.version,evidence)))
        elif args.command=='run': print(json.dumps(run_final(args.config),indent=2))
        else:
            data,digest=validate_freeze(args.config)
            for study in data['studies']: print(study['name'],verify_final_study(ROOT,study,data,digest))
            print('configuration_hash='+digest)
    except (ValueError,OSError) as exc: parser.error(str(exc))


if __name__=='__main__': main()
