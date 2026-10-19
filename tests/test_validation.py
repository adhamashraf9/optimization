import json
from pathlib import Path
import tempfile
import unittest
from milestone3.cases import make_case
from milestone3.search import SAConfig
from milestone3.experiments import run_study
from milestone3.validation import verify_study


class ValidationTests(unittest.TestCase):
    def test_saved_study_recomputes_and_detects_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/'study'
            run_study(output,[make_case('small',101)],[('sa_feasible',SAConfig(budget=10))],(0,),progress=False)
            report=verify_study(output)
            self.assertEqual(report['verified_runs'],1)
            self.assertEqual(report['optimization_evaluations'],10)
            result_path=output/'small/sa_feasible/seed_0/result.json'
            result=json.loads(result_path.read_text())
            result['best_evaluation']['fitness']+=1
            result_path.write_text(json.dumps(result))
            with self.assertRaises(ValueError): verify_study(output)

    def test_incomplete_study_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)
            (output/'manifest.json').write_text('{"complete":false}')
            with self.assertRaises(ValueError): verify_study(output)


if __name__ == '__main__': unittest.main()
