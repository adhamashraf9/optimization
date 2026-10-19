"""Fixed, serialized study inputs; generation seeds are separate from solver seeds."""
import json
from pathlib import Path
import random
from .model import Problem

CASE_SEEDS = {'small':101,'medium':102,'large':103,'clustered':104,'separated':105,'tuning':106}


def make_case(name: str, seed: int) -> Problem:
    if name not in CASE_SEEDS: raise ValueError(f'unknown case: {name}')
    if type(seed) is not int: raise ValueError('case seed must be an integer')
    n,m = {'small':(4,10),'large':(16,150)}.get(name,(8,50))
    rng = random.Random(seed)
    targets = []
    for index in range(m):
        if name in ('clustered','separated'):
            centers,std = ((150.,350.),35.) if name == 'clustered' else ((70.,430.),20.)
            center = centers[index % 2]
            targets.append(tuple(min(500.,max(0.,rng.gauss(center,std))) for _ in range(2)))
        else:
            targets.append((rng.uniform(0,500),rng.uniform(0,500)))
    return Problem(n,tuple(targets),tuple(rng.uniform(1,10) for _ in range(m)),
                   (250.,250.,0.),((0.,500.),(0.,500.),(30.,120.)),r_comm=200.,d_min=15.,
                   metadata={'name':name,'generation_seed':seed,
                             'description':('two clipped Gaussian clusters' if name in ('clustered','separated')
                                            else 'uniform static targets')})


def save_case(problem: Problem, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:
        json.dump({'schema_version':1,'problem':problem.to_dict()},f,indent=2,allow_nan=False)


def load_case(path: Path) -> Problem:
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        if data['schema_version'] != 1: raise ValueError('unsupported case schema')
        return Problem.from_dict(data['problem'])
    except (KeyError,TypeError,json.JSONDecodeError) as exc:
        raise ValueError(f'invalid case file: {path}') from exc


def generate_cases(directory: Path):
    for name,seed in CASE_SEEDS.items():
        save_case(make_case(name,seed),Path(directory)/f'{name}.json')
