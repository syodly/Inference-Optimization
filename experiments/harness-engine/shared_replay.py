"""Fixed-work shared-engine counterfactuals from complete independent-tenant traces.

Real GPU model requests, real tools and the original within-tenant arrival indices
are retained. Frozen upstream text isolates dispatch and does not establish live
answer quality. Both target and background decode identical per-call quotas.
"""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import shutil
import time

from analyze import read
from engine import Engine, Journal
from export_run import export
from replay import ReplayHarness
from scheduler import Controller
from shared import TenantJournal, score_tenants


async def execute(args):
    source = args.trace.resolve()
    cfg = json.loads((source/'config.json').read_text())
    source_summary = json.loads((source/'summary.json').read_text())
    if not (source_summary['trace_audit']['passed'] and source_summary['engine_errors'] == source_summary['root_errors'] == 0):
        raise ValueError('Use a complete independently audited shared-engine source')
    tasks_path = Path(cfg['tasks'])
    tasks = {t['task_id']: t for t in read(tasks_path)}
    active = [args.only_tenant] if args.only_tenant else list(cfg['tenant_specs'])
    selected = [tasks[k] for k in cfg['task_ids'] if tasks[k]['tenant_id'] in active]
    selected_ids = {t['task_id'] for t in selected}
    requests = [r for r in read(source/'requests.jsonl') if r['root_id'] in selected_ids]
    responses = [r for r in read(source/'responses.jsonl') if r['root_id'] in selected_ids]
    if not (len(requests) == len(responses) == len(selected)*10 and all(r.get('usage', {}).get('completion_tokens') for r in responses)):
        raise ValueError('Source must have every mandatory model response and a measured decode quota')
    specs = {}
    for tenant in active:
        values = dict(cfg['tenant_specs'][tenant])
        if tenant == 'target':
            values.update(policy=args.policy, cap=args.cap, session_cap=args.session_cap,
                          history_budget_tokens=args.history_budget_tokens,
                          measure_prompts=args.policy in ['size_return', 'history_budget', 'history_pressure'])
        specs[tenant] = argparse.Namespace(**values)
    journal = Journal(args.out)
    config = {**cfg, 'out': str(args.out), 'started': time.time(), 'policy': args.policy,
              'cap': args.cap, 'session_cap': args.session_cap,
              'history_budget_tokens': args.history_budget_tokens,
              'count': len(selected), 'task_ids': [t['task_id'] for t in selected],
              'expected_model_calls': len(requests), 'expected_agent_executions': len(selected)*4,
              'tenant_specs': {k: vars(v) for k, v in specs.items()},
              'replay': {'source_trace': str(source),
                         'source_config_sha256': hashlib.sha256((source/'config.json').read_bytes()).hexdigest(),
                         'source_request_sha256': hashlib.sha256((source/'requests.jsonl').read_bytes()).hexdigest(),
                         'frozen_prompts': True, 'fixed_completion_token_quota': True,
                         'real_tools': True, 'live_quality_evaluation': False,
                         'only_tenant': args.only_tenant, 'original_arrival_indices_preserved': True},
              'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}}
    (args.out/'config.json').write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
    (args.out/'sources').mkdir()
    for p in Path(__file__).parent.glob('*.py'): shutil.copy2(p, args.out/'sources'/p.name)
    engine = Engine(cfg['url'], cfg['model'], journal, True, 'qwen', 'low')
    stop, controllers = asyncio.Event(), {}
    try:
        await engine.health()
        observed = await engine.sample()
        if args.policy in ['pressure', 'history_pressure'] and any(observed.get(k) is None for k in ['kv_usage', 'waiting']):
            raise RuntimeError('Actual engine telemetry is required')
        await engine.reset_cache()
        poll = asyncio.create_task(engine.poll(stop))
        loops, jobs = [], []
        for tenant, settings in specs.items():
            trace = TenantJournal(journal, tenant)
            controller = Controller(settings.policy, settings.cap, engine, trace,
                                    settings.session_cap, settings.starvation_seconds,
                                    settings.history_budget_tokens, settings.history_output_reserve)
            controllers[tenant] = controller
            loops.append(asyncio.create_task(controller.loop()))
            harness = ReplayHarness(settings, engine, controller, trace, requests, responses)
            original_ids = [k for k in cfg['task_ids'] if tasks[k]['tenant_id'] == tenant]
            jobs.extend(harness.root(tasks[k], i) for i, k in enumerate(original_ids) if k in selected_ids)
        await asyncio.gather(*jobs)
        for controller in controllers.values(): controller.close()
        await asyncio.gather(*loops)
        stop.set(); await poll; await engine.sample()
        journal.write('events', event='run_complete', expected_model_calls=config['expected_model_calls'])
    finally:
        stop.set()
        for controller in controllers.values(): controller.close()
        await engine.close(); journal.close()
    return config, requests, responses


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--trace', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--policy', choices=['native', 'fixed', 'pressure', 'return_priority', 'size_return',
                                        'session_return', 'history_budget', 'history_pressure'], default='native')
    ap.add_argument('--cap', type=int, default=24)
    ap.add_argument('--session-cap', type=int, default=18)
    ap.add_argument('--history-budget-tokens', type=int, default=200000)
    ap.add_argument('--only-tenant', choices=['target', 'background'])
    args = ap.parse_args()
    cfg, original_requests, original_responses = asyncio.run(execute(args))
    # Reuse timing/span/ledger analysis, then explicitly remove frozen-answer scores.
    summary = score_tenants(args.out, cfg)
    actual = {r['call_id']: r for r in read(args.out/'requests.jsonl')}
    original = {r['call_id']: r for r in original_responses}
    responses = read(args.out/'responses.jsonl')
    same = sum(actual.get(r['call_id'], {}).get('payload', {}).get('messages') == r['payload']['messages'] for r in original_requests)
    quotas = sum(r.get('usage', {}).get('completion_tokens') == original[r['call_id']]['usage']['completion_tokens'] for r in responses)
    summary['quality'] = None
    summary.pop('quality_by_dataset', None)
    summary.pop('exact_correct_root_latency_seconds', None)
    tenants = summary.pop('quality_by_tenant')
    for name, entry in tenants.items():
        groups = entry.pop('quality_by_dataset')
        for group in groups.values():
            group.pop('em', None); group.pop('f1', None)
        entry['latency_by_dataset'] = groups
        sub = args.out/'tenants'/name
        sub_summary = json.loads((sub/'summary.json').read_text())
        sub_summary.update(quality=None, quality_protocol='Not evaluated: frozen-output fixed-work diagnostic.',
                           latency_by_dataset=groups)
        sub_summary.pop('quality_by_dataset', None); sub_summary.pop('exact_correct_root_latency_seconds', None)
        (sub/'summary.json').write_text(json.dumps(sub_summary, ensure_ascii=False, indent=2), encoding='utf-8')
        (sub/'scored.jsonl').rename(sub/'frozen_output_scored.jsonl')
    summary['latency_by_tenant'] = tenants
    summary['quality_protocol'] = 'Not evaluated: frozen upstream outputs; forced identical per-call decode quotas for both tenants.'
    summary['replay_accounting'] = {'source_calls': len(original_requests), 'identical_input_prompts': same,
        'quota_matches': quotas, 'source_completion_tokens': sum(r['usage']['completion_tokens'] for r in original_responses),
        'live_completion_tokens': sum(r.get('usage', {}).get('completion_tokens', 0) for r in responses),
        'full_source_trace': str(args.trace), 'both_tenants_frozen': True}
    summary['limitation'] = 'Matched-work independent-controller diagnostic; frozen answer quality is not a live quality result. Engine counters are global.'
    (args.out/'scored.jsonl').rename(args.out/'frozen_output_scored.jsonl')
    (args.out/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    pieces = '；'.join(f"{name}均值{v['root_latency_seconds']['mean']:.2f}秒/P95 {v['root_latency_seconds']['p95']:.2f}秒"
                       for name, v in tenants.items())
    record = (f"\n\n## {args.out.name} · 共享引擎同工作量因果对照\n\n"
              f"本轮使用{args.trace.name}的完整独立控制器记录，目标策略{args.policy}、调用上限{args.cap}、"
              f"历史软预算{args.history_budget_tokens}，租户选择{args.only_tenant or '全部'}。所有模型请求继续在双卡Qwen3.8-27B真实执行，"
              f"真实检索、来源核验和前后依赖重新执行，上游文本与每调用解码配额冻结，保留各控制器的原任务到达索引。"
              f"实际输入一致{same}/{len(original_requests)}，配额一致{quotas}/{len(original_responses)}，{pieces}。"
              '目标只看自己的图和全局引擎状态，不获得背景图、准确未来工具时间或隐藏答案。两组全部等待和真实解码量一并报告，'
              '不能把背景受损当作系统整体收益。每个控制器独立核对完整Agent执行、模型、工具、历史账本与依赖。'
              '由于冻结了前序输出，本轮只用于系统干扰和调度归因，不报告自主闭环答案质量；原始响应和冻结结果哈希均保留。\n')
    (args.out/'research_record.md').write_text(record, encoding='utf-8')
    with Path('RESEARCH_LOG.md').open('a', encoding='utf-8') as f: f.write(record)
    export(args.out, Path(__file__).resolve().parent)
    print(json.dumps({'run_id': args.out.name, 'trace_audit': summary['trace_audit'],
                      'replay_accounting': summary['replay_accounting'], 'latency_by_tenant': tenants}, indent=2))
    if not (summary['trace_audit']['passed'] and same == quotas == len(original_requests)
            and summary['engine_errors'] == summary['root_errors'] == 0):
        raise RuntimeError('Keep incomplete replay for inspection before further comparison')


if __name__ == '__main__':
    main()
