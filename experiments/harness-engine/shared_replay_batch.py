"""Execute predeclared shared-engine causal replays one round at a time."""
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
    state_path = Path('state')/('batch-'+spec['batch_id']+'.json')
    completed = []
    for entry in spec['runs']:
        if Path('state/STOP').exists():
            state_path.write_text(json.dumps({'status': 'operator_stop', 'completed': completed})); return
        run_id = entry['run_id']
        state = {'batch_id': spec['batch_id'], 'status': 'running', 'current': run_id,
                 'completed': completed, 'started': time.time()}
        state_path.write_text(json.dumps(state, indent=2))
        command = [sys.executable, 'shared_replay.py', '--trace', spec['trace'], '--out', 'runs/'+run_id, *entry['args']]
        with (Path('logs')/(run_id+'.log')).open('w') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            state.update(status='failed', returncode=result.returncode, finished=time.time())
            state_path.write_text(json.dumps(state, indent=2)); raise RuntimeError('Inspect '+run_id)
        summary = json.loads((Path('runs')/run_id/'summary.json').read_text())
        completed.append({'run_id': run_id, 'summary': summary, 'finished': time.time()})
        state.update(status='between_rounds', completed=completed, finished=time.time())
        state_path.write_text(json.dumps(state, indent=2))
        print('DONE', run_id, {k: v['root_latency_seconds']['mean'] for k, v in summary['latency_by_tenant'].items()}, flush=True)
    state_path.write_text(json.dumps({'batch_id': spec['batch_id'], 'status': 'complete',
                                     'completed': completed, 'finished': time.time()}, indent=2))


if __name__ == '__main__':
    main()
