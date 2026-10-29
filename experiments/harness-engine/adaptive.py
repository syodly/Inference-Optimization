"""Closed-loop optional review: observe model-dependent DAG choices before design.

Same pinned Qwen weights, two inference modes, no/always/uncertain review. Optional
work is explicit; quality/cost trade-offs are not called fixed-work speedups.
"""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import shutil
import time

from analyze import analyze, quality, read
from audit import audit
from engine import Engine, Journal
from export_run import export
from run import Harness, model_json
from scheduler import Controller


class ReviewChild(Harness):
    def child_session(self, root, branch_index):
        return root+'/review0'


class AdaptiveHarness(Harness):
    def __init__(self, args, engine, controller, journal):
        super().__init__(args, engine, controller, journal)
        self.review_count = 0
        self.decision_parse_errors = 0
        self.choices = []
        self.review = ReviewChild(argparse.Namespace(**{**vars(args), 'branches': 1}), engine, controller, journal)

    async def root(self, task, index):
        await asyncio.sleep(index*self.args.arrival_interval)
        root, parent = task['task_id'], task['task_id']+'/parent'
        start = time.monotonic()
        self.controller.remaining[root] = 3
        self.journal.write('events', event='root_submit', root_id=root, task_index=index,
                           question=task['question'], mandatory_children=3,
                           declared_optional_work='At most one all-source review Session and one parent continuation')
        self.journal.write('sessions', event='agent_execution_start', root_id=root, session_id=parent,
                           execution_id=parent+'/run0', role='parent')
        try:
            children = await asyncio.gather(*(self.branch(task, i, index) for i in range(3)), return_exceptions=True)
            failures = [repr(c) for c in children if isinstance(c, BaseException)]
            if failures:
                raise RuntimeError('Mandatory child failed: '+'; '.join(failures))
            self.journal.write('events', event='join_ready', root_id=root, children=3)
            system = ('You are the parent research agent. Combine all three mandatory child reports, '
                      'cross-link positive facts across shards, and give the best source-grounded answer. '
                      'A missing relation in one shard is not a global absence. '
                      'An optional independent reviewer can search the original sources again after your response. '
                      'Return ONLY a JSON object with these fields: answer (short string), citations (source ID list), '
                      'confidence (number from 0 to 1 reflecting support for your answer), needs_review (boolean), '
                      'review_query (a concrete question for the reviewer to resolve, or an empty string). '
                      'Set needs_review true when a bridge fact is missing, sources conflict, or answer support is weak. '
                      'If evidence is insufficient, use answer "unknown" and request review. No markdown or extra fields.')
            if task.get('answer_format'): system += ' '+task['answer_format']
            history = [{'role': 'system', 'content': system},
                       {'role': 'user', 'content': f"Question: {task['question']}\nChild reports:\n"+json.dumps(children, ensure_ascii=False)}]
            decision = await self.model(root, parent, 'decision', history, self.args.answer_tokens)
            decision_error = None
            try:
                preliminary = model_json(decision['text'])
                confidence = preliminary['confidence']
                if (not isinstance(preliminary.get('answer'), str) or not isinstance(confidence, (float, int))
                        or isinstance(confidence, bool) or not 0 <= confidence <= 1
                        or not isinstance(preliminary.get('needs_review'), bool)):
                    raise ValueError('Decision must contain answer, numeric confidence and boolean needs_review')
            except (ValueError, KeyError, TypeError) as exc:
                preliminary, confidence, decision_error = None, None, repr(exc)
                self.decision_parse_errors += 1
            uncertain = (decision_error is not None or preliminary['needs_review']
                         or confidence < self.args.review_threshold or preliminary['answer'].strip().lower() == 'unknown')
            do_review = self.args.review_mode == 'always' or (self.args.review_mode == 'uncertain' and uncertain)
            self.choices.append({'root_id': root, 'launch_review': do_review, 'uncertain': uncertain,
                                 'confidence': confidence, 'needs_review': preliminary.get('needs_review') if preliminary else None,
                                 'decision_parse_error': decision_error})
            self.journal.write('events', event='review_decision', root_id=root, mode=self.args.review_mode,
                               launch_review=do_review, uncertain=uncertain, confidence=confidence,
                               decision_parse_error=decision_error,
                               optional_model_calls=4 if do_review else 0,
                               optional_agent_executions=1 if do_review else 0,
                               observed_engine=dict(self.engine.latest))
            answer, final_error = decision, decision_error
            if do_review:
                self.review_count += 1
                self.controller.remaining[root] += 1
                focus = preliminary.get('review_query', '') if preliminary else ''
                candidate = preliminary.get('answer', 'unparsed initial response') if preliminary else 'unparsed initial response'
                review_task = {**task, 'question': task['question']+
                               '\nIndependent review: verify or correct the parent candidate answer: '+candidate+
                               '\nResolve this specific issue using the original sources: '+
                               (focus if isinstance(focus, str) and focus.strip() else 'Find the missing bridge or contradicting evidence for the answer.')}
                reviewed = await self.review.branch(review_task, 0, index)
                history.append(self.assistant(decision))
                history.append({'role': 'user', 'content': 'Independent reviewer report:\n'+reviewed['text']+
                                '\nUse the original reports and this review to resolve the original question. '
                                'Correct the candidate if the evidence warrants it. Return ONLY JSON with answer '
                                '(short string) and citations (source ID list). Do not request another review.'})
                answer = await self.model(root, parent, 'synthesis', history, self.args.answer_tokens)
                final_error = None
            try:
                parsed = model_json(answer['text'])
                if not isinstance(parsed, dict) or not isinstance(parsed.get('answer'), str):
                    raise ValueError('Final answer must be an object containing an answer string')
            except (ValueError, TypeError) as exc:
                parsed, final_error = None, repr(exc)
            self.journal.write('roots', root_id=root, task_index=index, duration=time.monotonic()-start,
                               output=answer['text'], parsed=parsed, parse_error=final_error,
                               children=children, error=None, preliminary=preliminary,
                               decision_parse_error=decision_error, review_launched=do_review,
                               confidence=confidence, optional_model_calls=4 if do_review else 0)
            self.journal.write('events', event='root_complete', root_id=root,
                               duration=time.monotonic()-start, valid_json=final_error is None)
        except Exception as exc:
            self.journal.write('roots', root_id=root, task_index=index, duration=time.monotonic()-start,
                               output=None, parsed=None, error=repr(exc))
            self.journal.write('events', event='root_failed', root_id=root, error=repr(exc))
        finally:
            self.journal.write('sessions', event='agent_execution_end', root_id=root, session_id=parent,
                               execution_id=parent+'/run0', role='parent')


