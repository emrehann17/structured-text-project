"""Offline behavioral tests. All small examples here are artificial test fixtures."""
from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import llm_pipeline as p
import evaluate as ev
import annotate_entities as annotation
import build_report as report
import demo

VALID = {'category':'spor', 'entities':{'person':[], 'organization':[], 'location':['İSTANBUL']}}
RAW = json.dumps(VALID, ensure_ascii=False)
SAMPLE = {'id':1, 'text':'İSTANBUL ve Ankara şehirleri.', 'true_category':'spor'}


def gold_record(status='completed', names=None):
    return {'id':1, 'annotation_method':'manual_from_text', 'status':status,
            'reviewer':'Test fixture' if status=='completed' else None,
            'reviewed_at':'2026-11-18' if status=='completed' else None,
            'text_sha256':p.fingerprint(SAMPLE['text']),
            'person':[], 'organization':[], 'location':names if names is not None else ['istanbul']}


def response(raw=RAW, error=None):
    row={'id':1, 'true_category':'spor', 'raw_output':raw, 'response_received':raw is not None,
         'api_error':error, 'elapsed_seconds':1}
    row.update(p.evaluate_response(raw or '', 'spor'))
    return row


class PipelineTests(unittest.TestCase):
    def test_only_format_differs(self):
        for temperature in (0,1):
            plain=p.build_request('haber','prompt',temperature)
            schema=p.build_request('haber','schema',temperature)
            self.assertNotIn('format',plain)
            self.assertEqual(schema.pop('format'),p.JSON_SCHEMA)
            self.assertEqual(plain,schema)
            self.assertEqual(plain['options']['seed'],42)
            self.assertEqual(plain['options']['top_k'],40)
            self.assertEqual(plain['options']['top_p'],0.9)

    def test_temperature_only_changes_temperature(self):
        a=p.build_request('haber','prompt',0); b=p.build_request('haber','prompt',1)
        a['options'].pop('temperature'); b['options'].pop('temperature')
        self.assertEqual(a,b)

    def test_invalid_mode_and_temperature_rejected(self):
        with self.assertRaises(ValueError): p.build_request('x','bad')
        for temperature in (-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError): p.build_options(temperature)

    def test_raw_and_cleaned_json_are_separate(self):
        for raw,raw_ok in ((RAW,True),(f'```json\n{RAW}\n```',False),(f'Here is JSON: {RAW}',False)):
            parsed,raw_valid,clean_valid=p.parse_json_response(raw)
            self.assertEqual(parsed,VALID)
            self.assertEqual(raw_valid,raw_ok)
            self.assertTrue(clean_valid)
        for raw in ('', '{', 'No JSON'):
            self.assertEqual(p.parse_json_response(raw),(None,False,False))

    def test_schema_and_semantics_are_separate(self):
        wrong=deepcopy(VALID); wrong['category']='ekonomi'
        flags=p.evaluate_response(json.dumps(wrong),'spor')
        self.assertTrue(flags['schema_valid']); self.assertFalse(flags['category_correct'])
        for obj in ({},[],{'category':'spor'},dict(VALID,category='other'),dict(VALID,extra=True)):
            flags=p.evaluate_response(json.dumps(obj),'spor')
            self.assertTrue(flags['raw_json_valid']); self.assertFalse(flags['schema_valid'])
        bad=deepcopy(VALID); bad['entities']['person']=[7]
        self.assertFalse(p.validate_schema(bad))

    def test_truncation_does_not_invent_fields(self):
        flags=p.evaluate_response(RAW[:-1],'spor')
        self.assertFalse(flags['schema_valid'])
        self.assertFalse(flags['category_correct'])

    def test_actual_http_contract_is_local(self):
        payload=Mock(); payload.json.return_value={'response':RAW}
        with patch.object(p.requests,'post',return_value=payload) as post:
            row=p.evaluate_sample(SAMPLE,'prompt',1)
        self.assertEqual(post.call_args.args[0],'http://localhost:11434/api/generate')
        self.assertNotIn('format',post.call_args.kwargs['json'])
        self.assertEqual(post.call_args.kwargs['timeout'],(5,300))
        self.assertTrue(row['raw_json_valid'])

    def test_api_errors_do_not_stop_evaluation(self):
        with patch.object(p.requests,'post',side_effect=p.requests.Timeout('test fixture')):
            row=p.evaluate_sample(SAMPLE)
        self.assertIsNotNone(row['api_error'])
        self.assertFalse(row['response_received'])
        self.assertFalse(row['schema_valid'])


