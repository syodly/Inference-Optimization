"""Export readable native-framework traces from immutable evidence bundles."""
from collections import Counter
import argparse
import json
from pathlib import Path
import tarfile

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'experiments/dsh-engine'
EVIDENCE=BASE/'state/upstream-complete'
OUT=BASE/'results/natural-dag-20261029/frameworks'
WEB='../experiments/dsh-engine/'


def read(path):return json.loads(path.read_text(encoding='utf8'))
def write(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf8')


def provenance_catalogue():
    """A single derived catalogue; never rewrites an archived spec or prompt."""
    hp_manifest=read(BASE/'evidence/e1-small-20261029/data-manifest.json')
    ids=['5a78f59755429970f5fffdf7','5ae75a5a5542991bbc9761f3','5a87868c5542996e4f308828',
         '5ab29624554299545a2cf9b5','5ab97c0255429970cfb8eb1f','5ae1316555429901ffe4adda']
    policies={'native':'原生系统策略','allow':'只放宽 workflow 使用条件',
              'encourage':'增加一般委派建议','autodelegate':'增加是否拆分的评估规则'}
    sources={
        'research':{'label':'HotpotQA 原题与文档＋自编合并任务','kind':'public_dataset_adaptation',
                    'dataset':'HotpotQA distractor / validation','task_origin':'六道子问题来自数据集；要求合并核查并写报告的外层任务由本实验编写',
                    'input_origin':'六题各10篇原始context，转成60个Markdown文件；答案标签不交给模型',
                    'task_ids':ids,'revision':hp_manifest['revision'],'source_url':hp_manifest['url'],
                    'source_sha256':hp_manifest['sha256']['tasks.jsonl'],'unit':'一次根任务中合并6道原题；多次运行复用同六题'},
        'runtime-audit':{'label':'自编核对任务＋官方DSH资料','kind':'official_source_fixture','dataset':None,
                         'task_origin':'本实验编写：追踪委派、workflow与工具并发的执行边界',
                         'input_origin':'官方DSH五个模块的文档及部分入口代码；不是公开benchmark',
                         'unit':'同一资料核对任务的策略对照'},
        'dsh-source-review':{'label':'自编审查任务＋官方DSH源码','kind':'official_source_fixture','dataset':None,
                             'task_origin':'本实验编写：检查跨模块执行路径中的正确性风险',
                             'input_origin':'官方DSH六类模块的文档、实现与设置文件；不是公开benchmark',
                             'unit':'同一源码任务的策略对照'},
        'multi-object-review':{'label':'自编任务＋4份虚构短资料','kind':'synthetic_fixture','dataset':None,
                               'task_origin':'本实验编写：分别提炼四个对象的架构、限制、影响，再给比较建议',
                               'input_origin':'Alpha Runtime / Beta Routing / Gamma Tools / Delta Workflow为人工虚构说明，不是DSH四个真实组件',
                               'unit':'同四份短资料的两次策略对照'},
        'simple':{'label':'自编折扣算术题','kind':'synthetic_fixture','dataset':None,
                  'task_origin':'本实验编写：240美元打17.5%折扣后的价格','input_origin':'题目内给定数字，无外部数据',
                  'unit':'同一简单负向校准题'},
        'open-research':{'label':'自编开放调查题＋运行时联网工具','kind':'authored_open_research','dataset':None,
                         'task_origin':'本实验编写：调查不同系统为何会自主派发子Agent',
                         'input_origin':'模型实际使用web_search / web_fetch等工具；无固定公开数据集题号',
                         'unit':'同一开放调查题、普通与Teams工具面的对照'}}
    for source in sources.values():source['official_benchmark_protocol']=False
    groups={
        'research':{'title':'六道HotpotQA合并调查','question':'是否被系统提示、推理强度或Team工具面抑制委派？','count':7},
        'runtime-audit':{'title':'官方DSH架构资料核对','question':'阅读真实架构资料是否会主动委派？','count':3},
        'dsh-source-review':{'title':'官方DSH大段源码审查','question':'任务更重时是否会拆分，而非一直累积上下文？','count':2},
        'multi-object-review':{'title':'4份虚构资料比较','question':'多个独立对象是否足以诱发委派？此任务很短，证据有限。','count':2},
        'simple':{'title':'自编折扣算术校准','question':'额外策略是否会让简单题也无条件创建子工作？','count':2},
        'open-research':{'title':'自编开放联网调查','question':'需要多轮检索时是否会委派？','count':2}}
    dsh_rows=[]
    archive=BASE/'evidence/autonomy-20261030-v002/raw.tar.gz'
    with tarfile.open(archive)as tar:
        for m in tar.getmembers():
            if not(m.name.endswith('/spec.json')and m.name.count('/')==3):continue
            case=m.name.split('/')[2];spec=json.load(tar.extractfile(m));scenario=spec['scenario']
            src=dict(sources[scenario]);src['input_files']=list(spec.get('input_sha256',{}))
            changed=policies[spec['policy']]
            if spec.get('team_profile'):changed+='；启用Agent Teams工具面'
            # Effort is derived from actual API traffic below; legacy specs
            # contain stale low values and must not be used as truth.
            summary=next(x for x in read(BASE/'evidence/autonomy-20261030-v002/summary.json')['runs']if x['case_id']==case)
            efforts=list(summary['wire_reasoning_efforts']);changed+='；实际推理强度 '+('/'.join(efforts))
            dsh_rows.append({'run_id':case,'framework':'官方DSH','group':scenario,'provenance':src,
                             'initial_task':spec['initial_task'],'experiment_change':changed,
                             'raw_spec_member':m.name,'raw_archive':'autonomy-20261030-v002',
                             'spec':spec,'summary':summary})
    for scenario,g in groups.items():
        g.update(id=scenario,source=sources[scenario],run_ids=[r['run_id']for r in dsh_rows if r['group']==scenario])
        assert len(g['run_ids'])==g['count']
    upstream_rows=[]
    archive=BASE/'evidence/upstream-workflows-20261030-v003/raw.tar.gz'
    outcomes={
        'odr-v001':'缺少API凭据，模型请求前失败','odr-v002':'无检索工具；子研究异常后提前进入报告',
        'odr-qwen-v003-20261030':'Python import path错误，未请求模型',
        'odr-qwen-v004-20261030':'研究和最终报告有截断','odr-qwen-v005-20261030':'扩大预算，最终报告仍截断',
        'odr-qwen-v006-20261030':'窄任务；误判资料缺失，零委派，未完成审查',
        'odr-qwen-v007-20261030':'澄清资料可从工具取得；3路研究、完整报告，内容另核对',
        'gptr-v001':'只完成context研究；未调用write_report',
        'gptr-qwen-v002-20261030':'嵌入端点404，终止本轮',
        'gptr-qwen-v003-20261030':'完整源码重复进入上下文；汇总超限，报告为空',
        'gptr-qwen-v004-20261030':'改用源码片段，角色与报告仍截断',
        'gptr-qwen-v005-20261030':'补齐源码片段和预算；6个子实例，完整报告，内容另核对'}
    variants={
        'odr-v001':'最早入口；缺少凭据，未进入模型执行',
        'odr-v002':'配置模型后重试；未配置有效检索工具',
        'odr-qwen-v003-20261030':'接入官方源码MCP；入口import path错误',
        'odr-qwen-v004-20261030':'修正入口路径；宽核对任务，压缩/报告额度4096',
        'odr-qwen-v005-20261030':'保持宽任务，压缩/报告额度改为8192',
        'odr-qwen-v006-20261030':'改为窄核对任务，要求600英文词；补全语料，研究循环4→3',
        'odr-qwen-v007-20261030':'在v006初始任务后追加资料可由source_search取得的说明；配置预算不变',
        'gptr-v001':'6条自编摘要；仅conduct_research，未执行write_report',
        'gptr-qwen-v002-20261030':'4份官方源码全文；默认嵌入路径失败',
        'gptr-qwen-v003-20261030':'使用原生小文档直返路径；完整源码反复进入上下文',
        'gptr-qwen-v004-20261030':'全文改为源码片段，每份约2500字符；仍有输出截断',
        'gptr-qwen-v005-20261030':'补齐关键递归源码片段；输出8192、英文、800词目标'}
    with tarfile.open(archive)as tar:
        summary=read(BASE/'evidence/upstream-workflows-20261030-v003/summary.json')['runs']
        members={m.name:m for m in tar.getmembers()}
        for row in summary:
            case=row['case_id'];base='upstream-workflows-20261030-v003/runs/'+case+'/'
            key=base+('spec.json'if base+'spec.json'in members else 'trace.json');spec=json.load(tar.extractfile(members[key]))
            legacy=case in ['odr-v001','odr-v002','gptr-v001']
            if case.startswith('odr-v'):material='未配置检索语料；无有效搜索工具'
            elif case=='gptr-v001':material='本实验编写的6条本地摘要，非官方原文'
            elif case in ['gptr-qwen-v002-20261030','gptr-qwen-v003-20261030']:material='固定的4份官方源码／文档全文；不是实时网络检索'
            else:material='固定的4份官方源码／文档片段；不是实时网络检索'
            p={'label':'自编编排机制核对题','kind':'authored_diagnostic','dataset':None,
               'task_origin':'Codex为排查编排机制编写的初始任务；不是公开数据集原题',
               'input_origin':material,'official_benchmark_protocol':False,
               'unit':'同类诊断任务的配置修正或提示变体；每次只提交1个根任务'}
            upstream_rows.append({'run_id':case,'framework':'ODR'if case.startswith('odr')else 'GPT Researcher',
                                  'provenance':p,'initial_task':spec['query'],'config':spec['config'],
                                  'experiment_change':variants[case],
                                  'outcome':outcomes[case],'wire_requests':row['wire_requests'],
                                  'raw_spec_member':key,'raw_archive':'upstream-workflows-20261030-v003',
                                  'trace_coverage':'旧trace仅部分事件数据'if legacy else 'spec/事件/API/产物；失败范围按记录',
                                  'display_id':{'odr-qwen-v007-20261030':'odr','odr-qwen-v006-20261030':'odr-focused',
                                                'odr-qwen-v005-20261030':'odr-wide','gptr-qwen-v005-20261030':'gptr'}.get(case)})
    assert len(dsh_rows)==18 and len(upstream_rows)==12
    plan1=read(BASE/'results/natural-dag-20261029-v001/plan.json')
    natural=[]
    local={'coding':('自编结账服务与7项可见unittest','非LiveCodeBench / SWE-bench题目'),
           'analysis':('确定性合成订单／退款／产品CSV','非生产或公开基准数据'),
           'incident':('人工编写日志／指标／部署记录','非真实生产故障')}
    for c in plan1['cases']:
        name=c['case_id'];p=dict(sources['research'if name=='research'else 'simple']) if name in ['research','simple'] else {
            'label':local[name][0],'kind':'synthetic_fixture','dataset':None,'task_origin':'本实验编写',
            'input_origin':local[name][1],'official_benchmark_protocol':False,'unit':'1个人工任务'}
        p['input_files']=list(c['input_sha256'])
        natural.append({'run_id':'natural-dag-20261029-v001/'+name,'framework':'官方DSH','provenance':p,
                        'initial_task':c['initial_task'],'rerun':'natural-dag-20261029-v002/'+name if name in ['analysis','incident'] else None})
    coverage=[
        {'id':'odr','framework':'ODR','task_source':'Codex自编的编排机制核对题；固定源码语料',
         'attempts':'7次尝试，含初始化失败；页面选3次','dataset_coverage':'DeepResearchBench：0题',
         'level':'原生应用运行；诊断案例','missing':'尚未做公开研究数据集上的任务质量与DAG观察'},
        {'id':'gptr','framework':'GPT Researcher','task_source':'Codex自编的机制研究题；早期6条摘要，后为4份官方源码',
         'attempts':'5次尝试；页面选1次完整运行','dataset_coverage':'公开研究数据集：0题',
         'level':'原生应用运行；诊断案例','missing':'尚未做多道公开研究题的代表性实验'},
        {'id':'coding','framework':'Coding','task_source':'自编Python结账服务，附带7项可见测试',
         'attempts':'官方DSH执行1次修复任务','dataset_coverage':'LiveCodeBench / SWE-bench：0题',
         'level':'DSH小型修复轨迹；原候选图未实测','missing':'尚未运行公开编码基准及对应真实coding编排'},
        {'id':'crag','framework':'CRAG','task_source':'人工指定3组相关性分数',
         'attempts':'原生process_flag函数执行3个边界输入','dataset_coverage':'PopQA / PubQA / Bio / ARC：0题',
         'level':'仅函数路由核对，无LLM工作流运行','missing':'尚未执行评估器→条件检索→生成的完整流程'}]
    archive_rows=[]
    for folder,scope,current in [('autonomy-20261030-v002','DSH18次排查＋单步API探针',True),
                                  ('upstream-workflows-20261030-v003','ODR7次＋GPT Researcher5次',True),
                                  ('autonomy-20261030','较早11次DSH快照',False),
                                  ('upstream-workflows-20261030-v002','较早12次原生运行快照',False)]:
        d=BASE/'evidence'/folder;idx=read(d/'index.json')
        archive_rows.append({'id':folder,'scope':scope,'current':current,'bytes':idx['bytes'],'sha256':idx['sha256'],
                             'url':WEB+'evidence/'+folder+'/raw.tar.gz','index_url':WEB+'evidence/'+folder+'/index.json',
                             'counting_note':'同一run_id在多个包中出现时只算一次；不是新增实验'})
    catalogue={'schema_version':1,'scope':'官方DSH当前观察、18次排查、原生ODR/GPT诊断及CRAG/Coding覆盖状态；不合并旧自建harness性能批次',
               'counting_rules':['运行次数包含失败尝试，不等于任务数量或数据集数量','公开代码是语料来源，不自动成为benchmark数据集',
                                 '外层任务为实验编写、子问题为数据集原题时，两层分别标注','重复包是归档快照，不重复计数'],
               'framework_coverage':coverage,'dsh_groups':list(groups.values()),'dsh_runs':dsh_rows,
               'upstream_runs':upstream_rows,'natural_cases':natural,'archives':archive_rows,
               'historical_dataset_experiment':{'title':'此前E1最小八题派发对照（独立旧实验）','dataset':'HotpotQA distractor / validation',
                   'task_ids':hp_manifest['task_ids'][:8],'attempts':'同8题跑原生 / 固定12 / 压力反馈12三轮，另有功能校准',
                   'protocol':'公开context上的自定义三子Agent应用；外层提示与工作流人为定义，不是原生HotpotQA评测协议',
                   'manifest_url':WEB+'evidence/e1-small-20261029/data-manifest.json','page_url':'topic1-experiments.html'}}
    catalogue['legacy_evidence_note']='upstream-odr-20261030-v001为更早ODR trace/wire快照，已纳入当前包对应运行，不另算实验。'
    public=read(BASE/'results/public-tasks-20261030-v001/index.json')
    catalogue['latest_dsh_public_tasks']={
        'batch':public['group'],'task_count':public['task_count'],'harness':'官方DSH → vLLM → Qwen3.8-27B',
        'scope':'独立于下面旧诊断的六道公开原题；不是ODR/GPT/CRAG算法运行，也不并入18次排查。',
        'datasets':{'DeepResearchBench':[19,93],'LiveCodeBench':['abc387_c','abc387_f'],'PopQA':['4382392','1223902']},
        'results_url':WEB+'results/public-tasks-20261030-v001/index.json',
        'source_manifest_url':WEB+'results/public-tasks-20261030-v001/source-manifest.json',
        'evidence_index_url':WEB+'evidence/public-tasks-20261030-v001/index.json',
        'page_url':'topic1-dag-observation.html#observation'}
    write(OUT/'experiment-catalogue.json',catalogue)
    return catalogue


def response(path):
    s=path.read_text(encoding='utf8');content='';reasoning='';calls={};finish=None;usage={};error=None
    if not s.startswith('data:'):
        obj=json.loads(s)
        if obj.get('error'):return {'content':'','tool_calls':[],'error':obj['error']},None,{}
        c=(obj.get('choices')or[{}])[0];m=c.get('message',{})
        return {'content':m.get('content')or'','reasoning':m.get('reasoning')or m.get('reasoning_content')or'', 'tool_calls':m.get('tool_calls')or[]},c.get('finish_reason'),obj.get('usage',{})
    for line in s.splitlines():
        if not line.startswith('data: ') or line=='data: [DONE]':continue
        chunk=json.loads(line[6:]);usage=chunk.get('usage')or usage
        if chunk.get('error'):error=chunk['error']
        for choice in chunk.get('choices',[]):
            d=choice.get('delta',{});content+=d.get('content')or'';reasoning+=d.get('reasoning_content')or d.get('reasoning')or''
            for tc in d.get('tool_calls')or[]:
                dest=calls.setdefault(tc.get('index',0),{'id':'','type':'function','function':{'name':'','arguments':''}})
                if tc.get('id'):dest['id']=tc['id']
                f=tc.get('function',{})
                dest['function']['name']+=f.get('name')or'';dest['function']['arguments']+=f.get('arguments')or''
            if choice.get('finish_reason'):finish=choice['finish_reason']
    return {'content':content,'reasoning':reasoning,'tool_calls':list(calls.values()),**({'error':error}if error else{})},finish,usage


def requests(case,start):
    rows=[]
    for ordinal,d in enumerate(sorted((EVIDENCE/'wire'/case).iterdir()),1):
        m=read(d/'request.json');res=read(d/'response.json');body=read(d/'request.body');out,finish,usage=response(d/'response.body')
        begin=m['started_wall_time']-start
        rows.append({'id':d.name,'ordinal':ordinal,'start':begin,'end':begin+res['duration_seconds'],'http_status':res.get('status'),
                     'finish_reason':finish,'request':body,'response':out,'measurement':{**res,'usage':usage},'stage':''})
    return rows


def peak(req):
    events=sorted([(r['start'],1)for r in req]+[(r['end'],-1)for r in req]);active=maximum=0
    for _,d in events:active+=d;maximum=max(maximum,active)
    return maximum


def node(id,title,start,end,row,lane=0,kind='',query='',role='',relation='',requests=None,caption=''):
    return {'id':id,'title':title,'start':start,'end':end,'row':row,'lane':lane,'kind':kind,'query':query,
            'role':role,'relation':relation,'request_ids':[r['id']for r in requests or []],'caption':caption}


def gptr(case):
    d=EVIDENCE/'runs'/case;c=read(d/'completion.json');spec=read(d/'spec.json');start=c['started_wall_time'];rr=requests(case,start)
    created=[e for e in c['events']if e['event']=='researcher_created'];ended={e['query']:e['wall_time']-start for e in c['events']if e['event']=='researcher_finished'}
    planners=[r for r in rr if str(r['request']['messages'][-1].get('content','')).startswith('Given the following prompt, generate')]
    assert len(created)==6 and len(planners)==3,(len(created),len(planners))
    nodes=[node('task','初始研究任务',0,0,0,role='用户只给研究目标，没有提供查询列表或执行图。',query=spec['query'],relation='应用先生成角色与本层查询。')]
    edges=[];assigned=set()
    for batch in range(3):
        p=planners[batch];p['stage']='本层查询生成';pn=f'plan-{batch}';row=[1,4,7][batch]
        pre=[r for r in rr if r['end']<=p['end'] and r['id']not in assigned and not any(r['id']in n['request_ids'] for n in nodes)]
        if batch>0:pre=[p]
        nodes.append(node(pn,['生成第一层查询','根据第一路发现继续提问','根据第二路发现继续提问'][batch],min(r['start']for r in pre),p['end'],row,kind='',query=p['request']['messages'][-1]['content'],role='模型生成查询文本；breadth=2 是应用给模型的数量预算，查询内容在线生成。',relation=['接初始任务，产生第一层两个查询。','等待本层全部研究与结果提炼结束，再沿第一条结果递归。','前一棵递归子树返回后，程序才处理第二条结果并生成其下一层查询。'][batch],requests=pre,caption='LLM 生成具体查询 · 数量受配置约束'))
        assigned.update(r['id']for r in pre)
        if batch==0:edges.append({'from':'task','to':pn})
        else:edges.append({'from':f'join-{batch-1}','to':pn,'order':batch==2})
        unit_ends=[]
        for k,e in enumerate(created[batch*2:batch*2+2]):
            q=e['query'];ids=[]
            for r in rr:
                text=str(r['request']['messages'][-1].get('content',''))
                if q in text and r['id']not in assigned and r not in planners and r['start']>=e['wall_time']-start-.05:
                    # The final report contains all queries too; its prompt has
                    # a different role and must not be assigned to one child.
                    if text.startswith('Using the following') or text.lstrip().startswith('Using the following'):continue
                    ids.append(r);r['stage']='子研究角色生成 / 查询扩展 / 结果提炼'
            en=max([ended[q],*[r['end']for r in ids]])
            unit_ends.append(en);assigned.update(r['id']for r in ids)
            nid=f'worker-{batch}-{k}'
            n=node(nid,f'{["第一层","第二层 A","第二层 B"][batch]} · 子研究 {k+1}',e['wall_time']-start,en,row+1,[-.65,.65][k],'worker',q,
                   '官方代码创建一个 GPTResearcher 实例，执行检索，再用模型提炼 learnings 和 follow-up questions。图中区间包含查询分支的结果提炼；对象 conduct_research 的结束时刻另存。',
                   '接本批生成的查询；检索使用固定官方源码片段。该分支返回后，发现进入上层汇合。',ids,'独立实例 · 检索＋结果提炼')
            n['conduct_finished_at']=ended[q];nodes.append(n);edges.append({'from':pn,'to':nid})
        en=max(unit_ends)
        nodes.append(node(f'join-{batch}',f'第 {batch+1} 批汇合',en,en,row+2,kind='join',role='程序等待本批查询分支全部返回；合并研究发现。这里不额外调用一个“汇合 Agent”。',relation='第一批之后还有递归；后两批分别属于第一层两条结果的后续子树。',caption='程序 gather / 合并边界'))
        edges.extend({'from':f'worker-{batch}-{k}','to':f'join-{batch}'}for k in range(2))
    last=[r for r in rr if r['id']not in assigned]
    for r in last:r['stage']='最终报告'
    assert len(last)==1,[(r['ordinal'],r['stage'])for r in last]
    nodes.append(node('report','最终报告',last[0]['start'],last[-1]['end'],10,role='使用累计的研究上下文写报告；报告文本的事实正确性需要另行核对。',relation='两棵递归子树都返回后汇总。',requests=last,caption='报告生成 · 不计为新子研究实例'))
    edges.append({'from':'join-2','to':'report'})
    final=last[-1]['finish_reason'];report=(d/'report.md').read_text(encoding='utf8')
    data={'id':'gptr','title':'GPT Researcher · 原生递归研究','case_id':case,'started_wall_time':start,'duration_seconds':c['duration_seconds'],
          'finding':'同一 Qwen27B 实际产生了 6 个子研究实例：先并行一层，再依据返回的 follow-up questions 生成后续查询。',
          'scope':'breadth=2 / depth=2 / concurrency=2 是应用配置。程序决定创建实例与递归框架，模型决定具体查询内容；这不证明模型自由选择了 Agent 总数。根实例共 1 个，图中显示另 6 个查询分支。',
          'stats':[['根＋子研究实例','1＋6'],['实际模型请求',len(rr)],['模型请求在途峰值',peak(rr)],['总耗时',f"{c['duration_seconds']:.2f} s"]],
          'query':spec['query'],'quality':f'最终 API finish_reason={final}；报告 {len(report)} 字符。完整输出不等于内容正确：报告把 ODR 超限分支称作“静默丢弃”，源码实际会返回错误 ToolMessage；把 GPT Researcher 概括成初始化时已确定完整图也过强，后续查询与失败会影响实际展开。页面结论以源码及执行事件为准，不采用这些错误概括。检索日志的“web”不代表真实联网。',
          'design_implication':'值得观察的控制边界是：第一层证据返回后，哪些后续问题现在值得展开。当前源码还把不同父结果的递归子树放在 for 循环中依次执行；优化前须确认依赖、来源去重和共享状态。',
          'spec':spec,'nodes':nodes,'edges':edges,'requests':rr,'report_finish_reason':final,'status_label':'完整流程正常结束；报告另列事实核对问题',
          'links':[['完整原始证据包',WEB+'evidence/upstream-workflows-20261030-v003/raw.tar.gz'],['本次报告',WEB+'results/natural-dag-20261029/frameworks/gptr-report.md'],['官方递归实现','https://github.com/assafelovic/gpt-researcher/blob/3582a6841fe7dc801e2a34e34ee408641aea9bce/gpt_researcher/skills/deep_research.py#L418']],
          'data_url':WEB+'results/natural-dag-20261029/frameworks/gptr.json'}
    (OUT/'gptr-report.md').write_text(report,encoding='utf8');return data


def odr(case):
    d=EVIDENCE/'runs'/case;c=read(d/'completion.json');spec=read(d/'spec.json');start=c['started_wall_time'];rr=requests(case,start)
    events=[json.loads(l)for l in (d/'events.jsonl').read_text(encoding='utf8').splitlines()]
    subgraphs=[e for e in events if e['event']=='on_chain_start' and e['name']=='LangGraph' and isinstance(e['data'].get('input'),dict) and 'research_topic'in e['data']['input']]
    nodes=[node('task','初始研究任务',0,0,0,query=spec['query'],role='只给初始研究目标，不给分支列表或 Agent 数。',relation='进入官方 ODR 简报与主管流程。')];edges=[];assigned=set();children=[]
    for i,e in enumerate(subgraphs):
        q=e['data']['input']['research_topic'];ending=next((x for x in events if x['event']=='on_chain_end' and x['run_id']==e['run_id']),None)
        en=ending['wall_time']-start if ending else c['duration_seconds'];st=e['wall_time']-start
        ids=[r for r in rr if q in '\n'.join(str(m.get('content','')) for m in r['request'].get('messages',[])) and st-.1<=r['start']<en]
        for r in ids:r['stage']='子研究推理 / 压缩'
        assigned.update(r['id']for r in ids)
        n=node(f'worker-{i}',f'主管委派 · 研究员 {i+1}',st,en,2,(i-(len(subgraphs)-1)/2), 'worker',q,'主管的 ConductResearch 调用被原生工具节点接纳，启动有独立状态的 researcher_subgraph；内部可多轮调用模型、MCP 检索，再压缩结果。','接主管在线生成的研究主题；输出 compressed_research 后返回主管。研究员节点的多次循环不重复计为新 Agent。',ids,'独立研究状态 · 多轮推理与检索')
        children.append(n);nodes.append(n)
    report_start=next(e['wall_time']-start for e in events if e['event']=='on_chain_start' and e['name']=='final_report_generation')
    first=min((n['start']for n in children),default=report_start);last=max((n['end']for n in children),default=report_start)
    before=[r for r in rr if r['id']not in assigned and r['start']<first]
    for r in before:r['stage']='研究简报 / 主管规划'
    nodes.append(node('supervisor','研究简报 → 主管委派',min(r['start']for r in before),max(r['end']for r in before),1,role='ODR 自带主管提示与 ConductResearch 工具。Qwen 在运行中生成研究主题与委派调用；上限 3 只限制可执行数量，不在初始任务里指定必须开几个。',relation='先生成研究简报，再由主管决定具体分支；图显示实际被接纳的子研究。',requests=before,caption='查看真实 ConductResearch 参数'))
    edges.append({'from':'task','to':'supervisor'});edges.extend({'from':'supervisor','to':n['id']}for n in children)
    after=[r for r in rr if r['id']not in assigned and r not in before]
    for r in after:r['stage']='主管汇合 / 最终报告'
    if children:
        nodes.append(node('join','研究结果返回主管',last,last,3,kind='join',role='原生 gather 等待已接纳研究子图返回；汇合不是额外的 Agent。',relation='所有已接纳研究单元结束后，主管才获得压缩研究结果。',caption='独立子图结束后汇合'))
        edges.extend({'from':n['id'],'to':'join'}for n in children)
    nodes.append(node('report','主管收束 → 最终报告',min(r['start']for r in after),max(r['end']for r in after),4 if children else 2,role='主管收束后进入最终报告；是否有新检索证据须依据实际工具记录。'))
    # Set these separately to keep the exported relation explicit.
    nodes[-1].update(lane=0,relation='主管收束后进入原生最终报告阶段。',request_ids=[r['id']for r in after],caption='点击检查收束响应与最终输出')
    edges.append({'from':'join' if children else 'supervisor','to':'report'})
    report=(d/'report.md').read_text(encoding='utf8');tools=Counter(e['name']for e in events if e['event']=='on_tool_start')
    final=rr[-1]['finish_reason']
    tag='odr-wide' if case=='odr-qwen-v005-20261030' else 'odr-focused' if case=='odr-qwen-v006-20261030' else 'odr'
    cc=spec['config']['configurable']
    data={'id':tag,'title':'Open Deep Research · '+({'odr':'澄清资料可取证','odr-wide':'宽问题主管委派','odr-focused':'误判资料缺失'}[tag]),'case_id':case,'started_wall_time':start,'duration_seconds':c['duration_seconds'],
          'finding':f'Qwen 在主管阶段生成委派，官方 ODR 实际启动了 {len(children)} 个独立研究子图；内部工具和模型请求真实重叠。' if children else '主管误把工具中已加载的资料当成用户尚未提供的输入，未委派便结束。工具可用不等于模型正确理解资料获取方式。',
          'scope':f'保留原生图、主管提示与工具选择逻辑，通过官方 MCP 接口提供固定源码检索。并发上限{cc["max_concurrent_research_units"]}、主管轮数{cc["max_researcher_iterations"]}、研究轮数{cc["max_react_tool_calls"]}是配置预算。窄问题同时调整了任务、语料片段和轮数，不能归因于单个变量。',
          'stats':[['独立子研究单元',len(children)],['实际模型请求',len(rr)],['模型请求在途峰值',peak(rr)],['总耗时',f"{c['duration_seconds']:.2f} s"]],
          'query':spec['query'],'quality':f'最终 API finish_reason={final}；报告 {len(report)} 字符；真实 source_search 调用 {tools["source_search"]} 次。'+('最终报告截断，不能算完整研究交付；子研究与汇合的执行记录有效。' if final=='length' else '流程正常结束；已取证内容仍逐项核对，不报告任务准确率。' if children else '流程正常结束，但报告要求用户补材料；未获取新证据，不算完成源码审查。'),
          'design_implication':'控制边界清楚地落在主管提出 ConductResearch 与研究子图启动之间。可以观察待展开分支、汇合等待和结果缺口，再研究结合引擎状态的推进；现有上限与 gather 本身属于原框架能力。',
          'spec':spec,'nodes':nodes,'edges':edges,'requests':rr,'native_tools':dict(tools),'report_finish_reason':final,
          'links':[['完整原始证据包',WEB+'evidence/upstream-workflows-20261030-v003/raw.tar.gz'],['本次报告',WEB+'results/natural-dag-20261029/frameworks/'+tag+'-report.md'],['官方主管执行','https://github.com/langchain-ai/open_deep_research/blob/1b7d2e80db9faa586165c60e09096dbbfd483a64/src/open_deep_research/deep_researcher.py#L282']],
          'data_url':WEB+'results/natural-dag-20261029/frameworks/'+tag+'.json'}
    data['status_label']='拓扑已采集；最终报告截断' if final=='length' else '委派、取证、报告流程正常结束' if children else '正常结束；误判输入，未完成审查'
    if tag=='odr':
        data['quality']+=' 人工核对发现报告的 GPT 总工作量公式有误：不是 breadth+breadth/2+…，每个成功父分支都可能继续递归，且 new_breadth 至少为2。本次另一实测为2+2×2=6个子实例；该错误原文保留。'
    data['scope']=f'原生 ODR 图、主管提示与工具选择逻辑保留；原生 MCP 提供固定官方源码检索。并发上限{cc["max_concurrent_research_units"]}、主管轮数{cc["max_researcher_iterations"]}、研究轮数{cc["max_react_tool_calls"]}是配置预算。'+({'odr':'初始任务明确资料已在工具中，无需用户补文件；未指定子研究数或预写分支。','odr-wide':'与窄问题的任务、语料片段和轮数均不同，不做耗时排名。','odr-focused':'相对宽问题同时改变任务、片段和轮数；实际零委派的原因以模型响应为准。'}[tag])
    if not children:
        nodes[1].update(title='主管思考 → 直接收束',role='主管只调用 think_tool 与 ResearchComplete，没有提出 ConductResearch。',relation='接研究简报，选择结束研究阶段，没有创建研究子图。',caption='没有生成研究员；点击查看真实响应')
        data['design_implication']='这轮没有可供派发优化的子研究前沿。原因是主管把工具可取证误判为缺少用户输入；这是任务说明与工具能力的接口问题，不能归因于引擎排队，也不能用强制 Agent 数掩盖。'
    (OUT/(tag+'-report.md')).write_text(report,encoding='utf8');return data


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--gptr-case',default='gptr-qwen-v005-20261030')
    parser.add_argument('--odr-case',default='odr-qwen-v007-20261030')
    args=parser.parse_args()
    OUT.mkdir(exist_ok=True)
    catalogue=provenance_catalogue()
    upstream={r['run_id']:r for r in catalogue['upstream_runs']}
    for name,func,case in [('gptr',gptr,args.gptr_case),('odr',odr,args.odr_case),('odr-focused',odr,'odr-qwen-v006-20261030'),('odr-wide',odr,'odr-qwen-v005-20261030')]:
        data=func(case)
        data.update(provenance=upstream[case]['provenance'],experiment_change=upstream[case]['experiment_change'])
        write(OUT/(name+'.json'),data)
        assert all(n['start']<=n['end']+.01 for n in data['nodes'])
        byid={n['id']:n for n in data['nodes']}
        assert all(byid[e['from']]['end']<=byid[e['to']]['start']+.2 for e in data['edges']),name
        assert len({r['id']for r in data['requests']})==len(data['requests'])
        assert Counter(rid for n in data['nodes'] for rid in n['request_ids'])==Counter(r['id'] for r in data['requests']),name
        print(name,len(data['nodes']),len(data['requests']),data['report_finish_reason'])
    audit=read(BASE/'evidence/autonomy-20261030-v002/summary.json')['runs']
    labels={'research-native':'六题调查·原生','research-allow':'六题调查·放宽 workflow','research-encourage':'六题调查·委派建议',
            'research-high':'六题调查·high（不支持）','research-medium':'六题调查·medium','research-xhigh-20261030':'六题调查·xhigh',
            'simple-encourage':'简单题·委派建议','simple-xhigh-calibration-20261030':'简单题·xhigh',
            'runtime-audit-native':'架构核对·原生','runtime-audit-encourage':'架构核对·委派建议',
            'runtime-audit-autodelegate-20261030':'架构核对·拆分评估策略',
            'multi-object-native-20261030':'四份虚构资料·原生','multi-object-autodelegate-20261030':'四份虚构资料·拆分评估策略',
            'source-review-native-20261030':'源码审查·原生（超时）','source-review-autodelegate-20261030':'源码审查·拆分评估（超限）',
            'open-research-encourage':'联网调查·委派建议','team-research':'六题调查·Agent Teams','team-open-research':'联网调查·Agent Teams'}
    for r in audit:
        r['label']=labels[r['case_id']]
        r['outcome']='仅根 Session；未委派'
        if r['case_id']=='research-high':r['outcome']='参数不支持；非行为样本'
        elif r['case_id']=='source-review-native-20261030':r['outcome']='900秒 watchdog；无审查报告'
        elif r['case_id']=='source-review-autodelegate-20261030':r['outcome']='上下文超限；无审查报告'
        elif r['exit_code']!=0:r['outcome']='输出触顶等异常；未委派'
    for row in catalogue['dsh_runs']:
        row['summary']=next(r for r in audit if r['case_id']==row['run_id'])
    write(OUT/'experiment-catalogue.json',catalogue)
    write(OUT/'index.json',{'catalogue_path':'experiment-catalogue.json',
        'runs':[{'id':'odr','label':'ODR v007 · 取证澄清','path':'odr.json'},{'id':'odr-focused','label':'ODR v006 · 资料误判','path':'odr-focused.json'},{'id':'odr-wide','label':'ODR v005 · 宽题截断','path':'odr-wide.json'},{'id':'gptr','label':'GPT Researcher v005 · 递归','path':'gptr.json'}],
        'dsh_runs':audit,'audit_note':'18 组均未观察到子 Session；其中参数拒绝、输出触顶、超时和上下文失败单列，不能算作 18 次成功任务，也不用于估计普遍的自然委派概率。',
        'incidents':[{'name':'GPT Researcher v001','finding':'旧运行只返回研究 context，没有调用 write_report；不能算完整报告成功。'},
                     {'name':'GPT Researcher v002','finding':'默认嵌入压缩请求落到不支持 embeddings 的服务，404；只终止自己的进程，保留记录。'},
                     {'name':'GPT Researcher v003','finding':'6 个子实例已创建；汇总上下文超 65536，报告为空。'},
                     {'name':'GPT Researcher v004','finding':'6 个子实例、23 次请求；角色生成一次 length，报告也 length 截断，并错误概括了递归机制。运行拓扑有效，报告质量未通过。'},
                     {'name':'ODR 旧 v002','finding':'3 个研究单元发生并行，但无检索工具配置；模型提出不存在的 tavily_search。源码会在异常后结束主管阶段，旧 trace 中最终报告早于部分子研究压缩结束；不算成功研究。'},
                     {'name':'ODR 新 v003','finding':'本地入口的 Python import path 未设置，初始化失败；没有请求模型。修正脚本搜索路径后以 v004 独立运行。'},
                     {'name':'ODR 新 v004','finding':'原生创建3个子研究单元，20次真实检索，21次模型请求；压缩与最终报告有 length 截断。拓扑证据成立，未算完整报告成功。'}],
        'coding_note':'原图是候选生成 / 测试 / 修复抽象，没有唯一的“Coding Harness”官方实现。LiveCodeBench 是 benchmark，其并行采样不等于子 Agent。已有 DSH 编程任务实际修复三个文件、原测试从 1/7 提升到 7/7，仍只有一个 Session。',
        'crag_note':'执行了官方 process_flag 原函数的三组分数边界：Correct / Ambiguous / Incorrect 均符合路由规则。分数为人工边界输入；未复现训练评估器、网页检索与完整生成，不冒充 CRAG 全量实验或多 Agent 阳性。'})
    for folder in ['autonomy-20261030-v002','upstream-workflows-20261030-v003']:
        path=BASE/'evidence'/folder/'index.json'
        metadata=read(path)
        metadata['provenance_catalogue']='../../results/natural-dag-20261029/frameworks/experiment-catalogue.json'
        metadata['scope_note']='诊断尝试，含失败与重跑；任务来源和未完成范围见统一索引。原始包字节不变。'
        write(path,metadata)


if __name__=='__main__':main()