async def execute(args):
    tasks = [t for t in read(args.tasks) if t['split'] == 'evaluation'][:args.count]
    if len(tasks) != args.count:
        raise ValueError('Use the complete predeclared diagnostic task set')
    journal = Journal(args.out)
    config = {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()}
    config.update(workflow='adaptive_verified', split='evaluation', trace_semantics_version=2,
                  task_ids=[t['task_id'] for t in tasks], started=time.time(),
                  expected_model_calls=args.count*10, expected_agent_executions=args.count*4,
                  dynamic_review={'mode': args.review_mode, 'threshold': args.review_threshold,
                                  'mandatory_calls_per_root': 10, 'optional_calls_per_review': 4,
                                  'optional_sessions_per_root': 1,
                                  'quality_scope': 'Existing public diagnostic examples, not a newly held-out generalization set.',
                                  'mode_scope': 'Same model weights with thinking on/off; not a model-size or fixed-work scheduling comparison.'},
                  data_manifest=json.loads((args.tasks.parent/'manifest.json').read_text(encoding='utf-8')),
                  tasks_sha256=hashlib.sha256(args.tasks.read_bytes()).hexdigest(),
                  source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')})
    for name in ['server', 'model_manifest', 'model_verification', 'source_revision', 'env']:
        path = Path('state')/(name+'.json')
        if path.exists(): config[name] = json.loads(path.read_text())
    (args.out/'config.json').write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
    (args.out/'sources').mkdir()
    for p in Path(__file__).parent.glob('*.py'): shutil.copy2(p, args.out/'sources'/p.name)
    engine = Engine(args.url, args.model, journal, args.thinking, 'qwen', 'low')
    controller = Controller('return_priority', args.cap, engine, journal, starvation_seconds=120)
    stop = asyncio.Event()
    harness = AdaptiveHarness(args, engine, controller, journal)
    try:
        await engine.health(); await engine.sample(); await engine.reset_cache()
        poll = asyncio.create_task(engine.poll(stop))
        schedule = asyncio.create_task(controller.loop())
        await asyncio.gather(*(harness.root(t, i) for i, t in enumerate(tasks)))
        controller.close(); await schedule; stop.set(); await poll; await engine.sample()
    finally:
        controller.close(); stop.set(); await engine.close(); journal.close()
    # Expected work is derived from declared online expansion choices, never from
    # the observed response count. An unfinished branch still fails the audit.
    config.update(expected_model_calls=args.count*10+harness.review_count*4,
                  expected_agent_executions=args.count*4+harness.review_count,
                  declared_online_choices=harness.choices)
    (args.out/'config.json').write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
    return config, harness.choices, harness.decision_parse_errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--tasks', type=Path, default=Path('datasets/mixed-research/tasks.jsonl'))
    ap.add_argument('--count', type=int, default=8)
    ap.add_argument('--review-mode', choices=['none', 'always', 'uncertain'], required=True)
    ap.add_argument('--review-threshold', type=float, default=.75)
    ap.add_argument('--thinking', action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument('--url', default='http://127.0.0.1:18081')
    ap.add_argument('--model', default='qwen27b')
    args = ap.parse_args()
    for k, v in dict(workflow='verified', branches=3, top_k=3, source_format='text', sampling_profile='qwen',
                     reasoning_effort='low', seed=1729, query_tokens=40, draft_tokens=4096,
                     evidence_tokens=4096, answer_tokens=4096, policy='return_priority', cap=24,
                     measure_prompts=False, tool_profile='natural', tool_delay=0, verify_delay=0,
                     verify_jitter=0, cohort=8, arrival_interval=0, second_wave=0).items():
        setattr(args, k, v)
    config, choices, parse_errors = asyncio.run(execute(args))
    summary = analyze(args.out, args.tasks.parent/'answers.jsonl', args.tasks)
    summary['trace_audit'] = audit(args.out)
    summary['dynamic_review'] = {'mode': args.review_mode, 'thinking': args.thinking,
                                'decision_parse_errors': parse_errors,
                                'reviewed_roots': sum(c['launch_review'] for c in choices),
                                'uncertain_roots': sum(c['uncertain'] for c in choices),
                                'choices': choices}
    gold = {row['task_id']: row for row in read(args.tasks.parent/'answers.jsonl')}
    comparisons = []
    for row in read(args.out/'scored.jsonl'):
        preliminary = row.get('preliminary') or {}
        initial_em, initial_f1 = quality(preliminary.get('answer', ''), row['gold_answer'], gold[row['root_id']].get('format'))
        if row.get('decision_parse_error'): initial_em = initial_f1 = 0.
        comparisons.append({'root_id': row['root_id'], 'review_launched': row.get('review_launched', False),
                            'confidence': row.get('confidence'), 'initial_em': initial_em, 'initial_f1': initial_f1,
                            'final_em': row['em'], 'final_f1': row['f1']})
    summary['dynamic_review']['offline_review_diagnostics'] = {
        'notice': 'Computed only after execution from hidden labels; not available to decisions or the controller.',
        'wrong_to_correct_roots': sum(r['review_launched'] and r['initial_em'] == 0 and r['final_em'] == 1 for r in comparisons),
        'correct_to_wrong_roots': sum(r['review_launched'] and r['initial_em'] == 1 and r['final_em'] == 0 for r in comparisons),
        'unreviewed_wrong_roots': sum(not r['review_launched'] and r['initial_em'] == 0 for r in comparisons),
        'high_confidence_wrong_initial_roots': sum(r['initial_em'] == 0 and r['confidence'] is not None and r['confidence'] >= args.review_threshold for r in comparisons),
        'records': comparisons}
    summary['limitation'] = 'Quality/work trade-off with a genuinely model-dependent optional branch. Not a fixed-work scheduling speedup or a model-size comparison.'
    (args.out/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    grouped = '；'.join(f"{k}准确率{v['em']:.3f}/F1 {v['f1']:.3f}，平均{v['root_latency_seconds']['mean']:.2f}秒"
                       for k, v in summary['quality_by_dataset'].items())
    record = (f"\n\n## {args.out.name} · 模型推理模式与可选复核图\n\n"
              f"本轮保持同一双卡Qwen3.8-27B权重、八道公开诊断题、三条必做调查分支和回流24调度，"
              f"思考模式{'开启' if args.thinking else '关闭'}，复核规则{args.review_mode}，阈值{args.review_threshold}。"
              '父Agent先给候选答案、来源、自报置信度与是否需要复核，再按预先声明规则决定是否创建一个可选独立子Session，'
              '由其重新检索全部原始来源并核对引句，父Session消费报告继续回答。'
              f"实际复核{sum(c['launch_review'] for c in choices)}/{args.count}题，调用{summary['model_calls']}/{summary['expected_model_calls']}，"
              f"{grouped}。根任务包含全部等待和可选工作，隐藏标签只做事后评分。"
              '本批先验证复核是否改善质量以及触发信号是否可信，不把少做工作、少生成token写成E1调度收益；'
              '两种设置仍是同一模型权重的推理模式，不冒充模型大小或参数能力对比。所有动态图选择、prompt、真实工具与失败完整保留。\n')
    (args.out/'research_record.md').write_text(record, encoding='utf-8')
    with Path('RESEARCH_LOG.md').open('a', encoding='utf-8') as f: f.write(record)
    export(args.out, Path(__file__).resolve().parent)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not (summary['trace_audit']['passed'] and summary['engine_errors'] == summary['root_errors'] == 0):
        raise RuntimeError('Inspect the complete failed dynamic round before further comparison')


if __name__ == '__main__':
    main()
