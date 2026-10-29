"""Validate reconstruction of every saved input using real tools and frozen outputs.

No GPU requests; timing and quality are not experimental results. Only offline
arrival sleeps are skipped; original task indices still seed the same tools.
"""
import argparse
import asyncio
import json
from pathlib import Path
import tempfile

from analyze import read
from engine import Journal
from run import Harness
from scheduler import Controller
from shared import TenantJournal


class InputCheckHarness(Harness):
    def __init__(self, settings, controller, journal, requests, responses):
        super().__init__(settings, None, controller, journal)
        self.requests = {(r['root_id'], r['node_id'], r['stage']): r for r in requests}
        self.responses = {r['call_id']: r for r in responses}
        self.checked = set()

    async def model(self, root, session, stage, messages, budget):
        record = self.requests[(root, session, stage)]
        if record['payload']['messages'] != messages:
            raise ValueError('Reconstructed prompt differs: '+record['call_id'])
        self.checked.add(record['call_id'])
        return self.responses[record['call_id']]


async def validate(source, destination):
    cfg = json.loads((source/'config.json').read_text())
    tasks = {t['task_id']: t for t in read(Path(cfg['tasks']))}
    requests, responses = [read(source/(name+'.jsonl')) for name in ['requests', 'responses']]
    with tempfile.TemporaryDirectory(prefix='offline-shared-replay-') as directory:
        trace = Path(directory)/'trace'
        journal = Journal(trace)
        loops, controllers, harnesses, jobs = [], [], [], []
        for tenant, settings in cfg['tenant_specs'].items():
            args = argparse.Namespace(**{**settings, 'policy': 'native', 'measure_prompts': False,
                                         'arrival_interval': 0, 'second_wave': 0})
            tenant_journal = TenantJournal(journal, tenant)
            controller = Controller('native', 128, None, tenant_journal)
            controllers.append(controller); loops.append(asyncio.create_task(controller.loop()))
            harness = InputCheckHarness(args, controller, tenant_journal, requests, responses)
            harnesses.append(harness)
            own = [tasks[k] for k in cfg['task_ids'] if tasks[k]['tenant_id'] == tenant]
            jobs.extend(harness.root(task, i) for i, task in enumerate(own))
        await asyncio.gather(*jobs)
        for c in controllers: c.close()
        await asyncio.gather(*loops); journal.close()
        roots = read(trace/'roots.jsonl')
        checked = set().union(*(h.checked for h in harnesses))
        report = {'source': str(source), 'experiment': False, 'expected_calls': len(requests),
                  'identical_reconstructed_inputs': len(checked),
                  'completed_roots': len(roots), 'root_errors': [r for r in roots if r.get('error')],
                  'scope': 'Offline full-DAG reconstruction check; tools real, outputs frozen, arrival sleeps skipped. No GPU or performance claim.'}
        report['passed'] = len(checked) == len(requests) and len(roots) == len(cfg['task_ids']) and not report['root_errors']
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if not report['passed']: raise RuntimeError('Repair prompt reconstruction before a timed replay')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('source', type=Path)
    ap.add_argument('--out', type=Path, default=Path('evidence/shared-replay-input-validation.json'))
    args = ap.parse_args()
    asyncio.run(validate(args.source, args.out))