class EvaluationTests(unittest.TestCase):
    def test_all_requests_remain_in_denominator(self):
        samples=[dict(SAMPLE,id=i) for i in range(4)]
        rows=[dict(response(raw),id=i) for i,raw in enumerate((RAW,f'```json\n{RAW}\n```','{}',None))]
        rows[-1]['api_error']='Test fixture failure'
        result=ev.analyze_results(samples,rows)
        self.assertEqual(result['raw_json_success_pct'],50)
        self.assertEqual(result['clean_json_success_pct'],75)
        self.assertEqual(result['schema_success_pct'],50)
        self.assertEqual(result['classification_accuracy_pct'],50)

    def test_turkish_exact_sets_and_type_errors(self):
        self.assertEqual(ev.normalize_entity('İSTANBUL'), 'istanbul')
        self.assertEqual(ev.normalize_entity('IŞIK'), 'ışık')
        self.assertEqual(ev.match_entities(['İSTANBUL','istanbul'],['istanbul']),(1,0,0))
        self.assertEqual(ev.match_entities(['İSTAN'],['istanbul']),(0,1,1))
        scores=ev.entity_scores({1:{'person':['İSTANBUL']}},{1:gold_record()})
        self.assertEqual(scores['micro']['tp'],0)
        self.assertEqual(scores['micro']['fp'],1)
        self.assertEqual(scores['micro']['fn'],1)

    def test_gold_change_changes_f1_and_fingerprint(self):
        before=ev.analyze_results([SAMPLE],[response()],{1:gold_record()})
        after=ev.analyze_results([SAMPLE],[response()],{1:gold_record(names=['Ankara'])})
        self.assertEqual(before['entity_f1']['micro']['f1_pct'],100)
        self.assertEqual(after['entity_f1']['micro']['f1_pct'],0)
        self.assertNotEqual(before['gold_sha256'],after['gold_sha256'])
        for metric in ev.METRICS:
            self.assertEqual(before[metric+'_pct'],after[metric+'_pct'])

    def test_draft_is_not_empty_gold_or_a_zero_score(self):
        summary=ev.analyze_results([SAMPLE],[response()],{1:gold_record('draft',[])})
        self.assertEqual(summary['entity_f1'],ev.PENDING_REVIEW)
        self.assertFalse(summary['entity_gold']['complete'])

    def test_duplicate_missing_or_wrong_reference_results_rejected(self):
        for rows in ([],[response(),response()],[dict(response(),true_category='ekonomi')]):
            with self.assertRaises(ValueError): ev.analyze_results([SAMPLE],rows)

    def test_old_statuses_and_wrong_text_are_rejected(self):
        old=gold_record(); old['annotation_method']='model_suggestions'
        with self.assertRaises(ValueError): ev.validate_gold_record(old)
        wrong=gold_record(); wrong['text_sha256']='wrong'
        with self.assertRaises(ValueError): ev.analyze_results([SAMPLE],[response()],{1:wrong})


