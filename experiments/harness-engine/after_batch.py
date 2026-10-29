"""Continue one predeclared batch only after an audited predecessor finishes."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--after', type=Path, required=True)
    ap.add_argument('--program', required=True)
    ap.add_argument('spec', type=Path)
    args = ap.parse_args()
    dependency = json.loads(args.after.read_text(encoding='utf-8'))
    spec = json.loads(args.spec.read_text(encoding='utf-8'))
    state_path = Path('state')/('continuation-'+spec['batch_id']+'.json')
    predecessor = Path('state')/('batch-'+dependency['batch_id']+'.json')
    next_state = Path('state')/('batch-'+spec['batch_id']+'.json')

    def save(**fields):
        state_path.write_text(json.dumps({'updated': time.time(), **fields}, indent=2), encoding='utf-8')

    save(status='waiting', dependency=str(predecessor))
    while True:
        if Path('state/STOP').exists():
            save(status='operator_stop'); return
        if predecessor.exists():
            previous = json.loads(predecessor.read_text())
            if previous['status'] == 'complete' and len(previous['completed']) == len(dependency['runs']):
                break
            if previous['status'] in ['failed', 'invalid_round', 'invalid_trace', 'operator_stop']:
                save(status='dependency_needs_inspection', dependency=previous['status']); return
        time.sleep(5)
    if next_state.exists():
        save(status='existing_batch_needs_inspection', path=str(next_state)); return
    save(status='running', program=args.program, specification=str(args.spec))
    with (Path('logs')/('batch-'+spec['batch_id']+'.log')).open('w') as log:
        result = subprocess.run([sys.executable, args.program, str(args.spec)],
                                stdout=log, stderr=subprocess.STDOUT)
    state = json.loads(next_state.read_text()) if next_state.exists() else {}
    valid = result.returncode == 0 and state.get('status') == 'complete' and len(state.get('completed', [])) == len(spec['runs'])
    save(status='planned_batch_finished' if valid else 'needs_inspection',
         returncode=result.returncode, completed_runs=len(state.get('completed', [])),
         next='Inspect actual evidence and choose the next iteration; the research objective remains active.')


if __name__ == '__main__':
    main()
