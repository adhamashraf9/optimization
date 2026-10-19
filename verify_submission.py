"""Verify the submission using only Python's standard library; keep final data intact."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent


def run(*arguments):
    """Use this interpreter and the package root, including paths with spaces."""
    command = [sys.executable, '-B', '-S', *map(str, arguments)]
    print('\nRUN:', ' '.join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def main():
    if sys.version_info < (3, 9):
        raise RuntimeError('Python 3.9 or newer is required')
    manifest = ROOT/'MANIFEST.sha256.json'
    if manifest.exists():
        entries = json.loads(manifest.read_text(encoding='utf-8'))['files']
        for relative, expected in entries.items():
            path = (ROOT/relative).resolve()
            if ROOT not in path.parents:
                raise ValueError('Manifest path escapes package: ' + relative)
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError('File checksum mismatch: ' + relative)
        print('Verified', len(entries), 'packaged file hashes.', flush=True)
    else:
        raise FileNotFoundError('MANIFEST.sha256.json is missing')
    run('-m', 'unittest', 'discover', '-s', 'tests', '-v')
    run('-m', 'milestone3.final_experiments', 'verify')
    # Smoke outputs are disposable and never mixed into the frozen final study.
    with tempfile.TemporaryDirectory(prefix='team47_submission_') as temporary:
        temporary = Path(temporary)
        demo = temporary/'demo'
        benchmark = temporary/'benchmark'
        run('-m', 'milestone3', 'demo', '--case', ROOT/'cases/medium.json',
            '--budget', '2000', '--seed', '0', '--output', demo)
        from milestone3.validation import verify_study
        audited = verify_study(demo)
        if audited['verified_runs'] != 1 or audited['optimization_evaluations'] != 2000:
            raise ValueError('Unexpected demo audit totals')
        run('-m', 'milestone3', 'benchmark', '--budget', '500', '--seeds', '0:10',
            '--output', benchmark)
        data = json.loads((benchmark/'benchmark.json').read_text())
        if data['optimal_evaluation']['fitness'] != -16 or data['hit_rate'] != 1:
            raise ValueError('Exact-grid benchmark did not match expected results')
        if len(data['trials']) != 10 or any(t['evaluations'] != 500 for t in data['trials']):
            raise ValueError('Unexpected benchmark evaluation accounting')
    print('\nPASS: integrity, 43-test suite, frozen study, fresh demo and benchmark.')
    print('Submission reminder: the actual narrated video is a separate required deliverable.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print('FAIL:', error, file=sys.stderr)
        sys.exit(1)
