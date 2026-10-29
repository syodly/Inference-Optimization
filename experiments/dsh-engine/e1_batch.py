"""Run exactly the explicitly requested three small DSH comparisons."""
import json
from pathlib import Path
import subprocess
import time

ROOT = Path('/home/Liangyijia_Hu/dsh-lab')
PYTHON = '/home/Liangyijia_Hu/harness-engine/.venv-engine/bin/python'


def main():
    plan = json.loads((ROOT/'e1-small-plan.json').read_text())
    state = {'batch_id': plan['batch_id'], 'status': 'running', 'started': time.time(), 'completed': []}
    path = ROOT/'state/e1-small-batch.json'
    for run in plan['runs']:
        state['current'] = run['run_id']
        path.write_text(json.dumps(state, indent=2)+'\n')
        command = [PYTHON, str(ROOT/'e1_run.py'), '--run-id', run['run_id'], '--policy', run['policy'],
                   '--cap', str(run['cap']), '--count', str(plan['tasks'])]
        print('RUN', run['run_id'], flush=True)
        subprocess.run(command, cwd=ROOT, check=True)
        subprocess.run([PYTHON, str(ROOT/'e1_analyze.py'), run['run_id']], cwd=ROOT, check=True)
        state['completed'].append(run['run_id'])
        path.write_text(json.dumps(state, indent=2)+'\n')
    state.update(status='completed', current=None, finished=time.time())
    path.write_text(json.dumps(state, indent=2)+'\n')
    print('SMALL_BATCH_COMPLETE', flush=True)


if __name__ == '__main__':
    main()
