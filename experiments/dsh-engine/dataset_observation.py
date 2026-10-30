"""Six small public-task observations in official DSH and existing Qwen vLLM.

ODR/GPT Researcher/CRAG are workflow references, not executed frameworks here.
Original questions are retained, without prescribed agents or execution graphs.
"""
import argparse
import ast
import asyncio
import base64
import csv
from concurrent.futures import ThreadPoolExecutor
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
import pickle
import io
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import traceback
import tarfile
import zlib
from urllib.parse import parse_qs, urlencode, urlparse
import urllib.request

ROOT = Path('/home/Liangyijia_Hu/dsh-lab')
BATCH = 'public-tasks-20261030-v001'
LOCAL = Path(__file__).resolve().parent


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str)+'\n', encoding='utf8')


def get(url, timeout=30):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (research observation)'})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def remote_probe():
    code = '''import importlib.util,os,urllib.request,json
print(json.dumps({'modules':{x:bool(importlib.util.find_spec(x)) for x in ['ddgs','duckduckgo_search','trafilatura','requests','transformers','torch']},'keys':{x:bool(os.getenv(x)) for x in ['TAVILY_API_KEY','SERPER_API_KEY','BRAVE_API_KEY']}}))
print('model_health',urllib.request.urlopen('http://127.0.0.1:18082/health').status)
for u in ['https://www.bing.com/search?format=rss&q=CRISPR+base+editing+prime+editing','https://html.duckduckgo.com/html/?q=CRISPR+base+editing','https://huggingface.co/api/models?search=crag+evaluator&limit=8']:
 try:
  r=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=15);b=r.read();print(u,r.status,len(b),b[:180])
 except Exception as e: print(u,repr(e))
'''
    result = subprocess.run(['ssh','-o','BatchMode=yes','songprojgpu1',(ROOT/'upstream/venv-gptr/bin/python').as_posix()+' -'],input=code,text=True,capture_output=True,encoding='utf8')
    print(result.stdout);print(result.stderr)


