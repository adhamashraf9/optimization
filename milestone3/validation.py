"""Post-run artifact audit; recomputations are outside all optimizer budgets."""
import csv
import json
import math
from pathlib import Path
from .cases import load_case
from .model import Evaluation, evaluate
from .search import SearchResult
from .experiments import summarize


def _read_csv(path):
    with Path(path).open(newline='',encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _equal(actual, expected, label):
    if expected is None:
        valid = actual is None or actual == ''
    elif isinstance(expected,(float,int)):
        try: valid = math.isclose(float(actual),expected,rel_tol=1e-11,abs_tol=1e-8)
        except (ValueError,TypeError): valid = False
    else:
        valid = actual == expected
    if not valid: raise ValueError(f'artifact mismatch: {label}: {actual!r} != {expected!r}')


def verify_study(directory):
    directory=Path(directory)
    manifest=json.loads((directory/'manifest.json').read_text())
    if not manifest.get('complete'): raise ValueError('study is incomplete')
    rows=_read_csv(directory/'runs.csv')
    expected_count=len(manifest['cases'])*len(manifest['configs'])*len(manifest['seeds'])
    _equal(len(rows),expected_count,'run count')
    seen=set()
    groups={}
    evaluations=0
    recomputations=0
    for row in rows:
        key=(row['case'],row['method'],int(row['seed']))
        if key in seen: raise ValueError('duplicate run key')
        seen.add(key)
        if key[0] not in manifest['cases'] or key[1] not in manifest['configs'] or key[2] not in manifest['seeds']:
            raise ValueError('unexpected case/method/seed')
        path=(directory/row['run_directory']).resolve()
        if directory.resolve() not in path.parents: raise ValueError('run path escapes study')
        problem=load_case(path/'case.json')
        config_data=json.loads((path/'config.json').read_text())
        config=config_data['config']
        expected_config=manifest.get('case_configs',{}).get(key[0],manifest['configs'])[key[1]]
        _equal(config,expected_config,'run config')
        _equal(config_data['method'],key[1],'method metadata')
        _equal(config_data['seed'],key[2],'seed metadata')
        result=json.loads((path/'result.json').read_text())
        _equal(result['status'],row['status'],'run status')
        _equal(result['evaluations'],int(row['evaluations']),'evaluation count')
        _equal(sum(result['phase_counts'].values()),result['evaluations'],'phase count sum')
        if result['evaluations'] > config['budget']: raise ValueError('budget exceeded')
        if result['status']=='completed': _equal(result['evaluations'],config['budget'],'completed budget')
        evaluations += result['evaluations']
        trace=_read_csv(path/'trace.csv')
        _equal(len(trace),len(result['trace']),'trace row count')
        previous_evaluation=0
        for saved,expected in zip(trace,result['trace']):
            for name,value in expected.items(): _equal(saved[name],value,'trace '+name)
            if not previous_evaluation < int(saved['evaluation']) <= result['evaluations']:
                raise ValueError('nonmonotonic trace evaluations')
            previous_evaluation=int(saved['evaluation'])
            if saved['phase']=='search' and key[1]!='random':
                steps=result['phase_counts']['search']
                j=int(saved['search_proposals'])-1
                temperature=result['initial_temperature']*config['final_temperature_ratio']**(j/max(1,steps-1))
                _equal(saved['temperature'],temperature,'cooling schedule')
        if result['status']=='completed': _equal(previous_evaluation,result['evaluations'],'last trace evaluation')
        if config_data.get('schema_version',1)>=2:
            _equal(json.loads((path/'configuration.json').read_text()),config_data,'configuration alias')
            _equal(_read_csv(path/'convergence.csv'),trace,'convergence alias')
            metrics=json.loads((path/'metrics.json').read_text())
            _equal(config_data['experiment'],manifest.get('experiment',{}),'experiment metadata')
            _equal(metrics['experiment'],config_data['experiment'],'metrics experiment metadata')
            _equal(row.get('configuration_hash'),config_data['experiment'].get('configuration_hash'),'run configuration hash')
            for name,value in {'status':result['status'],'total_evaluations':result['evaluations'],
                  'initialization_checks':result['initialization_checks'],
                  'initialization_attempts':result['initialization_attempts'],
                  'neighbor_proposals':result['proposals'],
                  'infeasible_evaluated_proposals':result['proposals']-result['feasible_proposals'],
                  'accepted_moves':result['accepted_moves'],'elapsed_seconds':result['elapsed_seconds'],
                  'initial_evaluation':result['initial_evaluation'],'best_evaluation':result['best_evaluation']}.items():
                _equal(metrics[name],value,'metrics '+name)
            for phase in ('initialization','calibration','search'):
                _equal(metrics[phase+'_evaluations'],result['phase_counts'][phase],'metrics phase count')
            if result['initial_positions'] is None:
                for filename in ('initial_placement.csv','final_placement.csv','initial_edges.csv','final_edges.csv'):
                    if (path/filename).exists(): raise ValueError('fabricated placement after initialization failure')
        for prefix,position_key,evaluation_key in [('', 'best_positions','best_evaluation'),
                                                  ('initial_','initial_positions','initial_evaluation')]:
            if result[position_key] is None: continue
            scored=evaluate(problem,result[position_key],config['energy_weight'],config['penalty_weight'])
            recomputations += 1
            if not scored.feasible: raise ValueError('saved initial/best placement is infeasible')
            for name in ('fitness','coverage','power','total_weight','coverage_fraction'):
                _equal(result[evaluation_key][name],getattr(scored,name),evaluation_key+'.'+name)
            for name,value in scored.violations.items():
                _equal(result[evaluation_key]['violations'][name],value,name)
            positions=_read_csv(path/f'{prefix}positions.csv')
            if config_data.get('schema_version',1)>=2:
                _equal(_read_csv(path/('initial_placement.csv' if prefix else 'final_placement.csv')),positions,'placement alias')
            _equal(len(positions),problem.num_uavs,'position count')
            for i,(point,saved) in enumerate(zip(result[position_key],positions)):
                _equal(saved['id'],i,'position id')
                for axis,value in zip('xyz',point): _equal(saved[axis],value,'position '+axis)
                _equal(saved['radius'],point[2]*math.tan(math.radians(problem.beam_angle_deg)),'radius')
                if 'gcs_reachable' in saved: _equal(saved['gcs_reachable'],int(i in scored.connected_uavs),'UAV reachability')
            targets=_read_csv(path/f'{prefix}targets.csv')
            _equal(len(targets),len(problem.targets),'target count')
            for i,(saved,hit) in enumerate(zip(targets,scored.covered_targets)):
                for name,value in [('id',i),('x',problem.targets[i][0]),('y',problem.targets[i][1]),
                                   ('weight',problem.weights[i]),('covered',int(hit))]:
                    _equal(saved[name],value,'target '+name)
            edges=_read_csv(path/f'{prefix}edges.csv')
            if config_data.get('schema_version',1)>=2 and not prefix:
                _equal(_read_csv(path/'final_edges.csv'),edges,'edge alias')
            actual_edges=tuple((int(e['from_id']),int(e['to_id'])) for e in edges)
            _equal(actual_edges,scored.edges,'communication edges')
            nodes=tuple(tuple(p) for p in result[position_key])+(problem.gcs,)
            for edge,(a,b) in zip(edges,scored.edges):
                if 'distance' in edge:
                    _equal(edge['distance'],math.dist(nodes[a],nodes[b]),'edge distance')
                    _equal(edge['eligible'],1,'edge eligibility')
                    reachable=set(scored.connected_uavs)|{problem.num_uavs}
                    _equal(edge['gcs_reachable'],int(a in reachable and b in reachable),'edge reachability')
                for suffix,node in [('1',nodes[a]),('2',nodes[b])]:
                    for axis,value in zip('xyz',node): _equal(edge[axis+suffix],value,'edge endpoint')
            if not prefix:
                for name in ('fitness','coverage','power','coverage_fraction'):
                    _equal(row[name],getattr(scored,name),'runs.csv '+name)
        for name in ('initial_evaluation','best_evaluation','final_evaluation','best_penalized_evaluation'):
            if result[name] is not None: result[name]=Evaluation(**result[name])
        groups.setdefault(key[0],[]).append((key[1],key[2],SearchResult(**result)))
    summary=_read_csv(directory/'summary.csv')
    _equal(len(summary),len(manifest['cases'])*len(manifest['configs']),'summary count')
    for case,runs in groups.items():
        for computed in summarize(runs):
            matches=[r for r in summary if r['case']==case and r['method']==computed['method']]
            if len(matches)!=1: raise ValueError('missing or duplicate summary row')
            for name,value in computed.items(): _equal(matches[0][name],value,'summary '+name)
    return {'verified_runs':len(rows),'optimization_evaluations':evaluations,
            'postrun_verification_evaluations':recomputations,'summary_rows':len(summary),
            'note':'Recomputations verify saved data consistency, not global optimality; separate from optimization budget.'}
