"""Real-engine, fixed-input/token-quota causal replay. Supplement to closed-loop trials.

Upstream model outputs are frozen from an audited trace; real tools re-execute.
This isolates dispatch effects and cannot establish live answer quality.
"""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import shutil
import time

from analyze import analyze, read, distribution
from audit import audit
from engine import Engine, Journal
from run import Harness
from scheduler import Controller


class ReplayHarness(Harness):
    def __init__(self, args, engine, controller, journal, requests, responses):
        super().__init__(args, engine, controller, journal)
        self.frozen_requests = {(r['root_id'], r['node_id'], r['stage']): r for r in requests}
        self.frozen_responses = {r['call_id']: r for r in responses}

    async def model(self, root, session, stage, messages, budget):
        recorded = self.frozen_requests[(root, session, stage)]
        frozen = self.frozen_responses[recorded['call_id']]
        original = recorded['payload']
        # The frozen predecessors/tool results must reconstruct identical API input.
        if messages != original['messages']:
            raise ValueError('Replay history differs from source trace: ' + recorded['call_id'])
        await self.controller.admit(root, session, stage)
        call_id = recorded['call_id']
        self.activation += 1
        self.journal.write('sessions', event='activation_start', root_id=root, session_id=session,
                           activation_id=call_id, messages=messages)
        try:
            quota = frozen['usage']['completion_tokens']
            payload = {**original, 'max_tokens': quota, 'min_tokens': quota, 'ignore_eos': True}
            payload.pop('priority', None)
            if self.args.policy == 'backend_priority':
                payload['priority'] = {'query': 0, 'draft': -1, 'evidence': -2, 'synthesis': -3}[stage]
            actual = await self.engine.generate(
                call_id=call_id, root_id=root, node_id=session, stage=stage, messages=messages,
                max_tokens=quota, seed=self.args.seed, generation_overrides=payload)
            if actual.get('usage', {}).get('completion_tokens') != quota:
                raise ValueError('Engine did not execute fixed token quota: ' + call_id)
            self.journal.write('replay_frozen_outputs', root_id=root, node_id=session, stage=stage,
                               call_id=call_id, quota=quota,
                               text_sha256=hashlib.sha256(frozen['text'].encode()).hexdigest(),
                               notice='Downstream receives source-trace output, not this replay generation.')
            return frozen
        finally:
            self.controller.release()
            self.journal.write('sessions', event='activation_end', root_id=root, session_id=session,
                               activation_id=call_id)


