"""Real target/background research tasks from the already pinned public corpora."""
import argparse
import hashlib
import json
from pathlib import Path

from analyze import read


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, default=Path('datasets/shared-load'))
    args = ap.parse_args()
    groups = [('target', Path('datasets/mixed-research'), 'evaluation', 16),
              ('background', Path('datasets/longbench-v2'), 'calibration', 4)]
    tasks, answers, provenance = [], [], []
    for tenant, source, split, count in groups:
        selected = [t for t in read(source/'tasks.jsonl') if t['split'] == split][:count]
        if len(selected) != count:
            raise ValueError('Expected the complete predeclared source task list')
        gold = {t['task_id']: t for t in read(source/'answers.jsonl')}
        for task in selected:
            tasks.append({**task, 'source_split': task['split'], 'split': 'evaluation',
                          'tenant_id': tenant, 'dataset_id': task.get('dataset_id', 'longbench-v2')})
            answers.append({**gold[task['task_id']], 'tenant_id': tenant})
        provenance.append({'tenant_id': tenant, 'source_directory': str(source), 'source_split': split,
                           'selected_ids': [t['task_id'] for t in selected],
                           'manifest': json.loads((source/'manifest.json').read_text(encoding='utf-8')),
                           'source_tasks_sha256': hashlib.sha256((source/'tasks.jsonl').read_bytes()).hexdigest()})
    if len({t['task_id'] for t in tasks}) != len(tasks):
        raise ValueError('Target and background tasks must be disjoint')
    args.out.mkdir(parents=True, exist_ok=True)
    for name, rows in [('tasks.jsonl', tasks), ('answers.jsonl', answers)]:
        (args.out/name).write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in rows), encoding='utf-8')
    manifest = {'kind': 'independent-tenant-research', 'sources': provenance,
                'target_roots': 16, 'background_roots': 4,
                'notice': 'Background tasks use existing calibration questions as real work, not held-out quality evidence. '
                          'All original question/source texts are preserved; no padding or dummy GPU load.',
                'quality_protocol': 'Report each tenant and dataset separately; a mixed aggregate is not a uniform quality score.',
                'sha256': {n: hashlib.sha256((args.out/n).read_bytes()).hexdigest()
                           for n in ['tasks.jsonl', 'answers.jsonl']}}
    (args.out/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'out': str(args.out), 'target_roots': 16, 'background_roots': 4, 'total': len(tasks)}))


if __name__ == '__main__':
    main()
