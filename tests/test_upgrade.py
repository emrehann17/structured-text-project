"""Offline contract tests. Every inference response below is a labeled test fixture."""
from copy import deepcopy
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import annotate_entities as annotation
import demo
import evaluate as ev
import llm_pipeline as p

VALID = {'category':'spor','entities':{'person':[], 'organization':[], 'location':[]}}
RAW = json.dumps(VALID)


def gold(**overrides):
    result = dict(id=1, person=[], organization=[], location=[], status='verified',
                  reviewer='Human test fixture', reviewed_at='2026-11-16', text_sha256=p.fingerprint('text'))
    result.update(overrides)
    return result


class UpgradeTests(unittest.TestCase):
    def test_only_format_differs(self):
        for temp in (0, 1.0):
            a, b = p.build_request('same news', 'prompt', temp), p.build_request('same news', 'schema', temp)
            self.assertNotIn('format', a)
            self.assertEqual(b.pop('format'), p.JSON_SCHEMA)
            self.assertEqual(a, b)

    def test_temperature_reaches_http(self):
        response = Mock(); response.json.return_value = {'response':RAW}
        with patch.object(p.requests, 'post', return_value=response) as post:
            p.call_ollama('text', 'prompt', 1.0)
        self.assertEqual(post.call_args.kwargs['json']['options']['temperature'], 1)
        self.assertNotIn('format', post.call_args.kwargs['json'])
        self.assertEqual(post.call_args.kwargs['json']['options']['seed'], 42)

    def test_invalid_configuration(self):
        for temp in (-1, float('nan'), float('inf')):
            with self.assertRaises(ValueError): p.build_options(temp)
        with self.assertRaises(ValueError): p.build_request('text', 'json')

    def test_selection(self):
        selected = ev.load_samples()
        self.assertEqual([s['id'] for s in selected], ev.select_evaluation_ids(ev.load_samples('all')))
        self.assertEqual(len({s['text'] for s in selected}), 100)
        self.assertFalse(set(s['id'] for s in selected) & set(s['id'] for s in ev.load_jsonl(ev.DATA_PATH)[:5]))

    def test_turkish_matching(self):
        self.assertEqual(ev.normalize_entity('  İZMİR  IŞIK_ Üniversitesi '), 'izmir ışık üniversitesi')
        self.assertEqual(ev.normalize_entity('I\u0307zmir'), 'izmir')
        self.assertEqual(ev.match_entities(['İZMİR','izmir', 'Ankara'], ['İzmir']), (1,1,0))
        self.assertEqual(ev.match_entities(['ABD', 'BM'], ['Amerika Birleşik Devletleri | ABD']), (1,1,0))
        self.assertEqual(ev.match_entities(['AB'], ['A.B.']), (0,1,1))
        self.assertEqual(ev.match_entities(['İzmir'], ['İzmir','izmir']), (1,0,0))
        with self.assertRaises(ValueError): ev.match_entities(['a'], ['a | b', 'b | c'])

    def test_prf_and_type_preservation(self):
        result = ev.entity_scores({1:{'person':['Ada','Ada'], 'organization':['İzmir'], 'location':[]}},
                                  {1:gold(person=['Ada'], location=['İzmir'])})
        self.assertEqual(result['micro']['f1_pct'], 50)
        self.assertEqual(result['micro']['precision_pct'], 50)
        self.assertEqual(result['micro']['recall_pct'], 50)
        self.assertEqual(ev.prf(2,1,3), {'tp':2,'fp':1,'fn':3,'precision_pct':66.67,'recall_pct':40.0,'f1_pct':50.0})
        self.assertEqual(result['person']['f1_pct'], 100)
        self.assertEqual(result['organization']['fp'], 1)
        self.assertEqual(result['location']['fn'], 1)
        self.assertEqual(ev.prf(0,0,0)['f1_pct'], 0)
        self.assertEqual(ev.entity_scores({1:None}, {1:gold(person=['Ada'])})['micro']['fn'], 1)

    def test_review_enforcement(self):
        for record in (gold(status='candidate'), gold(reviewer=None)):
            with self.assertRaises(ValueError): ev.entity_scores({1:None}, {1:record})
        self.assertFalse(ev.gold_status([1,2], {1:gold()})['complete'])
        with self.assertRaises(ValueError): ev.validate_gold_record(gold(person=['a']*6))

    def test_pending_f1_is_not_partial_score(self):
        sample = {'id':1,'text':'text','true_category':'spor'}
        with patch.object(p,'call_ollama',return_value={'response':RAW}): row=p.evaluate_sample(sample)
        summary=ev.analyze_results([sample],[row],{1:gold(status='candidate')})
        self.assertEqual(summary['entity_f1'], ev.PENDING_REVIEW)
        with self.assertRaises(ValueError): ev.analyze_results([sample],[row],{1:gold(text_sha256='wrong')})

    def test_review_never_auto_verifies(self):
        sample={'id':1,'text':'text','true_category':'spor'}
        candidate=gold(status='candidate',reviewer=None,reviewed_at=None)
        with redirect_stdout(StringIO()):
            self.assertIsNone(annotation.review(candidate,sample,'human',ask=lambda _:''))
        self.assertEqual(candidate['status'],'candidate')
        answers=iter(['','','','','y'])
        with redirect_stdout(StringIO()): reviewed=annotation.review(candidate,sample,'human',ask=lambda _:next(answers))
        self.assertEqual(reviewed['status'],'verified')
        self.assertEqual(candidate['status'],'candidate')

    def test_controlled_provenance(self):
        a=dict(model='qwen',model_digest='digest',quantization='quant',environment_sha256='env',
               prompt_version='v2',prompt_sha256='prompt',schema_sha256='schema',options=p.build_options(0),mode='prompt')
        b=deepcopy(a); b['mode']='schema'
        ev.check_controlled_pair(a,b)
        for key in ('model_digest','quantization','prompt_sha256','environment_sha256'):
            broken=deepcopy(b); broken[key]='different'
            with self.assertRaises(ValueError): ev.check_controlled_pair(a,broken)
        b=deepcopy(a); b['options']['temperature']=1
        ev.check_controlled_pair(a,b,temperature=True)
        b['options']['seed']=99
        with self.assertRaises(ValueError): ev.check_controlled_pair(a,b,temperature=True)

    def test_compare_rejects_order_mismatch(self):
        with TemporaryDirectory() as directory:
            root=Path(directory); (root/'results').mkdir()
            rows=[{'id':s['id']} for s in reversed(ev.load_samples())]
            (root/'results/prompt_only.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
            with patch.object(ev,'ROOT',root), self.assertRaises(ValueError): ev.compare_runs()

    def test_demo_novelty(self):
        samples=ev.load_jsonl(demo.DEMO_PATH); source=ev.load_jsonl(ev.DATA_PATH)
        self.assertEqual(len(demo.check_novelty(samples,source)),5)
        for text in (source[0]['text'], source[0]['text']+' Küçük bir ek.'):
            broken=deepcopy(samples); broken[0]['text']=text
            with self.assertRaises(ValueError): demo.check_novelty(broken,source)

    def test_demo_live_uses_inference_and_check_is_offline(self):
        with patch.object(sys,'argv',['demo.py','--check']), patch.object(demo,'evaluate_sample') as infer, redirect_stdout(StringIO()):
            demo.main()
        infer.assert_not_called()
        env={'model_digest':'test','details':{'quantization_level':'test'}}
        with TemporaryDirectory() as directory, patch.object(demo,'capture_environment',return_value=env), \
             patch.object(demo,'environment_fingerprint',return_value='test'), \
             patch.object(p,'call_ollama',return_value={'response':RAW}) as call, \
             patch.object(sys,'argv',['demo.py','--output',str(Path(directory)/'live.jsonl')]), redirect_stdout(StringIO()):
            demo.main()
            self.assertEqual(call.call_count,20)
            self.assertEqual(len(ev.load_jsonl(Path(directory)/'live.jsonl')),20)

    def test_new_run_overwrite_protection(self):
        with patch.object(ev,'capture_environment') as capture, self.assertRaises(ValueError):
            ev.run_experiment(ev.RESULT_PATH,ev.load_samples(),'schema',0)
        capture.assert_not_called()

    def test_interrupted_run_resumes_without_replacing_saved_output(self):
        environment=json.loads((ev.ROOT/'results/environment.json').read_text())
        samples=[{'id':i,'text':'text','true_category':'spor'} for i in (1,2)]
        with patch.object(p,'call_ollama',return_value={'response':RAW}):
            rows=[p.evaluate_sample(s,'prompt',0) for s in samples]
        with TemporaryDirectory() as directory, redirect_stdout(StringIO()), \
             patch.object(ev,'capture_environment',return_value=environment):
            path=Path(directory)/'interrupted.jsonl'
            with patch.object(ev,'evaluate_sample',side_effect=[rows[0],KeyboardInterrupt]), self.assertRaises(KeyboardInterrupt):
                ev.run_experiment(path,samples,'prompt',0)
            before=path.read_bytes()
            with patch.object(ev,'evaluate_sample',return_value=rows[1]) as infer:
                ev.run_experiment(path,samples,'prompt',0,resume=True)
            self.assertEqual(infer.call_count,1)
            self.assertTrue(path.read_bytes().startswith(before))
            self.assertEqual([r['id'] for r in ev.load_jsonl(path)],[1,2])
            self.assertEqual(json.loads(path.with_suffix('.metadata.json').read_text())['status'],'complete')
            with self.assertRaises(ValueError): ev.run_experiment(path,samples,'prompt',0,resume=True)

    def test_mixed_digest_and_modified_source_rejected(self):
        samples=ev.load_samples()[:2]
        rows=ev.load_jsonl(ev.ROOT/'results/prompt_only.jsonl')[:2]
        mixed=deepcopy(rows); mixed[1]['model_digest']='different'
        with self.assertRaises(ValueError): ev.analyze_results(samples,mixed)
        rows[0]['text_sha256']='changed'
        with self.assertRaises(ValueError): ev.analyze_results(samples,rows)

    def test_defense_changes_actual_request_and_preserves_source(self):
        original=Path(p.__file__).read_bytes()
        response=Mock(); response.json.return_value={'response':RAW}
        with TemporaryDirectory() as directory, redirect_stdout(StringIO()), \
             patch.object(demo,'capture_environment',return_value={'model_digest':'test','details':{'quantization_level':'test'}}), \
             patch.object(p.requests,'post',return_value=response) as post:
            demo.defense_demo(Path(directory)/'defense.jsonl',ev.load_jsonl(demo.DEMO_PATH)[-1])
        self.assertEqual(post.call_count,2)
        before,after=[call.kwargs['json'] for call in post.call_args_list]
        self.assertEqual(before.pop('format'),p.JSON_SCHEMA)
        self.assertNotIn('format',after)
        self.assertEqual(before,after)
        self.assertEqual(Path(p.__file__).read_bytes(),original)

    def test_real_comparison_recomputes_and_keeps_evidence(self):
        before={name:(ev.ROOT/path).read_bytes() for name,(path,_,_) in ev.RUNS.items()}
        with patch.object(ev,'write_json'),patch.object(ev,'save_comparison_figure'), \
             patch.object(p.requests,'post',side_effect=AssertionError('Offline only')):
            comparison,temperature=ev.compare_runs()
        self.assertEqual(comparison['samples'],100)
        self.assertEqual(comparison['paired_classification']['both_schema_valid'],98)
        self.assertEqual(comparison['paired_classification']['different_prediction_when_both_valid'],0)
        for name,(path,_,_) in ev.RUNS.items():
            self.assertEqual((ev.ROOT/path).read_bytes(),before[name])
            self.assertEqual(temperature['runs'][name]['total_requests'],100)

    def test_comparison_rejects_duplicate_and_missing_ids(self):
        rows=ev.load_jsonl(ev.ROOT/'results/prompt_only.jsonl')
        for broken in (rows+[rows[0]], rows[:10]+rows[11:]):
            with TemporaryDirectory() as directory:
                path=Path(directory)/'prompt_only.jsonl'
                path.write_text(''.join(json.dumps(r)+'\n' for r in broken))
                with self.assertRaises(ValueError): ev.compare_runs(directory)

    def test_category_agreement_respects_api_failure(self):
        row={'id':1,'true_category':'spor','raw_output':RAW,'response_received':True,'api_error':None}
        failed=dict(row,api_error='failed')
        counts=ev.category_agreement([failed],[row])
        self.assertEqual(counts['only_second_correct'],1)
        self.assertEqual(counts['both_schema_valid'],0)


if __name__=='__main__': unittest.main()
