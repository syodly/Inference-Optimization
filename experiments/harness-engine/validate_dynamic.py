"""Offline structural fixtures, never an inference, quality or performance result."""
import argparse
import asyncio
import json
from pathlib import Path
import tempfile

from adaptive import AdaptiveHarness
from analyze import read
from audit import audit
from engine import Journal
from scheduler import Controller


class FixtureEngine:
    def __init__(self, sample, journal, confidence, needs_review):
        self.sample, self.journal = sample, journal
        self.confidence, self.needs_review = confidence, needs_review
        self.latest = {'fixture_only': True}

    async def generate(self, *, call_id, root_id, node_id, stage, messages, **kwargs):
        self.journal.write('requests', call_id=call_id, root_id=root_id, node_id=node_id, stage=stage,
                           payload={'messages': messages}, fixture_only=True)
        self.journal.write('events', event='model_submit', call_id=call_id, root_id=root_id, node_id=node_id, stage=stage)
        if stage == 'decision':
            text = json.dumps({'answer': 'fixture-candidate', 'citations': [], 'confidence': self.confidence,
                               'needs_review': self.needs_review, 'review_query': 'Check the candidate against the original sources.'})
        elif stage == 'synthesis':
            text = json.dumps({'answer': 'fixture-final', 'citations': []})
        else:
            text = next(r['text'] for r in self.sample['streams']['responses'] if r['stage'] == stage)
        result = {'text': text, 'reasoning': '', 'usage': {}, 'fixture_only': True}
        self.journal.write('responses', call_id=call_id, root_id=root_id, node_id=node_id, stage=stage, **result)
        self.journal.write('events', event='model_complete', call_id=call_id, root_id=root_id, node_id=node_id, stage=stage, usage={})
        return result


async def validate(sample, mode, confidence, needs_review):
    with tempfile.TemporaryDirectory(prefix='dynamic-structure-only-') as directory:
        run = Path(directory)/'trace'
        journal = Journal(run)
        args = argparse.Namespace(workflow='verified', branches=3, top_k=3, source_format='text', thinking=True,
                                  sampling_profile='qwen', reasoning_effort='low', seed=1729,
                                  query_tokens=40, draft_tokens=4096, evidence_tokens=4096, answer_tokens=4096,
                                  policy='return_priority', cap=24, measure_prompts=False,
                                  tool_profile='natural', tool_delay=0, verify_delay=0, verify_jitter=0,
                                  cohort=1, arrival_interval=0, second_wave=0, review_mode=mode, review_threshold=.75)
        engine = FixtureEngine(sample, journal, confidence, needs_review)
        controller = Controller('return_priority', 24, engine, journal, starvation_seconds=120)
        harness = AdaptiveHarness(args, engine, controller, journal)
        schedule = asyncio.create_task(controller.loop())
        await harness.root(sample['task'], 0)
        controller.close(); await schedule; journal.close()
        expected_review = mode == 'always' or (mode == 'uncertain' and (needs_review or confidence < .75))
        config = {'workflow': 'adaptive_verified', 'policy': 'return_priority', 'cap': 24, 'branches': 3,
                  'count': 1, 'task_ids': [sample['task']['task_id']], 'trace_semantics_version': 2,
                  'expected_model_calls': 14 if expected_review else 10,
                  'expected_agent_executions': 5 if expected_review else 4,
                  'dynamic_review': {'mode': mode, 'threshold': .75}}
        (run/'config.json').write_text(json.dumps(config), encoding='utf-8')
        checked = audit(run)
        if not checked['passed']:
            raise RuntimeError(json.dumps(checked))
        requests = read(run/'requests.jsonl')
        (run/'requests.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in requests[1:]), encoding='utf-8')
        broken = audit(run)
        if broken['passed']:
            raise RuntimeError('The auditor accepted a deliberately missing mandatory call')
        return {'mode': mode, 'fixture_confidence': confidence, 'expected_review': expected_review,
                'calls': checked['request_count'], 'tools': checked['tool_count'],
                'agent_executions': checked['agent_execution_count'], 'audit_passed': True,
                'deliberately_missing_call_rejected': True}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sample', type=Path, default=Path('results/v020-delay-native-a/raw-example.json'))
    ap.add_argument('--out', type=Path, default=Path('evidence/dynamic-structure-validation.json'))
    args = ap.parse_args()
    sample = json.loads(args.sample.read_text(encoding='utf-8'))
    cases = [('none', .95, False), ('always', .95, False), ('uncertain', .5, True), ('uncertain', .95, False)]
    records = [asyncio.run(validate(sample, *case)) for case in cases]
    report = {'experiment': False, 'gpu_requests': 0,
              'scope': 'Synthetic parent decisions and recorded child text are structural fixtures only. Actual retrieval/source checks run; no quality or timing inference.',
              'records': records}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