class AnnotationAndReportTests(unittest.TestCase):
    def test_full_refresh_changes_metrics_plot_and_report_after_gold_edit(self):
        environment={key:'test fixture' for key in
                     ('ollama_version','model','model_digest','platform','python','gpu','model_template','model_system')}
        environment['details']={'quantization_level':'TEST'}
        environment['model_parameters']=None
        signature=ev.environment_fingerprint(environment)
        with TemporaryDirectory() as directory:
            directory=Path(directory)
            for filename,mode,temperature in ev.RUNS.values():
                row=response()
                row.update(mode=mode,temperature=temperature,options=p.build_options(temperature),
                           format_sent=mode=='schema',model=p.MODEL,prompt_version=p.PROMPT_VERSION,
                           prompt_sha256=p.fingerprint(p.build_prompt('')),schema_sha256=p.fingerprint(p.JSON_SCHEMA),
                           model_digest=environment['model_digest'],quantization='TEST',environment_sha256=signature,
                           text_sha256=p.fingerprint(SAMPLE['text']))
                (directory/filename).write_text(json.dumps(row)+'\n')
                ev.write_json((directory/filename).with_suffix('.metadata.json'),
                              {'status':'complete','sample_ids':[1],'environment':environment,'environment_after':environment})
            def rebuild_with(record):
                gold={1:record}
                with patch.object(ev,'load_samples',return_value=[SAMPLE]), \
                     patch.object(ev,'load_gold',return_value=gold),patch.object(report,'load_gold',return_value=gold), \
                     patch.object(p.requests,'post',side_effect=AssertionError('Refresh must be offline')),redirect_stdout(StringIO()):
                    result=report.rebuild(directory)
                paths=['metrics.json','metrics.png','report/technical_report.md','report/technical_report.pdf']
                return result,{name:(directory/name).read_bytes() for name in paths}
            before,old_files=rebuild_with(gold_record())
            after,new_files=rebuild_with(gold_record(names=['Ankara']))
            self.assertEqual(before['runs']['prompt_only']['entity_f1']['micro']['f1_pct'],100)
            self.assertEqual(after['runs']['prompt_only']['entity_f1']['micro']['f1_pct'],0)
            for name in old_files:
                self.assertNotEqual(old_files[name],new_files[name],name)
            pending,_=rebuild_with(gold_record('draft',[]))
            self.assertEqual(pending['runs']['prompt_only']['entity_f1'],ev.PENDING_REVIEW)

    def test_save_requires_human_confirmation_and_source_names(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/'gold.jsonl'
            path.write_text(json.dumps(gold_record('draft',[]))+'\n')
            initial=path.read_bytes()
            payload={'reviewer':'Test fixture','confirmed':True,'person':[],'organization':[],'location':['İSTANBUL']}
            for invalid in (dict(payload,confirmed=False),dict(payload,reviewer=''),dict(payload,location=['Paris'])):
                with self.assertRaises(ValueError): annotation.save_annotation(SAMPLE,invalid,path)
                self.assertEqual(path.read_bytes(),initial)
            with patch.object(p.requests,'post',side_effect=AssertionError('Manual annotation must never call a model')):
                record=annotation.save_annotation(SAMPLE,payload,path)
            self.assertEqual(record['status'],'completed')
            self.assertEqual(ev.load_gold(path)[1]['location'],['İSTANBUL'])

    def test_blank_initial_project_annotations_have_no_suggestions(self):
        # Works both before and after genuine manual progress: drafts contain no suggestion metadata.
        for record in ev.load_gold().values():
            self.assertEqual(record['annotation_method'],'manual_from_text')
            self.assertNotIn('candidate_source',record)
            self.assertNotIn('review_flags',record)

    def test_report_reflects_gold_change_and_pending_state(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)
            def document(record):
                gold={1:record}
                summary=ev.analyze_results([SAMPLE],[response()],gold)
                results={'runs':{k:deepcopy(summary) for k in ev.RUNS},
                         'entity_gold':summary['entity_gold'],'gold_sha256':summary['gold_sha256'],
                         'paired_classification':None}
                with patch.object(report,'load_gold',return_value=gold):
                    return report.report_markdown(results,path)
            before=document(gold_record())
            after=document(gold_record(names=['Ankara']))
            pending=document(gold_record('draft',[]))
            self.assertIn('Entity micro-F1 at T=0 is 100%',before)
            self.assertIn('Entity micro-F1 at T=0 is 0%',after)
            self.assertIn('INCOMPLETE',pending)
            self.assertNotIn('Entity micro-F1 at T=0 is',pending)

    def test_failed_rebuild_removes_stale_derived_artifacts(self):
        with TemporaryDirectory() as directory:
            path=Path(directory); (path/'report').mkdir()
            files=[path/'metrics.json',path/'metrics.png',path/'report/technical_report.md',path/'report/technical_report.pdf']
            for target in files: target.write_text('old stale score')
            with patch.object(report,'compare_runs',side_effect=ValueError('Test fixture failure')):
                with self.assertRaises(ValueError): report.rebuild(path)
            self.assertTrue(all(not target.exists() for target in files))

    def test_a1_preserves_source_and_works_without_completed_gold(self):
        source=Path(ev.__file__); original=source.read_bytes(); output=StringIO()
        with patch.object(ev,'load_gold',return_value={1:gold_record('draft',[])}), \
             patch.object(ev,'load_samples',return_value=[SAMPLE]), redirect_stdout(output), \
             patch.object(p.requests,'post',side_effect=AssertionError('A1 is offline')):
            demo.defense_demo()
        self.assertEqual(source.read_bytes(),original)
        self.assertIn('before teaching example: istanbul (1, 0, 0)',output.getvalue())
        self.assertIn('after teaching example: İSTANBUL (0, 1, 1)',output.getvalue())
        self.assertIn('awaits 100 completed manual annotations',output.getvalue())

    def test_live_demo_calls_all_modes_and_temperatures(self):
        environment={'model_digest':'test-fixture'}
        with TemporaryDirectory() as directory, patch.object(ev,'capture_environment',return_value=environment), \
             patch.object(p,'evaluate_sample',return_value=response()) as infer, redirect_stdout(StringIO()):
            output=Path(directory)/'live.jsonl'
            demo.live_demo(output)
            self.assertEqual(infer.call_count,20)
            self.assertEqual({(c.args[1],c.args[2]) for c in infer.call_args_list},
                             {('prompt',0),('schema',0),('prompt',1),('schema',1)})
            self.assertEqual(len(ev.load_jsonl(output)),20)
            with self.assertRaises(ValueError): demo.live_demo(output)


if __name__=='__main__':
    unittest.main()
