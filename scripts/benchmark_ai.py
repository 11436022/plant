"""Bounded paired pilot using the real diagnosis service and isolated reference DB.

No production data, prompts, thresholds, or files are changed. Public test images
are selected before inference. Results are dataset-label agreement, not proof of
agronomic correctness or absence of hallucinations.
"""

import argparse
import contextlib
import hashlib
import io
import importlib.metadata
import json
import math
import os
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fetch_images(manifest, destination):
    import requests
    from PIL import Image, ImageDraw
    destination.mkdir(parents=True,exist_ok=True)
    for case in manifest['cases']:
        case_id = case['id']
        if not re.fullmatch(r'[a-z0-9-]+',case_id):
            raise ValueError('Unsafe case ID')
        path = destination/f'{case_id}.bin'
        if path.exists():
            content = path.read_bytes()
        elif case_id == 'nonplant-checkerboard' and 'fixture' in case:
            im = Image.new('RGB',(640,480),'white')
            draw = ImageDraw.Draw(im)
            for x in range(0,640,40):
                for y in range(0,480,40):
                    if (x//40+y//40)%2 == 0:
                        draw.rectangle((x,y,x+39,y+39),fill='black')
            buf = io.BytesIO()
            im.save(buf,format='PNG')
            content = buf.getvalue()
        else:
            url = urlsplit(case['url'])
            if url.scheme != 'https' or url.netloc != 'raw.githubusercontent.com' or url.query or url.fragment:
                raise ValueError('Only pinned public GitHub image URLs are permitted')
            if not re.match(r'^/pratikkayal/PlantDoc-Dataset/[0-9a-f]{40}/test/',url.path):
                raise ValueError('Unexpected dataset URL or mutable revision')
            with requests.get(case['url'],timeout=40,stream=True) as response:
                response.raise_for_status()
                content = bytearray()
                for chunk in response.iter_content(65536):
                    content.extend(chunk)
                    if len(content)>10*1024*1024:
                        raise ValueError('Image download exceeds 10 MiB')
        if digest(content) != case['image']['sha256']:
            raise ValueError(f'Image hash mismatch: {case_id}')
        if not path.exists():
            path.write_bytes(content)


def parse_candidate(text):
    try:
        value = json.loads((text or '').replace('```json', '').replace('```', '').strip())
    except (ValueError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def score(case, result):
    if not isinstance(result, dict):
        return {'outcome': 'no_structured_result', 'crop_correct': None}
    unknown = result.get('category') == 'unknown'
    crop_correct = (result.get('crop_name') == case['expected_crop']) if case['expected_crop'] else None
    if case['target_policy'] == 'abstain':
        outcome = 'abstained' if unknown else 'incorrect_known_label'
    elif unknown:
        outcome = 'abstained'
    else:
        exact = crop_correct and result.get('category') == case['expected_category'] and result.get('status_name') == case['expected_status']
        outcome = 'label_match' if exact else 'incorrect_known_label'
    return {'outcome': outcome, 'crop_correct': crop_correct}


def ratio(numerator, denominator):
    return {'numerator': numerator, 'denominator': denominator,
            'value': numerator / denominator if denominator else None}


def generation_config(thinking_level=None):
    if thinking_level not in (None, 'minimal', 'low', 'medium', 'high'):
        raise ValueError('Unsupported thinking level')
    thinking = {'thinking_level': thinking_level} if thinking_level else {'thinking_budget': 0}
    return {'temperature': 0, 'max_output_tokens': 4096, 'thinking_config': thinking}


def summarize(cases, rows, model):
    selected = [r for r in rows if r['model'] == model]
    by_id = {c['id']: c for c in cases}
    attempted = [r for r in selected if r['status'] not in {'not_run', 'input_rejected'}]
    parsed = [r for r in attempted if isinstance(r.get('final'), dict)]
    plant = [r for r in parsed if by_id[r['case_id']]['expected_crop']]
    supported = [r for r in parsed if by_id[r['case_id']]['group'] == 'supported']
    supported_attempted = [r for r in attempted if by_id[r['case_id']]['group'] == 'supported']
    guards = [r for r in parsed if by_id[r['case_id']]['target_policy'] == 'abstain']
    matches = sum(r['final_score']['outcome'] == 'label_match' for r in supported)
    latencies = sorted(r['inference_seconds'] for r in parsed)
    calls = [call for row in selected for call in row.get('calls', [])]
    return {
        'planned': len(cases), 'attempted': len(attempted), 'structured_results': len(parsed),
        'not_run': len(cases) - len(selected) + sum(r['status'] == 'not_run' for r in selected),
        'input_rejected': sum(r['status'] == 'input_rejected' for r in selected),
        'service_or_parse_errors': sum(r['status'] == 'error' for r in attempted),
        'crop_agreement_received': ratio(sum(r['final_score']['crop_correct'] is True for r in plant), len(plant)),
        'supported_status_agreement_received': ratio(matches, len(supported)),
        'supported_status_yield_attempted_including_errors': ratio(matches, len(supported_attempted)),
        'supported_abstentions': sum(r['final_score']['outcome'] == 'abstained' for r in supported),
        'supported_incorrect_known': sum(r['final_score']['outcome'] == 'incorrect_known_label' for r in supported),
        'guard_abstention_received': ratio(sum(r['final_score']['outcome'] == 'abstained' for r in guards), len(guards)),
        'raw_to_final': [{'case_id':r['case_id'], 'raw':r['raw_score']['outcome'], 'final':r['final_score']['outcome']} for r in parsed],
        'unverified_advice': sum(r.get('advice', {}).get('unverified_source') is True for r in parsed),
        'advice_with_dosage_pattern': sum(r.get('advice', {}).get('dosage_pattern') is True for r in parsed),
        'inference_seconds': {'n':len(latencies), 'median':statistics.median(latencies) if latencies else None,
            'p95_nearest_rank':latencies[math.ceil(.95*len(latencies))-1] if latencies else None},
        'api_requests':len(calls),
        'api_request_errors':sum('error' in c for c in calls),
        'usage':{key:sum(c.get('usage', {}).get(key) or 0 for c in calls) for key in
            ('prompt_token_count','candidates_token_count','thoughts_token_count','total_token_count')},
    }


class RecordedModels:
    """Intercept model choice and record requests without storing credentials."""
    def __init__(self, client, model, key, config, interval, max_calls):
        self.client, self.model, self.key, self.config = client, model, key, config
        self.interval, self.max_calls = interval, max_calls
        self.calls = []
        self.total = 0
        self.last_start = 0.0
        self.slept = 0.0
        self.stopped = None

    def generate_content(self, *, model, contents, **kwargs):
        if self.stopped or self.total >= self.max_calls:
            raise RuntimeError(self.stopped or 'Configured API request budget reached')
        wait = max(0.0, self.interval - (time.perf_counter() - self.last_start))
        time.sleep(wait)
        self.slept += wait
        self.last_start = time.perf_counter()
        self.total += 1
        prompt = contents[0]
        record = {'model':self.model, 'production_model_argument':model,
            'started_at':datetime.now(timezone.utc).isoformat(),
            'prompt_sha256':digest(prompt.encode()), 'prompt':prompt, 'config':self.config}
        self.calls.append(record)
        start = time.perf_counter()
        try:
            response = self.client.models.generate_content(model=self.model, contents=contents, config=self.config, **kwargs)
            record.update({'text':response.text, 'model_version':response.model_version,
                'response_id':response.response_id,
                'usage':response.usage_metadata.model_dump(mode='json',exclude_none=True) if response.usage_metadata else {},
                'finish_reasons':[str(c.finish_reason) for c in response.candidates or []]})
            return response
        except Exception as exc:
            code = getattr(exc, 'code', None)
            message = str(exc).replace(self.key, '[REDACTED]')
            message = re.sub(r'AIza[\w-]+', '[REDACTED]', message)
            record['error'] = {'type':type(exc).__name__, 'code':code, 'message':message[:3000]}
            if code in (400,401,403,404,429):
                self.stopped = f'Model stopped after HTTP {code}; no automatic retry or key rotation'
            raise
        finally:
            record['seconds'] = time.perf_counter() - start


def advice_audit(result):
    if not isinstance(result, dict) or result.get('category') not in {'disease','pest'}:
        return {'applicable': False}
    traceable = all(str(result.get(k) or '').strip() for k in ('reference_source','reference_url','reference_record_id'))
    return {'applicable': True, 'unverified_source': not traceable,
        'requires_review': result.get('requires_review'),
        'dosage_pattern': bool(re.search(r'\d+(?:\.\d+)?\s*(?:%|\u500d|ppm|mg|ml|mL)', str(result.get('treatment') or ''))),
        'professional_correctness': 'not independently evaluated'}


def write_report(path, report):
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix+'.pending')
    pending.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    pending.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--images',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--key-file',type=Path)
    parser.add_argument('--models',nargs='+',default=['gemini-2.5-flash','gemini-2.5-flash-lite'])
    parser.add_argument('--thinking-level',choices=['minimal','low','medium','high'],
        help='Explicit newer-model setting; replaces legacy budget=0 and is recorded as a protocol difference')
    parser.add_argument('--max-calls-per-model',type=int,default=18)
    parser.add_argument('--interval',type=float,default=13)
    parser.add_argument('--free-tier-confirmed',action='store_true')
    parser.add_argument('--preflight-only',action='store_true')
    parser.add_argument('--fetch-images',action='store_true',help='Fetch original public images by pinned manifest URL and verify hashes')
    args = parser.parse_args()
    if args.report.exists():
        parser.error('Refusing to overwrite an existing evaluation report; use a new path')
    if len(set(args.models)) != len(args.models) or not args.models:
        parser.error('Model IDs must be unique')
    if args.interval < 0 or args.max_calls_per_model < 1:
        parser.error('Invalid request limits')
    root = args.root.resolve()
    sys.path.insert(0,str(root))
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    cases = manifest['cases']
    if len({c['id'] for c in cases}) != len(cases):
        raise ValueError('Duplicate case IDs')
    if len({c['image']['sha256'] for c in cases}) != len(cases):
        raise ValueError('Duplicate source images would distort sample counts')
    if args.fetch_images:
        fetch_images(manifest,args.images)
    key = args.key_file.read_text(encoding='utf-8').strip() if args.key_file else os.getenv('GEMINI_API_KEY','')
    if not args.preflight_only and (not key or not args.free_tier_confirmed):
        parser.error('Live runs require a test key and explicit free-tier verification')
    os.environ['GEMINI_API_KEY'] = key or 'offline-preflight-no-network'
    for name,value in {'DB_USER':'evaluation','DB_PASSWORD':'evaluation','DB_HOST':'127.0.0.1','DB_NAME':'evaluation_unused'}.items():
        os.environ[name] = value
    from fastapi import HTTPException
    from google import genai
    from google.genai import types
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.db.models import Base
    from app.services import ai, rag
    from app.services.files import validate_image_content
    from seed import upsert_reference_data
    reference_data = json.loads((root/'data.json').read_text(encoding='utf-8'))
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    db = Session(engine)
    upsert_reference_data(db, reference_data)
    names = ai.get_reference_lists(db)
    config = generation_config(args.thinking_level)
    # The unavailable production index is not replaced with fabricated retrieval.
    if (root/'knowledge_base.faiss').exists() or (root/'knowledge_content.json').exists():
        raise RuntimeError('This preregistered pilot expects no RAG index; define a separate RAG protocol before testing')
    assert rag.faiss_index is None and not rag.knowledge_content
    report = {'schema_version':1, 'created_at':datetime.now(timezone.utc).isoformat(),
        'code_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        'ai_service_sha256':digest((root/'app/services/ai.py').read_bytes()),
        'reference_data_sha256':digest((root/'data.json').read_bytes()),
        'manifest_sha256':digest(args.manifest.read_bytes()), 'manifest':manifest,
        'environment':{'python':sys.version, 'packages':{p:importlib.metadata.version(p) for p in ('google-genai','Pillow','SQLAlchemy','fastapi')}},
        'mode':'preflight' if args.preflight_only else 'live-paired-service-pilot',
        'protocol':{'models':args.models,'config_overrides':config,'repetitions':1,
            'order':'case order fixed; model order reversed on alternating cases' if len(args.models)>1 else 'case order fixed; single-model run, not interleaved',
            'rag':'No index present; real service empty-context fallback; not a RAG evaluation',
            'database':'Isolated SQLite seeded from unchanged data.json; no production DB connection',
            'scope':'Image gate + real preliminary and diagnosis calls + validation + DB grounding; not HTTP/auth/device/SMTP acceptance',
            'raw_definition':'Final diagnosis JSON before name/confidence validation; not unconstrained base-model accuracy',
            'image_handling':'Original decoded by production Pillow loader, no resize/crop; SDK serializes image; filenames and expected labels are not included in prompts',
            'latency':'Two sequential model calls plus local processing, excluding deliberate rate-limit sleep; not deployment SLA',
            'labels':'Dataset folder labels only; no expert confirmation; small selected pilot, no population inference',
            'professional_advice_review':'Not performed; source presence and dosage patterns are mechanical risk indicators only',
            'request_limit_per_model':args.max_calls_per_model, 'retry_attempts':1},
        'input_checks':[], 'rows':[], 'summary':{}}
    paths = {}
    for case in cases:
        case_id = case['id']
        if not re.fullmatch(r'[a-z0-9-]+',case_id):
            raise ValueError('Unsafe case ID')
        path = args.images/f'{case_id}.bin'
        content = path.read_bytes()
        if digest(content) != case['image']['sha256']:
            raise ValueError(f'Image hash mismatch: {case_id}')
        try:
            validate_image_content(content,case['image']['mime'])
            check = {'case_id':case_id, 'accepted':True}
        except HTTPException as exc:
            check = {'case_id':case_id, 'accepted':False, 'status':exc.status_code, 'detail':exc.detail}
        report['input_checks'].append(check)
        paths[case_id] = path
    write_report(args.report,report)
    if args.preflight_only:
        db.close()
        engine.dispose()
        print(json.dumps({'preflight':'complete','eligible':sum(c['accepted'] for c in report['input_checks']), 'total':len(cases)}))
        return 0
    client = genai.Client(api_key=key,http_options=types.HttpOptions(timeout=90000,retry_options=types.HttpRetryOptions(attempts=1)))
    recorders = {m:RecordedModels(client,m,key,config,args.interval,args.max_calls_per_model) for m in args.models}
    try:
        for i,case in enumerate(cases):
            order = args.models if i%2 == 0 else args.models[::-1]
            for model in order:
                recorder = recorders[model]
                row = {'case_id':case['id'],'model':model,'started_at':datetime.now(timezone.utc).isoformat()}
                report['rows'].append(row)
                if not report['input_checks'][i]['accepted']:
                    row['status'] = 'input_rejected'
                elif recorder.stopped or recorder.total+2 > args.max_calls_per_model:
                    row.update(status='not_run',reason=recorder.stopped or 'Insufficient remaining request budget for both stages')
                else:
                    recorder.calls, recorder.slept = [], 0.0
                    ai.client = SimpleNamespace(models=recorder)
                    start = time.perf_counter()
                    with contextlib.redirect_stdout(io.StringIO()):
                        validated = ai.diagnostic_plant(str(paths[case['id']]), *names)
                        final = ai.ground_diagnosis_in_database(validated,db) if validated else None
                    elapsed = time.perf_counter()-start
                    raw = parse_candidate(recorder.calls[-1].get('text')) if len(recorder.calls)==2 else None
                    row.update(status='ok' if final else 'error', raw=raw, validated=validated, final=final,
                        calls=recorder.calls, raw_score=score(case,raw), final_score=score(case,final),
                        advice=advice_audit(final), wall_seconds=elapsed,
                        intentional_sleep_seconds=recorder.slept, inference_seconds=max(0,elapsed-recorder.slept))
                report['summary'] = {m:summarize(cases,report['rows'],m) for m in args.models}
                write_report(args.report,report)
                print(json.dumps({'case':case['id'],'model':model,'status':row['status'], 'outcome':row.get('final_score',{}).get('outcome')},ensure_ascii=False),flush=True)
        report['completed_at'] = datetime.now(timezone.utc).isoformat()
        write_report(args.report,report)
    finally:
        client.close()
        db.close()
        engine.dispose()
    return 0 if all(s['structured_results']==len(cases) for s in report['summary'].values()) else 2


if __name__ == '__main__':
    sys.exit(main())
