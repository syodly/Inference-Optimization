"""Start predeclared shared-engine rounds after the current continuation ends.

No inference overlaps the existing v020/v021 series. Failed or incomplete
dependencies are left for inspection; this does not relaunch previous work.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parent
STATE = ROOT/'state/continuation-v024.json'


def save(**fields):
    STATE.write_text(json.dumps({'updated': time.time(), **fields}, indent=2), encoding='utf-8')


def main():
    save(status='waiting', dependency='state/continuation-v020-v021.json')
    while True:
        if (ROOT/'state/STOP').exists():
            save(status='operator_stop'); return
        p = ROOT/'state/continuation-v020-v021.json'
        if p.exists():
            dependency = json.loads(p.read_text())
            if dependency['status'] == 'planned_batches_finished':
                break
            if dependency['status'] in ['needs_inspection', 'operator_stop']:
                save(status='dependency_needs_inspection', dependency=dependency)
                return
        for name in ['tool-return-v020', 'mixed-replay-v021']:
            p = ROOT/'state'/('batch-'+name+'.json')
            if p.exists() and json.loads(p.read_text())['status'] in ['failed', 'invalid_round', 'invalid_trace']:
                save(status='dependency_needs_inspection', dependency=str(p)); return
        time.sleep(5)
    specification = ROOT/'configs/shared-load-v024.json'
    spec = json.loads(specification.read_text())
    previous = ROOT/'state'/('batch-'+spec['batch_id']+'.json')
    if previous.exists():
        save(status='existing_batch_needs_inspection', path=str(previous)); return
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.glob('*.py')}
    save(status='running', specification=str(specification), code_sha256=hashes)
    with (ROOT/'logs/batch-shared-load-v024.log').open('w') as log:
        result = subprocess.run([sys.executable, 'shared_batch.py', str(specification)],
                                cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    state = json.loads(previous.read_text()) if previous.exists() else {}
    valid = result.returncode == 0 and state.get('status') == 'complete' and len(state.get('completed', [])) == len(spec['runs'])
    save(status='planned_batch_finished' if valid else 'needs_inspection',
         returncode=result.returncode, completed_runs=len(state.get('completed', [])),
         next='Inspect both tenants and fixed-work results before selecting another mechanism; research remains active.')


if __name__ == '__main__':
    main()
