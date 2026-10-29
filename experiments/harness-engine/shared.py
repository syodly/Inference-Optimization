"""One real shared-engine experiment with independent tenant controllers.

Both actors execute useful complete research tasks. The target controller sees
global engine telemetry, its own sessions and tools, but no background DAG/state.
"""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import shutil
import time

from analyze import analyze, read
from audit import audit
from engine import Engine, Journal
from export_run import export
from run import Harness
from scheduler import Controller


class TenantJournal:
    def __init__(self, journal, tenant):
        self.journal, self.tenant = journal, tenant

    def write(self, stream, **fields):
        return self.journal.write(stream, tenant_id=self.tenant, **fields)


def tenant_args(args, tenant):
    target = tenant == 'target'
    policy = args.policy if target else 'native'
    return argparse.Namespace(
        workflow='verified', branches=3, top_k=3, source_format='text', thinking=True,
        sampling_profile='qwen', reasoning_effort='low', query_tokens=40,
        draft_tokens=4096, evidence_tokens=4096, answer_tokens=4096, seed=args.seed,
        tool_profile='natural', tool_delay=0, verify_delay=args.verify_delay if target else 0,
        verify_jitter=0, cohort=16 if target else 0,
        arrival_interval=args.arrival_interval if target else 1,
        second_wave=0 if target else args.background_arrival,
        policy=policy, cap=args.cap if target else 128, session_cap=args.session_cap,
        starvation_seconds=120, history_budget_tokens=args.history_budget_tokens,
        history_output_reserve=1024,
        measure_prompts=policy in ['size_return', 'history_budget', 'history_pressure'])


async def execute(args):
    tasks = read(args.tasks)
    active = ['target', 'background'] if args.background else ['target']
    selected = [t for t in tasks if t['tenant_id'] in active]
    specs = {tenant: tenant_args(args, tenant) for tenant in active}
    journal = Journal(args.out)
    config = {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()}
    config.update(workflow='verified', branches=3, split='evaluation', task_ids=[t['task_id'] for t in selected],
                  count=len(selected), started=time.time(), expected_model_calls=len(selected)*10,
                  trace_semantics_version=2, expected_agent_executions=len(selected)*4,
                  data_manifest=json.loads((args.tasks.parent/'manifest.json').read_text(encoding='utf-8')),
                  tasks_sha256=hashlib.sha256(args.tasks.read_bytes()).hexdigest(),
                  tenant_specs={k: vars(v) for k, v in specs.items()},
                  observation_boundary='Independent controllers; target sees own DAG/tools and shared engine metrics only.',
                  source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in Path(__file__).parent.glob('*.py')})
    for name in ['server', 'model_manifest', 'model_verification', 'source_revision', 'env']:
        path = Path('state')/(name+'.json')
        if path.exists(): config[name] = json.loads(path.read_text())
    server_log = Path(config.get('server', {}).get('log', 'logs/engine-graph.log'))
    if server_log.exists():
        lines = server_log.read_text(errors='replace').splitlines()
        config['engine_capacity_evidence'] = {
            key: next((line for line in reversed(lines) if fragment in line), None)
            for key, fragment in [('kv_capacity', 'GPU KV cache size:'),
                                  ('block_size', 'Setting attention block size to'),
                                  ('hybrid_cache_mode', 'Mamba cache mode is set to')]}
    (args.out/'config.json').write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
    (args.out/'sources').mkdir()
    for path in Path(__file__).parent.glob('*.py'): shutil.copy2(path, args.out/'sources'/path.name)
    engine = Engine(args.url, args.model, journal, True, 'qwen', 'low')
    stop = asyncio.Event()
    controllers = {}
    try:
        journal.write('events', event='engine_health', models=await engine.health())
        observed = await engine.sample()
        if specs['target'].policy in ['pressure', 'history_pressure'] and any(
                observed.get(k) is None for k in ['kv_usage', 'waiting']):
            raise RuntimeError('The actual shared engine telemetry is required')
        await engine.reset_cache()
        poll = asyncio.create_task(engine.poll(stop))
        loops, jobs = [], []
        for tenant, settings in specs.items():
            trace = TenantJournal(journal, tenant)
            controller = Controller(settings.policy, settings.cap, engine, trace, settings.session_cap,
                                    settings.starvation_seconds, settings.history_budget_tokens,
                                    settings.history_output_reserve)
            controllers[tenant] = controller
            loops.append(asyncio.create_task(controller.loop()))
            harness = Harness(settings, engine, controller, trace)
            own_tasks = [t for t in selected if t['tenant_id'] == tenant]
            jobs.extend(harness.root(t, i) for i, t in enumerate(own_tasks))
        await asyncio.gather(*jobs)
        for controller in controllers.values(): controller.close()
        await asyncio.gather(*loops)
        stop.set(); await poll
        await engine.sample()
        journal.write('events', event='run_complete', expected_model_calls=config['expected_model_calls'])
    finally:
        stop.set()
        for controller in controllers.values(): controller.close()
        await engine.close(); journal.close()
    return config