def prepare_local():
    out = LOCAL/'state'/BATCH
    out.mkdir(exist_ok=True)
    repo = 'https://github.com/Ayanami0730/deep_research_bench.git'
    rev = subprocess.check_output(['git','ls-remote',repo,'HEAD'],text=True).split()[0]
    url = f'https://raw.githubusercontent.com/Ayanami0730/deep_research_bench/{rev}/data/prompt_data/query.jsonl'
    body = get(url)
    (out/'drb-original.jsonl').write_bytes(body)
    rows = [json.loads(line) for line in body.decode().splitlines() if line.strip()]
    dump(out/'drb-source.json',{'dataset':'DeepResearchBench','revision':rev,'url':url,'sha256':hashlib.sha256(body).hexdigest(),'count':len(rows)})
    print('DRB',len(rows),'tasks; original SHA256 retained')
    info=json.loads(get('https://hf-mirror.com/api/datasets/livecodebench/code_generation_lite'))
    url='https://hf-mirror.com/datasets/livecodebench/code_generation_lite/resolve/'+info['sha']+'/test6.jsonl'
    request=urllib.request.Request(url,headers={'Range':'bytes=0-1048575','User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(request,timeout=30)as response:
        body=response.read(1048576)
        status=response.status
    (out/'lcb-prefix.bin').write_bytes(body)
    dump(out/'lcb-source.json',{'dataset':'livecodebench/code_generation_lite','revision':info['sha'],'url':url,'range_status':status,'partial_bytes':len(body),'partial_sha256':hashlib.sha256(body).hexdigest()})
    rows=[json.loads(x)for x in body.splitlines()[:-1]]
    print('LCB complete prefix rows',[(x['question_id'],x['difficulty'])for x in rows])


def select_local():
    src=LOCAL/'state'/BATCH
    bundle=src/'inputs'
    bundle.mkdir(exist_ok=True)
    research=[json.loads(x) for x in (src/'drb-original.jsonl').read_text(encoding='utf8').splitlines()]
    provenance=json.loads((src/'drb-source.json').read_text(encoding='utf8'))
    cases=[]
    for task_id in [19,93]:
        raw=next(x for x in research if x['id']==task_id)
        cases.append({'case_id':f'drb-{task_id}','category':'research','dataset':'DeepResearchBench',
                      'dataset_task_id':task_id,'initial_task':raw['prompt'],'original_question':raw['prompt'],
                      'task_origin':'official dataset original, unmodified','dataset_source':provenance,
                      'selection_reason':'Two illustrative tasks: systems research and multi-product market research; not representative sampling.',
                      'workflow_reference':['ODR','GPT Researcher'],'executed_harness':'official DSH',
                      'input_files':{'task.json':json.dumps(raw,ensure_ascii=False,indent=2)}})
    rows=[json.loads(x) for x in (src/'lcb-prefix.bin').read_bytes().splitlines()[:-1]]
    provenance=json.loads((src/'lcb-source.json').read_text(encoding='utf8'))
    for task_id in ['abc387_c','abc387_f']:
        raw=next(x for x in rows if x['question_id']==task_id)
        public={k:v for k,v in raw.items() if k!='private_test_cases'}
        dump(bundle/'offline-labels'/f'{task_id}.json',{'private_test_cases':raw['private_test_cases']})
        cases.append({'case_id':f'lcb-{task_id}','category':'coding','dataset':'LiveCodeBench code_generation_lite / test6 (release_v6)',
                      'dataset_task_id':task_id,'initial_task':raw['question_content'],'original_question':raw['question_content'],
                      'task_origin':'official dataset original, unmodified','dataset_source':provenance,
                      'selection_reason':'One medium and one hard problem from the first complete download-prefix rows; no outcome-based selection.',
                      'workflow_reference':['coding generation/test/repair'],'executed_harness':'official DSH',
                      'input_files':{'statement.md':raw['question_content'],'task.json':json.dumps(public,ensure_ascii=False,indent=2),
                                     'public-tests.json':raw['public_test_cases']}})
    crag=LOCAL/'state/CRAG-source'
    groups={}
    for line in (crag/'data/popqa/test_popqa.txt').read_text(encoding='utf8').splitlines():
        if not line.strip():continue
        q,sep,doc=line.partition(' [SEP]')
        assert sep,line[:100]
        doc=doc.removeprefix(' ')
        # This release's inference fixture is unlabelled. Strip only a trailing
        # binary relevance label if one is present in another source revision.
        if '\t' in doc and doc.rsplit('\t',1)[1] in ['0','1']:
            doc=doc.rsplit('\t',1)[0]
        groups.setdefault(q,[]).append(doc)
    questions=list(groups)
    for index in [0,1]:
        q=questions[index];docs=groups[q]
        context='\n\n'.join(f'[{i}] {d}' for i,d in enumerate(docs,1))
        cases.append({'case_id':f'popqa-{index}','category':'retrieval_qa','dataset':'PopQA via official CRAG inference fixture',
                      'dataset_task_id':{'release_row_index':index,'question':q},'original_question':q,
                      'initial_task':q+'\n\nRetrieved passages (original dataset context):\n'+context,
                      'task_origin':'official original question and passages; context delimiter only is experiment formatting',
                      'dataset_source':{'url':'https://github.com/HuskyInSalt/CRAG/blob/de7c2961ae624a1483a138c5798e1f6d0c4fb0e0/data/popqa/test_popqa.txt',
                         'revision':'de7c2961ae624a1483a138c5798e1f6d0c4fb0e0','sha256':hashlib.sha256((crag/'data/popqa/test_popqa.txt').read_bytes()).hexdigest()},
                      'selection_reason':'First two original question groups, not selected by output or manual route scores.',
                      'workflow_reference':['CRAG conditional retrieval'],
                      'executed_harness':'official DSH; NOT original CRAG algorithm',
                      'input_files':{'question.txt':q,'retrieved-passages.txt':context}})
    for case in cases:
        case['input_sha256']={name:hashlib.sha256(body.encode()).hexdigest() for name,body in case['input_files'].items()}
        case['title']=str(case['dataset'])+' / '+str(case['dataset_task_id'])
        case['provenance']=case['task_origin']+'; '+case['executed_harness']
    manifest={'batch_id':BATCH,'cases':cases,'max_output_tokens':8192,
              'execution_stack':'official DSH 0.2.1-rc.2 -> passive wire observer -> vLLM -> Qwen3.8-27B',
              'policies':'native DSH; no delegation encouragement or custom workflow; temperature0 and output8192 declared',
              'scope':'6 illustrative tasks only; no framework comparisons, routing reproduction or benchmark aggregate score',
              'labels_visible_at_runtime':False,'no_prescribed_agents':True,'no_replay':True}
    dump(bundle/'plan.json',manifest)
    print(json.dumps({'cases':[(c['case_id'],len(c['initial_task'])) for c in cases]},ensure_ascii=False))


def run_remote(case_id):
    root=ROOT/'runs'/BATCH
    inputs=ROOT/'fixtures'/BATCH
    plan=json.loads((inputs/'plan.json').read_text(encoding='utf8'))
    root.mkdir(parents=True,exist_ok=True)
    if not (root/'plan.json').exists():dump(root/'plan.json',plan)
    spec=next(x for x in plan['cases'] if x['case_id']==case_id)
    workspace=Path('/home/Liangyijia_Hu/dsh-public-task-workspaces')/BATCH/case_id
    directory=root/case_id
    directory.mkdir(parents=True,exist_ok=False)
    workspace.mkdir(parents=True,exist_ok=False)
    for parent in [workspace,*workspace.parents]:
        assert not (parent/'AGENTS.md').exists(),parent
    for name,body in spec['input_files'].items():
        (workspace/name).write_text(body,encoding='utf8')
    shutil.copytree(workspace,directory/'input')
    spec={**spec,'workspace':str(workspace),'max_output_tokens':8192,'model':'Qwen3.8-27B',
          'reasoning_effort':'low','temperature':0,'source_commit':'687f282e8625c6b8d11ff58211a90524be2e4317',
          'agent_count_prescribed':False,'graph_prescribed':False,'policy':'native','watchdog_seconds':900}
    dump(directory/'spec.json',spec)
    (directory/'initial-task.txt').write_text(spec['initial_task'],encoding='utf8')
    shutil.copy2(__file__,directory/'runner.py')
    for name in ['qwen.patch.yml','natural.patch.yml','natural-observer.mjs']:
        shutil.copy2(ROOT/name,directory/name)
    node=ROOT/'toolchain/node-v24.22.2-linux-x64/bin/node'
    cmd=[str(node),str(ROOT/'runtime/node_modules/@deepseek-ai/dsh/lib/bin.js'),
         '--profile','headless','--patch',str(ROOT/'qwen.patch.yml'),
         '--patch',str(ROOT/'natural.patch.yml'),'--json',spec['initial_task']]
    env={**os.environ,'DSH_HOME':str(directory/'home'),'DSH_QWEN_API_KEY':'local-qwen-no-auth',
         'DSH_DAG_EVENT_FILE':str(directory/'observer.jsonl'),'DSH_DAG_MAX_TOKENS':'8192',
         'PATH':str(node.parent)+':/home/Liangyijia_Hu/harness-engine/.venv-engine/bin:'+os.environ['PATH']}
    started=time.time()
    with (directory/'cli.jsonl').open('wb') as out,(directory/'stderr.log').open('wb') as err:
        proc=subprocess.Popen(cmd,cwd=workspace,env=env,stdout=out,stderr=err,stdin=subprocess.DEVNULL,start_new_session=True)
        dump(directory/'launch.json',{'pid':proc.pid,'started_wall_time':started,'command':cmd})
        watchdog=False
        try:code=proc.wait(timeout=900)
        except subprocess.TimeoutExpired:
            watchdog=True;os.killpg(proc.pid,signal.SIGTERM)
            try:code=proc.wait(timeout=15)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);code=proc.wait()
    finished=time.time()
    shutil.copytree(workspace,directory/'output',ignore=shutil.ignore_patterns('__pycache__'))
    rows=[json.loads(x) for x in (directory/'observer.jsonl').read_text().splitlines()] if (directory/'observer.jsonl').exists() else []
    cli=[json.loads(x) for x in (directory/'cli.jsonl').read_text().splitlines() if x.strip()]
    finals=[x['text'] for x in cli if x.get('type')=='final']
    (directory/'answer.txt').write_text('\n\n'.join(finals),encoding='utf8')
    result={'case_id':case_id,'exit_code':code,'watchdog_triggered':watchdog,
            'started_wall_time':started,'finished_wall_time':finished,'duration_seconds':finished-started,
            'model_requests':sum(x['event']=='model_request_ready' for x in rows),
            'tool_calls':sum(x['event']=='tool_start' for x in rows),
            'session_files':len(list((directory/'home').rglob('session.v4.jsonl.zstd'))),
            'final_characters':sum(map(len,finals))}
    dump(directory/'completion.json',result)
    print(json.dumps(result),flush=True)


def analyze_remote():
    sys.path.insert(0,str(ROOT))
    from natural_analyze import analyze_case
    record=ROOT/'runs'/BATCH
    plan=json.loads((ROOT/'fixtures'/BATCH/'plan.json').read_text())
    dump(record/'plan.json',plan)
    summaries=[]
    for spec in plan['cases']:
        if not (record/spec['case_id']/'completion.json').exists():continue
        spec={**spec,'title':spec.get('title',str(spec['dataset'])+' / '+str(spec['dataset_task_id'])),
              'provenance':spec.get('provenance',spec['task_origin']+'; '+spec['executed_harness'])}
        summary=analyze_case(record,spec)
        summary['dataset']=spec['dataset'];summary['dataset_task_id']=spec['dataset_task_id']
        summary['dataset_source']=spec['dataset_source'];summary['executed_harness']=spec['executed_harness']
        dump(record/spec['case_id']/'summary.json',summary)
        summaries.append(summary)
    source_dir=record/'source-reference';source_dir.mkdir(exist_ok=True)
    web_source=ROOT/'runtime/node_modules/@deepseek-ai/dsh-tool-web/lib/index.js'
    shutil.copy2(web_source,source_dir/'dsh-tool-web.js')
    dump(source_dir/'manifest.json',{'dsh-tool-web.js':hashlib.sha256(web_source.read_bytes()).hexdigest(),
         'isConcurrencySafe':'web_search and web_fetch both declare () => true in pinned DSH release; declaration is not measured overlap'})
    dump(record/'comparison.json',{'batch_id':BATCH,'cases':summaries,'scope':plan['scope']})
    print(json.dumps([{'case':s['case_id'],'agents':s['agent_sessions'],'models':s['model_calls'],'tools':s['tool_counts'],'seconds':s['duration_seconds'],'truncated':s['output_truncations']}for s in summaries],ensure_ascii=False),flush=True)


def score_remote():
    class DataOnly(pickle.Unpickler):
        def find_class(self,module,name):raise ValueError('Unexpected executable pickle object')
    record=ROOT/'runs'/BATCH
    plan=json.loads((ROOT/'fixtures'/BATCH/'plan.json').read_text())
    for spec in plan['cases']:
        if spec['category']!='coding':continue
        directory=record/spec['case_id']
        if not (directory/'completion.json').exists():continue
        answer=(directory/'answer.txt').read_text()
        blocks=re.findall(r'```(?:python|python3|py)?\s*\n(.*?)```',answer,re.S)
        candidates=[(p,p.read_text())for name in ['solution.py','solve.py','main.py']for p in [directory/'output'/name]if p.exists()]
        if not candidates:
            candidates=[(p,p.read_text())for p in (directory/'output').rglob('*.py')if p.name in answer and 'test'not in p.name and 'brute'not in p.name]
        if not candidates:candidates=[(directory/'scoring'/f'final-block-{i}.py',body)for i,body in enumerate(blocks)]
        if not candidates:
            dump(directory/'offline-score.json',{'status':'no_python_candidate','scope':'offline only; no feedback to model'});continue
        path,code=candidates[0] if candidates[0][0].parent.name=='output' else candidates[-1]
        target=directory/'scoring/solution.py';target.parent.mkdir(exist_ok=True)
        target.write_text(code)
        try:
            tree=ast.parse(code)
            imports={n.names[0].name.split('.')[0] if isinstance(n,ast.Import) else (n.module or '').split('.')[0]for n in ast.walk(tree)if isinstance(n,(ast.Import,ast.ImportFrom))}
            allowed={'sys','math','collections','functools','itertools','bisect','heapq','array','typing','operator','decimal','fractions','random','queue'}
            assert imports<=allowed,imports-allowed
        except Exception as exc:
            dump(directory/'offline-score.json',{'status':'candidate_not_executed','reason':repr(exc),'scope':'offline only'});continue
        public=json.loads(spec['input_files']['public-tests.json'])
        label=ROOT/'fixtures'/BATCH/'offline-labels'/f"{spec['dataset_task_id']}.json"
        data=json.loads(label.read_text())['private_test_cases']
        try:private=json.loads(data)
        except json.JSONDecodeError:
            private=json.loads(DataOnly(io.BytesIO(zlib.decompress(base64.b64decode(data)))).load())
        results=[]
        for kind,tests in [('public',public),('private',private)]:
            for i,test in enumerate(tests):
                started=time.time()
                try:
                    p=subprocess.run(['python3','-I',str(target)],input=test['input'],capture_output=True,text=True,timeout=5,cwd=target.parent)
                    ok=p.returncode==0 and p.stdout.split()==test['output'].split()
                    results.append({'kind':kind,'index':i,'passed':ok,'exit_code':p.returncode,'seconds':time.time()-started,
                                    **({}if ok else {'expected':test['output'],'actual':p.stdout,'stderr':p.stderr})})
                except subprocess.TimeoutExpired:results.append({'kind':kind,'index':i,'passed':False,'timeout':True})
        score={'status':'scored','candidate_origin':str(path.relative_to(directory)),
               'scope':'offline original tests only; no hidden inputs or verdicts supplied to Qwen',
               'public_passed':sum(r['passed']for r in results if r['kind']=='public'),'public_total':len(public),
               'private_passed':sum(r['passed']for r in results if r['kind']=='private'),'private_total':len(private),'tests':results}
        dump(directory/'offline-score.json',score)
        print(spec['case_id'],score['public_passed'],len(public),score['private_passed'],len(private),flush=True)


def collect_remote():
    record=ROOT/'runs'/BATCH
    plan=json.loads((record/'plan.json').read_text())
    assert all((record/c['case_id']/'summary.json').exists()for c in plan['cases'])
    archive=ROOT/'artifacts'/f'{BATCH}-raw.tar.gz'
    with tarfile.open(archive,'x:gz')as tar:tar.add(record,arcname=BATCH)
    dump(ROOT/'artifacts'/f'{BATCH}-index.json',{'archive':archive.name,'bytes':archive.stat().st_size,
           'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'task_count':6,'harness':'official DSH','replay':False})
    print('archived',archive.stat().st_size,flush=True)


def export_local():
    state=LOCAL/'state'/BATCH
    record=state/'unpacked'/BATCH
    plan=json.loads((state/'inputs/plan.json').read_text(encoding='utf8'))
    out=LOCAL/'results'/BATCH
    out.mkdir(exist_ok=True)
    archive=LOCAL/'evidence'/BATCH/'raw.tar.gz'
    source_files=[]
    with tarfile.open(archive)as tar:
        for member in tar.getmembers():
            if member.isfile()and '/source-reference/'in member.name:
                body=tar.extractfile(member).read()
                source_files.append({'archive_member':member.name,'bytes':len(body),
                                     'sha256':hashlib.sha256(body).hexdigest()})
    dump(out/'source-manifest.json',{'batch':BATCH,'raw_archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
         'note':'Derived checksums of immutable archived source files; LCB is a 1 MiB prefix, not the complete release.',
         'files':source_files})
    descriptor=importlib.util.spec_from_file_location('natural_export',LOCAL/'export_natural_site.py')
    mod=importlib.util.module_from_spec(descriptor);descriptor.loader.exec_module(mod)
    titles={'drb-19':'研究原题 · Prometheus高流失率','drb-93':'研究原题 · 视频编辑软件市场',
            'lcb-abc387_c':'代码原题 · Snake Numbers（中等）','lcb-abc387_f':'代码原题 · Count Arrays（难）',
            'popqa-0':'检索问答 · Henry Feilden职业','popqa-1':'检索问答 · Herlyn Espinal职业'}
    cases=[]
    gold_file=state/'popqa-original.tsv'
    gold_rows=list(csv.DictReader(io.StringIO(gold_file.read_text(encoding='utf8')),delimiter='\t'))if gold_file.exists()else []
    for spec in plan['cases']:
        case=spec['case_id'];source=record/case
        if not (source/'summary.json').exists():continue
        directory=out/case;directory.mkdir(exist_ok=True)
        s=json.loads((source/'summary.json').read_text(encoding='utf8'))
        graph=json.loads((source/'graph.json').read_text(encoding='utf8'))
        for name in ['summary.json','timeline.json','graph.json','initial-task.txt','completion.json','spec.json','answer.txt','offline-score.json','stop-reason.json']:
            if(source/name).exists():shutil.copy2(source/name,directory/name)
        if not(directory/'initial-task.txt').exists():
            assert s['initial_task']==spec['initial_task']
            (directory/'initial-task.txt').write_text(spec['initial_task'],encoding='utf8')
        score=json.loads((source/'offline-score.json').read_text(encoding='utf8'))if(source/'offline-score.json').exists()else None
        qa_score=None
        if spec['category']=='retrieval_qa' and gold_rows:
            gold=next(r for r in gold_rows if r['question']==spec['original_question'])
            answer=(source/'answer.txt').read_text(encoding='utf8')
            matches=[alias for alias in json.loads(gold['possible_answers'])if re.search(r'\b'+re.escape(alias)+r'\b',answer,re.I)]
            qa_score={'dataset':'PopQA original','id':gold['id'],'expected_aliases':json.loads(gold['possible_answers']),
                      'matched_aliases':matches,'alias_match':bool(matches),'scope':'offline answer-alias check only; not a grounding metric',
                      'labels_visible_at_runtime':False,'gold_source_url':'https://raw.githubusercontent.com/AlexTMallen/adaptive-retrieval/main/data/popQA.tsv',
                      'gold_source_sha256':hashlib.sha256(gold_file.read_bytes()).hexdigest()}
            dump(directory/'offline-score.json',qa_score)
        quality='正常结束仅表示执行完成；未进行RACE/FACT报告质量评分。'if spec['category']=='research'else '只记录DSH在给定原题与检索上下文上的行为；没有运行CRAG评估器或路由算法。'if spec['category']=='retrieval_qa'else '模型自主作答；测试在运行结束后离线执行，没有把隐藏测试反馈给模型。'
        stopped=(source/'stop-reason.json').exists()
        if spec['category']=='research':quality+=' 本轮原生web_search因缺DeepSeek搜索凭据失败，网页访问也有错误；研究质量受工具环境限制，不能据此推断模型的通常委派行为。'
        if stopped:quality+=' 已主动停止这道反复网络重试的任务，保留完整轨迹；不是成功研究。'
        if score and score.get('status')=='scored':quality+=f" 原测试：公开{score['public_passed']}/{score['public_total']}，隐藏{score['private_passed']}/{score['private_total']}。"
        if qa_score:quality+=' 原始PopQA答案别名离线匹配：'+('通过。'if qa_score['alias_match']else '未通过。')
        task_id=spec['dataset_task_id']
        if isinstance(task_id,dict):task_id='发布文件题组 '+str(task_id['release_row_index'])
        s.update(run_id=BATCH,label=titles[case],purpose_cn=spec['original_question'],provenance_cn=f"数据集：{spec['dataset']}；题号：{task_id}。任务来源：公开原题；执行框架：官方DSH。"+('原题和原始检索段落同时输入；不是CRAG算法复现。'if spec['category']=='retrieval_qa'else '未改原题，也未加入委派要求。'),
                 short_result_cn='已停止；搜索环境受限'if stopped else '超时；未交付'if s['watchdog_triggered']else '输出截断；未交付代码'if s['output_truncations']and spec['category']=='coding'else '输出截断'if s['output_truncations']else '搜索失败；输出待核验'if spec['category']=='research'else f"公开{score['public_passed']}/{score['public_total']}；隐藏{score['private_passed']}/{score['private_total']}"if score and score.get('status')=='scored'else '答案别名匹配通过'if qa_score and qa_score['alias_match']else '答案别名未匹配'if qa_score else '有最终输出',result_cn=quality,
                 execution=mod.execution_summary(graph),offline_score=score or qa_score,
                 paths={'graph':f'../{BATCH}/{case}/graph.json','timeline':f'../{BATCH}/{case}/timeline.json',
                        'summary':f'../{BATCH}/{case}/summary.json','input':f'../{BATCH}/{case}/initial-task.txt',
                        'answer':f'../{BATCH}/{case}/answer.txt','sources':f'../{BATCH}/source-manifest.json',
                        'raw':f'../../evidence/{BATCH}/raw.tar.gz'})
        s['execution']['pinned_parallel_safe_tools']=['read','web_search','web_fetch']
        s['execution']['classification_scope']='Pinned DSH declarations checked for read/web_search/web_fetch; remaining observed bash/edit/write/todo are exclusive.'
        cases.append(s)
    dump(out/'index.json',{'group':BATCH,'label':'公开原题 · DSH统一入口','cases':cases,'task_count':len(cases),'scope':plan['scope']})
    metadata=LOCAL/'evidence'/BATCH/'index.json'
    meta=json.loads(metadata.read_text(encoding='utf8'))
    meta.update(local_archive='raw.tar.gz',results=f'../../results/{BATCH}/index.json',
                source_manifest=f'../../results/{BATCH}/source-manifest.json',report='../../notes/natural-dag-20261029.md',
                scope_note='Six original public tasks in official DSH only; includes research tool failures, one stopped run and one output truncation. Raw bytes unchanged.')
    dump(metadata,meta)
    print('exported',len(cases),'public task views')


def retrieve_local():
    evidence=LOCAL/'evidence'/BATCH
    evidence.mkdir(exist_ok=True)
    for remote,name in [(f'{BATCH}-index.json','index.json'),(f'{BATCH}-raw.tar.gz','raw.tar.gz')]:
        if(evidence/name).exists():continue
        subprocess.run(['scp','-q',f'songprojgpu1:/home/Liangyijia_Hu/dsh-lab/artifacts/{remote}',str(evidence/name)],check=True)
    meta=json.loads((evidence/'index.json').read_text())
    assert (evidence/'raw.tar.gz').stat().st_size==meta['bytes']
    assert hashlib.sha256((evidence/'raw.tar.gz').read_bytes()).hexdigest()==meta['sha256']
    target=LOCAL/'state'/BATCH/'unpacked'
    target.mkdir(exist_ok=True)
    with tarfile.open(evidence/'raw.tar.gz')as tar:
        # Only derived viewer records need extraction on Windows. The complete
        # native HOME/input/wire paths remain intact in the immutable tarball.
        members=[m for m in tar.getmembers()if m.isfile()and len(Path(m.name).parts)<=3]
        tar.extractall(target,members=members,filter='data')
    print('retrieved verified archive',meta['bytes'],meta['sha256'])


def main():
    p=argparse.ArgumentParser()
    p.add_argument('action',choices=['probe','prepare','select','run','batch','analyze','score','collect','retrieve','export'])
    p.add_argument('--case')
    args=p.parse_args()
    if args.action=='probe':remote_probe()
    elif args.action=='prepare':prepare_local()
    elif args.action=='select':select_local()
    elif args.action=='run':run_remote(args.case)
    elif args.action=='batch':
        plan=json.loads((ROOT/'fixtures'/BATCH/'plan.json').read_text())
        for spec in plan['cases']:
            if (ROOT/'runs'/BATCH/spec['case_id']/'completion.json').exists():continue
            run_remote(spec['case_id'])
    elif args.action=='analyze':analyze_remote()
    elif args.action=='score':score_remote()
    elif args.action=='collect':collect_remote()
    elif args.action=='export':export_local()
    elif args.action=='retrieve':retrieve_local()


if __name__=='__main__':main()
