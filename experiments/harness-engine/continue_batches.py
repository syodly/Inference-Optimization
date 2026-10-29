"""Finish v017 with stable code, deploy the staged revision, then run short rounds.

Only explicitly listed project files and experiment specifications are touched.
This helper never restarts failed rounds or runs two inference batches together.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parent
STATE = ROOT / 'state/continuation-v020-v021.json'
FILES = ['run.py', 'replay.py', 'scheduler.py', 'analyze.py', 'audit.py', 'batch.py',
         'export_run.py', 'history_audit.py', 'compare_mixed.py', 'compare_replays.py']


def stopped():
    return (ROOT / 'state/STOP').exists()


def completed(specification):
    spec = json.loads((ROOT / specification).read_text())
    path = ROOT / 'state' / ('batch-'+spec['batch_id']+'.json')
    if not path.exists():
        return False
    state = json.loads(path.read_text())
    if state['status'] in ['failed', 'invalid_round', 'invalid_trace']:
        raise RuntimeError('Retain failed batch for inspection: '+str(path))
    return state['status'] == 'complete' and len(state['completed']) == len(spec['runs'])


def save(**fields):
    STATE.write_text(json.dumps({'updated': time.time(), **fields}, indent=2), encoding='utf-8')


def main():
    save(status='waiting', dependency='configs/mixed-history-v017.json')
    while not completed('configs/mixed-history-v017.json'):
        if stopped():
            save(status='operator_stop'); return
        time.sleep(5)
    if stopped():
        save(status='operator_stop'); return
    staged = ROOT / 'stage-v2'
    hashes = {name: hashlib.sha256((staged / name).read_bytes()).hexdigest() for name in FILES}
    for name in FILES:
        shutil.copy2(staged / name, ROOT / name)
    save(status='deployed', code_sha256=hashes)
    for program, specification in [('batch.py', 'configs/tool-return-v020.json'),
                                   ('replay_batch.py', 'configs/mixed-replay-v021.json')]:
        if stopped():
            save(status='operator_stop'); return
        spec = json.loads((ROOT / specification).read_text())
        if completed(specification):
            continue
        state_path = ROOT / 'state' / ('batch-'+spec['batch_id']+'.json')
        if state_path.exists():
            raise RuntimeError('Existing unfinished batch; inspect before continuing: '+str(state_path))
        save(status='running', specification=specification, code_sha256=hashes)
        with (ROOT / 'logs' / ('batch-'+spec['batch_id']+'.log')).open('w') as log:
            result = subprocess.run([sys.executable, program, specification], cwd=ROOT,
                                    stdout=log, stderr=subprocess.STDOUT)
        if stopped():
            save(status='operator_stop'); return
        if result.returncode or not completed(specification):
            save(status='needs_inspection', specification=specification, returncode=result.returncode)
            raise RuntimeError('Batch was not fully validated: '+specification)
    save(status='planned_batches_finished', code_sha256=hashes,
         next='Inspect comparisons and choose the next research iteration; the research goal remains active.')


if __name__ == '__main__':
    main()
