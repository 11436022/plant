import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).with_name('benchmark_ai.py')
if not SCRIPT.exists():
    SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'benchmark_ai.py'
SPEC = importlib.util.spec_from_file_location('benchmark_ai', SCRIPT)
benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(benchmark)

CASE = {'id':'case-1','group':'supported','expected_crop':'tomato',
        'expected_category':'disease','expected_status':'early-blight',
        'target_policy':'known_label_or_abstain'}
MATCH = {'crop_name':'tomato','category':'disease','status_name':'early-blight','confidence':.1}


@pytest.mark.parametrize('text,expected', [
    ('{"category":"unknown"}',{'category':'unknown'}),
    ('```json\n{"category":"unknown"}\n```',{'category':'unknown'}),
    ('[]',None),('null',None),('not json',None),(None,None),
])
def test_parse_candidate(text,expected):
    assert benchmark.parse_candidate(text) == expected


def test_matching_uses_labels_not_model_confidence():
    assert benchmark.score(CASE,MATCH)['outcome'] == 'label_match'
    wrong = dict(MATCH,status_name='late-blight',confidence=.999)
    assert benchmark.score(CASE,wrong)['outcome'] == 'incorrect_known_label'


def test_unknown_is_not_counted_as_correct_supported_label():
    assert benchmark.score(CASE,dict(MATCH,category='unknown'))['outcome'] == 'abstained'


def test_no_result_is_not_an_abstention():
    assert benchmark.score(CASE,None)['outcome'] == 'no_structured_result'


def test_out_of_scope_requires_abstention():
    case = dict(CASE,group='out_of_scope',target_policy='abstain')
    assert benchmark.score(case,MATCH)['outcome'] == 'incorrect_known_label'
    assert benchmark.score(case,dict(MATCH,category='unknown'))['outcome'] == 'abstained'


def make_row(case_id,status,final):
    return {'case_id':case_id,'model':'a','status':status,'final':final,
        'final_score':benchmark.score(CASE,final),'raw_score':benchmark.score(CASE,final),
        'inference_seconds':4,'calls':[]}


def test_metrics_keep_abstentions_errors_and_missing_cases_distinct():
    cases = [dict(CASE,id=f'case-{i}') for i in range(4)]
    rows = [make_row('case-0','ok',MATCH),make_row('case-1','ok',dict(MATCH,category='unknown')),
        make_row('case-2','error',None)]
    summary = benchmark.summarize(cases,rows,'a')
    assert summary['supported_status_agreement_received'] == benchmark.ratio(1,2)
    assert summary['supported_status_yield_attempted_including_errors'] == benchmark.ratio(1,3)
    assert summary['service_or_parse_errors'] == 1
    assert summary['supported_abstentions'] == 1
    assert summary['not_run'] == 1


def test_empty_summary_has_no_fabricated_zero_accuracy():
    summary = benchmark.summarize([CASE],[],'a')
    assert summary['supported_status_agreement_received']['value'] is None
    assert summary['inference_seconds']['median'] is None
    assert summary['not_run'] == 1


def test_advice_source_fields_are_not_professional_approval():
    result = dict(MATCH,treatment='10 ppm',reference_source='x',reference_url='https://example.org',
        reference_record_id='1',requires_review=False)
    audit = benchmark.advice_audit(result)
    assert audit['dosage_pattern'] is True
    assert audit['unverified_source'] is False
    assert audit['professional_correctness'] == 'not independently evaluated'


def test_blank_source_is_unverified():
    audit = benchmark.advice_audit(dict(MATCH,reference_source=' ',reference_url='https://example.org',reference_record_id='1'))
    assert audit['unverified_source'] is True


def test_report_writes_complete_json(tmp_path):
    path = tmp_path/'result.json'
    benchmark.write_report(path,{'status':'not_run'})
    assert json.loads(path.read_text()) == {'status':'not_run'}
    assert not path.with_suffix('.json.pending').exists()


def test_model_wrapper_records_and_bounds_calls(monkeypatch):
    monkeypatch.setattr(benchmark.time,'sleep',lambda _:None)
    seen = []
    def generate(**kwargs):
        seen.append(kwargs)
        return SimpleNamespace(text='{}',model_version='a-001',response_id='response-1',usage_metadata=None,candidates=[])
    client = SimpleNamespace(models=SimpleNamespace(generate_content=generate))
    wrapper = benchmark.RecordedModels(client,'a','secret',{'temperature':0},0,1)
    wrapper.generate_content(model='production',contents=['fixed prompt',object()])
    assert seen[0]['model'] == 'a'
    assert wrapper.calls[0]['prompt_sha256'] == benchmark.digest(b'fixed prompt')
    assert wrapper.calls[0]['model_version'] == 'a-001'
    with pytest.raises(RuntimeError,match='budget'):
        wrapper.generate_content(model='production',contents=['fixed prompt'])
    assert len(seen) == 1


def test_quota_error_stops_model_and_redacts_key(monkeypatch):
    monkeypatch.setattr(benchmark.time,'sleep',lambda _:None)
    class QuotaError(Exception):
        code = 429
    def generate(**kwargs):
        raise QuotaError('quota key=private-key')
    client = SimpleNamespace(models=SimpleNamespace(generate_content=generate))
    wrapper = benchmark.RecordedModels(client,'a','private-key',{},0,18)
    with pytest.raises(QuotaError):
        wrapper.generate_content(model='production',contents=['prompt'])
    assert 'private-key' not in json.dumps(wrapper.calls)
    assert wrapper.stopped
    with pytest.raises(RuntimeError,match='stopped'):
        wrapper.generate_content(model='production',contents=['prompt'])
    assert wrapper.total == 1
