"""Command-line entry point: python -B -S -m milestone3 --help."""
import argparse
from pathlib import Path
from dataclasses import replace
from .cases import load_case
from .search import SAConfig
from .experiments import run_study, comparison_configs, sensitivity_configs
from .benchmark import run_benchmark
from .export import write_json


def parse_seeds(text):
    try:
        values=tuple(range(*map(int,text.split(':')))) if ':' in text else tuple(map(int,text.split(',')))
        if not values or len(set(values)) != len(values): raise ValueError()
        return values
    except (ValueError,TypeError) as exc:
        raise argparse.ArgumentTypeError('use unique comma-separated seeds or start:stop') from exc


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['demo','benchmark','pilot','compare','sensitivity'])
    parser.add_argument('--output',type=Path,required=True,help='new output directory; existing directories are never overwritten')
    parser.add_argument('--case',type=Path)
    parser.add_argument('--budget',type=int,default=5000)
    parser.add_argument('--seed',type=int,default=0)
    parser.add_argument('--seeds',type=parse_seeds,default=tuple(range(10)),help='e.g. 0:10 or 0,1,2')
    parser.add_argument('--operator',choices=['3d','altitude','mixed'],default='mixed')
    parser.add_argument('--mode',choices=['feasible','penalized'],default='feasible')
    parser.add_argument('--move-scale',type=float,default=.05)
    parser.add_argument('--temperature-multiplier',type=float,default=1.)
    parser.add_argument('--final-temperature-ratio',type=float,default=.01)
    args=parser.parse_args()
    try:
        config=SAConfig(budget=args.budget,operator=args.operator,constraint_mode=args.mode,
                        move_scale=args.move_scale,temperature_multiplier=args.temperature_multiplier,
                        final_temperature_ratio=args.final_temperature_ratio)
        if args.command=='benchmark':
            args.output.mkdir(parents=True,exist_ok=False)
            report=run_benchmark(args.budget,args.seeds)
            write_json(args.output/'benchmark.json',report)
            print(f'Finite-grid optimum={report["optimal_evaluation"]["fitness"]}; hit_rate={report["hit_rate"]}; oracle evaluations={report["oracle_evaluations"]}')
            return 0
        root=Path(__file__).resolve().parent.parent/'cases'
        if args.case:
            cases=[load_case(args.case)]
        elif args.command=='demo':
            cases=[load_case(root/'m2_reference.json')]
        elif args.command=='sensitivity':
            cases=[load_case(root/'medium.json')]
        else:
            cases=[load_case(root/f'{name}.json') for name in ('small','medium','large','clustered','separated','m2_reference')]
        configs=(comparison_configs(config) if args.command=='compare' else
                 sensitivity_configs(config) if args.command=='sensitivity' else [('sa_'+args.mode,config)])
        seeds=(args.seed,) if args.command=='demo' else args.seeds
        summaries=run_study(args.output,cases,configs,seeds)
        return 0 if all(s['successful_runs']==s['attempted_runs'] for s in summaries) else 2
    except (ValueError,OSError) as exc:
        parser.error(str(exc))


if __name__=='__main__':
    raise SystemExit(main())
