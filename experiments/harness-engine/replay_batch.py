"""Sequential replay rounds, with a durable state file and short individual runs."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spec', type=Path)
    args = ap.parse_args()
    spec = json.loads(args.spec.read_text(encoding='utf-8'))
    state_path = Path('state') / ('batch-' + spec['batch_id'] + '.json')
    completed = []
    for entry in spec['runs']:
        if Path('state/STOP').exists():
            break
        run_id = entry['run_id']
        state = {'batch_id': spec['batch_id'], 'status': 'running', 'current': run_id,
                 'completed': completed, 'started': time.time()}
        state_path.write_text(json.dumps(state, indent=2))
        command = [sys.executable, 'replay.py', '--trace', spec['trace'], '--out', 'runs/' + run_id, *entry['args']]
        print('START', run_id, flush=True)
        with (Path('logs') / (run_id + '.log')).open('w') as log:
            p = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
        if p.returncode:
            state.update(status='failed', returncode=p.returncode)
            state_path.write_text(json.dumps(state, indent=2))
            raise RuntimeError(run_id + ' process failed; inspect log')
        summary = json.loads((Path('runs') / run_id / 'summary.json').read_text())
        completed.append({'run_id': run_id, 'summary': summary, 'finished': time.time()})
        valid = (summary['engine_errors'] == summary['root_errors'] == 0 and summary['trace_audit']['passed']
                 and summary['replay_accounting']['identical_input_prompts'] == summary['expected_model_calls']
                 and summary['replay_accounting']['quota_matches'] == summary['expected_model_calls'])
        state.update(status='between_rounds' if valid else 'invalid_round', completed=completed, finished=time.time())
        state_path.write_text(json.dumps(state, indent=2))
        print('DONE', run_id, summary['root_latency_seconds'], 'valid', valid, flush=True)
        if not valid:
            raise RuntimeError('Incomplete replay accounting; retain trace and repair before further comparisons')
    state_path.write_text(json.dumps({'batch_id': spec['batch_id'], 'status': 'complete',
                                     'completed': completed, 'finished': time.time()}, indent=2))


if __name__ == '__main__':
    main()
