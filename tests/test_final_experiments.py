from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest

from milestone3.final_experiments import build_configuration, freeze, validate_freeze, verify_final_study
from milestone3.experiments import run_study, summarize
from milestone3.search import SAConfig, solve_sa
from milestone3.cases import make_case
from milestone3.validation import verify_study

ROOT=Path(__file__).resolve().parents[1]


class FinalExperimentTests(unittest.TestCase):
    def test_scope_and_settings(self):
        config=build_configuration(ROOT, 'test_v1', 'pilot evidence')
        self.assertEqual(config['expected_runs'],105)
        main,sensitivity,challenging=config['studies']
        self.assertEqual(main['budgets'],{'small':2000,'medium':4000,'large':5000})
        self.assertEqual(main['seeds'],list(range(100,110)))
        self.assertEqual(list(main['configs']),['sa_feasible','random'])
        self.assertEqual(sensitivity['cases'],['medium'])
        self.assertEqual(sensitivity['seeds'],list(range(200,205)))
        self.assertEqual(len(sensitivity['configs']),5)
        self.assertEqual(challenging['cases'],['clustered','separated'])
        self.assertEqual(len(challenging['seeds']),5)
        self.assertEqual(config['neighborhood']['probabilities'],{'3d':.8,'altitude':.2,'coordinated':0.})

    def test_frozen_hash_and_input_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'freeze.json'
            data=build_configuration(ROOT,'test_v1','pilot evidence')
            digest=freeze(path,data)
            loaded,actual=validate_freeze(path,ROOT)
            self.assertEqual(actual,digest)
            self.assertEqual(loaded,data)
            with self.assertRaises(FileExistsError): freeze(path,data)
            path.write_text(path.read_text()+' ')
            with self.assertRaises(ValueError): validate_freeze(path,ROOT)
            # A fresh self-consistent config must still detect bad case hashes.
            data['cases']['medium']['sha256']='0'*64
            other=Path(d)/'other.json'; freeze(other,data)
            with self.assertRaises(ValueError): validate_freeze(other,ROOT)
            data=build_configuration(ROOT,'test_v1','pilot evidence')
            data['source_hashes']['milestone3/search.py']='0'*64
            source=Path(d)/'source.json'; freeze(source,data)
            with self.assertRaises(ValueError): validate_freeze(source,ROOT)

    def test_guard_failure_before_or_after_solver_prevents_export(self):
        for fail_on in (1,2):
            with self.subTest(fail_on=fail_on), tempfile.TemporaryDirectory() as d:
                output=Path(d)/'study'; calls=[]
                def guard():
                    calls.append(1)
                    if len(calls)==fail_on: raise ValueError('changed frozen source')
                with self.assertRaises(ValueError):
                    run_study(output,[make_case('small',101)],
                              [('sa_feasible',SAConfig(budget=4))],(100,),progress=False,guard=guard)
                self.assertEqual(len(calls),fail_on)
                self.assertFalse((output/'small/sa_feasible/seed_100').exists())
                self.assertFalse(json.loads((output/'manifest.json').read_text())['complete'])

    def test_case_budgets_metadata_and_audit(self):
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/'study'
            metadata={'configuration_hash':'a'*64,'version':'test_v1','study':'test'}
            run_study(output,[make_case('small',101),make_case('medium',102)],
                      [('sa_feasible',SAConfig(budget=10))],(100,),progress=False,
                      budget_by_case={'small':4,'medium':6},experiment_metadata=metadata)
            self.assertEqual(verify_study(output)['optimization_evaluations'],10)
            path=output/'small/sa_feasible/seed_100/metrics.json'
            metrics=json.loads(path.read_text())
            self.assertEqual(metrics['experiment'],metadata)
            metrics['experiment']['configuration_hash']='b'*64
            path.write_text(json.dumps(metrics))
            with self.assertRaises(ValueError): verify_study(output)

    def test_no_search_budget_not_successful(self):
        r=solve_sa(make_case('small',101),SAConfig(budget=1),100)
        self.assertEqual(summarize([('sa_feasible',100,r)])[0]['successful_runs'],0)

    def test_final_audit_binds_manifest_to_frozen_definition(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); output=root/'study'
            cfg=SAConfig(budget=4); p=make_case('small',101)
            study={'name':'test','output':'study','cases':['small'],
                   'configs':{'sa_feasible':asdict(cfg)},'seeds':[100],
                   'budgets':{'small':4},'expected_runs':1}
            data={'version':'test_v1','cases':{'small':{'definition':json.loads(json.dumps(p.to_dict()))}}}
            digest='a'*64
            metadata={'configuration_hash':digest,'version':'test_v1','study':'test'}
            run_study(output,[p],[('sa_feasible',cfg)],(100,),progress=False,experiment_metadata=metadata)
            self.assertEqual(verify_final_study(root,study,data,digest)['verified_runs'],1)
            study['seeds']=[101]
            with self.assertRaises(ValueError): verify_final_study(root,study,data,digest)


if __name__=='__main__': unittest.main()