def score_tenants(run, config):
    """Offline: independent trace audits, then both tenants' quality and latency."""
    tasks_path = Path(config['tasks'])
    selected = {t['task_id']: t for t in read(tasks_path) if t['task_id'] in config['task_ids']}
    summary = analyze(run, tasks_path.parent/'answers.jsonl', tasks_path)
    tenant_summaries, audits = {}, {}
    streams = ['requests', 'responses', 'events', 'sessions', 'tools', 'roots', 'metrics']
    original = {name: read(run/(name+'.jsonl')) for name in streams}
    for tenant, settings in config['tenant_specs'].items():
        sub = run/'tenants'/tenant; sub.mkdir(parents=True)
        ids = {k for k, task in selected.items() if task['tenant_id'] == tenant}
        local_config = {**config, **settings, 'task_ids': sorted(ids), 'count': len(ids),
                        'expected_model_calls': len(ids)*10, 'expected_agent_executions': len(ids)*4}
        (sub/'config.json').write_text(json.dumps(local_config, ensure_ascii=False, indent=2), encoding='utf-8')
        for name, rows in original.items():
            own = []
            for row in rows:
                owner = row.get('tenant_id') or selected.get(row.get('root_id'), {}).get('tenant_id')
                if owner == tenant or owner is None:
                    own.append(row)
            (sub/(name+'.jsonl')).write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in own), encoding='utf-8')
        tenant_summaries[tenant] = analyze(sub, tasks_path.parent/'answers.jsonl', tasks_path)
        audits[tenant] = audit(sub)
    ids = [r['call_id'] for r in original['requests']]
    complete = len(ids) == len(set(ids)) == config['expected_model_calls']
    summary['trace_audit'] = {'passed': complete and all(a['passed'] for a in audits.values()),
                              'scope': 'Every model/tool/Agent span, dependency and ledger audited within its independent tenant; global call IDs must be disjoint.',
                              'tenants': audits, 'global_request_count': len(ids)}
    summary['quality_by_tenant'] = {name: {'root_latency_seconds': s['root_latency_seconds'],
                                           'quality_by_dataset': s['quality_by_dataset'],
                                           'model_calls': s['model_calls'], 'tokens': s['tokens'],
                                           'batch_makespan_seconds': s['batch_makespan_seconds'],
                                           'engine_errors': s['engine_errors'], 'root_errors': s['root_errors'],
                                           'parse_errors': s['parse_errors'],
                                           'length_finishes': s['length_finishes'],
                                           'control_observations': s['control_observations'],
                                           'cache_by_stage': s['cache_by_stage']}
                                    for name, s in tenant_summaries.items()}
    summary['limitation'] = ('One deliberately shared-engine workload, not concurrent policy experiments. '
                             'Tenant frontend counters are local; engine metrics/counter deltas are global. '
                             'Background calibration questions are useful load, not held-out generalization evidence.')
    (run/'audit.json').write_text(json.dumps(summary['trace_audit'], indent=2), encoding='utf-8')
    (run/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--tasks', type=Path, default=Path('datasets/shared-load/tasks.jsonl'))
    ap.add_argument('--url', default='http://127.0.0.1:18081')
    ap.add_argument('--model', default='qwen27b')
    ap.add_argument('--policy', choices=['native', 'fixed', 'pressure', 'return_priority', 'size_return',
                                        'session_return', 'history_budget', 'history_pressure'], default='native')
    ap.add_argument('--cap', type=int, default=24)
    ap.add_argument('--session-cap', type=int, default=18)
    ap.add_argument('--history-budget-tokens', type=int, default=200000)
    ap.add_argument('--seed', type=int, default=1729)
    ap.add_argument('--background', action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument('--arrival-interval', type=float, default=2)
    ap.add_argument('--background-arrival', type=float, default=20)
    ap.add_argument('--verify-delay', type=float, default=0)
    args = ap.parse_args()
    config = asyncio.run(execute(args))
    summary = score_tenants(args.out, config)
    pieces = []
    for name, data in summary['quality_by_tenant'].items():
        grouped = '、'.join(f"{dataset}:EM={g['em']:.3f}/F1={g['f1']:.3f}"
                           for dataset, g in data['quality_by_dataset'].items())
        pieces.append(f"{name}平均{data['root_latency_seconds']['mean']:.2f}秒，P95={data['root_latency_seconds']['p95']:.2f}秒，{grouped}")
    record = (f"\n\n## {args.out.name} · 独立任务共享引擎\n\n"
              f"本轮使用同一双卡Qwen3.8-27B真实引擎，target策略为{args.policy}，固定16个混合研究任务，"
              f"每隔{args.arrival_interval}秒提交；背景{'启用' if args.background else '未启用'}，启用时四道不重合长文题从"
              f"{args.background_arrival}秒开始提交，目标来源核验附加等待{args.verify_delay}秒，"
              f"各自完成真实检索、引用核验与父汇合。实际模型调用"
              f"{summary['model_calls']}/{summary['expected_model_calls']}，模型错误{summary['engine_errors']}、任务错误{summary['root_errors']}。"
              + '；'.join(pieces) + '。目标控制器只看自己的任务及全局引擎指标，不读取背景图或未来到达时间；'
              '两组完整质量、全部等待和背景受到的影响均报告，不能把让背景变慢算作整体改善。背景使用已有校准题作为真实工作，'
              '不声称新的隐藏测试集；问题和来源未补字或删改。每组独立核对Agent执行、模型、工具、账本与依赖，'
              '全局核对调用ID和总工作量。此轮只是完整实测记录，机制归因仍须同负载强基线及固定工作量对照。\n')
    (args.out/'research_record.md').write_text(record, encoding='utf-8')
    with Path('RESEARCH_LOG.md').open('a', encoding='utf-8') as f: f.write(record)
    export(args.out, Path(__file__).resolve().parent)
    print(json.dumps({'run_id': args.out.name, 'trace_audit': summary['trace_audit'],
                      'quality_by_tenant': summary['quality_by_tenant']}, ensure_ascii=False, indent=2))
    if not summary['trace_audit']['passed'] or summary['engine_errors'] or summary['root_errors']:
        raise RuntimeError('Keep the complete failed trial; inspect before starting another comparison')


if __name__ == '__main__':
    main()