async def execute(args):
    source = args.trace.resolve()
    cfg = json.loads((source / 'config.json').read_text())
    requests = read(source / 'requests.jsonl')
    responses = read(source / 'responses.jsonl')
    if len(responses) != cfg['expected_model_calls'] or any(r.get('error') for r in responses):
        raise ValueError('Replay requires a complete source trace')
    source_audit = json.loads((source / 'audit.json').read_text())
    if not source_audit['passed']:
        raise ValueError('Source causal audit failed')
    original_namespace = argparse.Namespace(**cfg)
    for key in ['tasks', 'out']:
        setattr(original_namespace, key, Path(getattr(original_namespace, key)))
    original_namespace.out = args.out
    original_namespace.policy, original_namespace.cap = args.policy, args.cap
    original_namespace.session_cap = args.session_cap
    tasks = {t['task_id']: t for t in read(original_namespace.tasks)}
    selected = [tasks[k] for k in cfg['task_ids']]
    journal = Journal(args.out)
    engine = Engine(original_namespace.url, original_namespace.model, journal)
    controller = Controller(args.policy, args.cap, engine, journal, args.session_cap)
    replay_cfg = {**cfg, 'out': str(args.out), 'policy': args.policy, 'cap': args.cap,
                  'session_cap': args.session_cap, 'started': time.time(),
                  'replay': {'source_trace': str(source), 'source_config_sha256': hashlib.sha256((source / 'config.json').read_bytes()).hexdigest(),
                             'frozen_prompts': True, 'fixed_completion_token_quota': True,
                             'real_tools': True, 'live_quality_evaluation': False},
                  'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}}
    state_server = Path('state/server.json')
    if state_server.exists():
        replay_cfg['server'] = json.loads(state_server.read_text())
    (args.out / 'config.json').write_text(json.dumps(replay_cfg, indent=2), encoding='utf-8')
    (args.out / 'sources').mkdir()
    for p in Path(__file__).parent.glob('*.py'):
        shutil.copy2(p, args.out / 'sources' / p.name)
    stop = asyncio.Event()
    try:
        await engine.health()
        await engine.reset_cache()
        await engine.sample()
        poll = asyncio.create_task(engine.poll(stop))
        schedule = asyncio.create_task(controller.loop())
        harness = ReplayHarness(original_namespace, engine, controller, journal, requests, responses)
        await asyncio.gather(*(harness.root(t, i) for i, t in enumerate(selected)))
        controller.close()
        await schedule
        stop.set()
        await poll
        await engine.sample()
    finally:
        controller.close()
        stop.set()
        await engine.close()
        journal.close()
    # Reuse timing/accounting analysis, explicitly remove frozen-answer quality.
    summary = analyze(args.out, original_namespace.tasks.parent / 'answers.jsonl', original_namespace.tasks)
    summary['quality'] = None
    summary['quality_protocol'] = 'Not evaluated: causal replay uses frozen upstream outputs and forced decoding quotas.'
    summary.pop('exact_correct_root_latency_seconds', None)
    summary['trace_audit'] = audit(args.out)
    replay_requests = {r['call_id']: r for r in read(args.out / 'requests.jsonl')}
    quota_rows = read(args.out / 'responses.jsonl')
    summary['replay_accounting'] = {
        'source_calls': len(requests),
        'identical_input_prompts': sum(replay_requests.get(r['call_id'], {}).get('payload', {}).get('messages') == r['payload']['messages'] for r in requests),
        'quota_matches': sum(r.get('usage', {}).get('completion_tokens') == harness.frozen_responses[r['call_id']]['usage']['completion_tokens'] for r in quota_rows),
        'source_completion_tokens': sum(r['usage']['completion_tokens'] for r in responses),
        'live_completion_tokens': sum(r.get('usage', {}).get('completion_tokens', 0) for r in quota_rows),
        'full_source_trace': str(source),
        'interpretation': 'GPU executes all prefills and fixed decoding quotas. Frozen text is used only at causal boundaries; no quality or complete-harness speedup claim.',
    }
    summary['limitation'] = 'Fixed input and decoding quota mechanism isolation, not an autonomous end-to-end harness run.'
    (args.out / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    # Avoid exporting replay into the website table for live answer quality.
    destination = Path('results/replays') / args.out.name
    destination.mkdir(parents=True)
    for name in ['config.json', 'summary.json', 'audit.json', 'workload_fingerprints.json']:
        shutil.copy2(args.out / name, destination / name)
    record = (
        f"\n\n## {args.out.name} · 固定输入与生成配额的真实引擎因果回放\n\n"
        f"本轮以 {source.name} 的完整 trace 为输入，策略为 {args.policy}，模型调用上限 {args.cap}，"
        f"Session 窗口参数 {args.session_cap}。所有模型仍在双卡 Qwen3.8-27B 上实际推理，"
        f"前后依赖和真实工具重新执行；下游输入使用原记录的上游文本，逐请求强制相同输出 token 配额，"
        f"从而把采样产生的工作量变化与派发差异分开。实际完成 {summary['model_calls']} 次调用，"
        f"整任务平均耗时 {summary['root_latency_seconds']['mean']:.2f} 秒，"
        f"P95 为 {summary['root_latency_seconds']['p95']:.2f} 秒。"
        f"相同输入 {summary['replay_accounting']['identical_input_prompts']}/{len(requests)}，"
        f"配额匹配 {summary['replay_accounting']['quota_matches']}/{len(responses)}，"
        f"模型错误 {summary['engine_errors']}，任务错误 {summary['root_errors']}。"
        f"由于冻结了前序决策且强制解码，本轮不报告答案质量，不替代完整闭环实验，只作为系统机制归因；"
        f"原始请求、真实输出、冻结文本哈希、工具和指标保存在 {args.out}。\n")
    with Path('RESEARCH_LOG.md').open('a', encoding='utf-8') as f:
        f.write(record)
    (args.out / 'research_record.md').write_text(record, encoding='utf-8')
    (destination / 'research_record.md').write_text(record, encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--trace', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--policy', choices=['native', 'fixed', 'pressure', 'progress', 'backend_priority', 'session_window', 'return_priority'], default='native')
    ap.add_argument('--cap', type=int, default=12)
    ap.add_argument('--session-cap', type=int, default=12)
    asyncio.run(execute(ap.parse_args()))
