"""Mix existing public tasks without changing source texts, answers, or task semantics."""
import argparse
import hashlib
import json
from pathlib import Path


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, default=Path('datasets/mixed-research'))
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    inputs = [('longbench-v2', Path('datasets/longbench-v2')), ('hotpot', Path('datasets/hotpot'))]
    tasks, answers, provenance = [], [], []
    for dataset_id, directory in inputs:
        source_tasks = rows(directory / 'tasks.jsonl')
        source_gold = {r['task_id']: r for r in rows(directory / 'answers.jsonl')}
        selected = []
        for split, count in [('calibration', 4), ('evaluation', 8)]:
            chosen = [r for r in source_tasks if r['split'] == split][:count]
            if len(chosen) != count:
                raise ValueError('Insufficient pre-existing source tasks: ' + dataset_id + '/' + split)
            for r in chosen:
                tasks.append({**r, 'dataset_id': dataset_id})
                answers.append({**source_gold[r['task_id']], 'dataset_id': dataset_id})
                selected.append(r['task_id'])
        manifest = json.loads((directory / 'manifest.json').read_text())
        provenance.append({'dataset_id': dataset_id, 'source_directory': str(directory),
                           'source_manifest': manifest, 'selected_task_ids': selected,
                           'tasks_sha256': hashlib.sha256((directory / 'tasks.jsonl').read_bytes()).hexdigest()})
    # Alternate long and short roots; a count-only Session window sees both as one slot.
    tasks.sort(key=lambda r: (r['split'], provenance[0]['selected_task_ids'].index(r['task_id'])
                             if r['dataset_id'] == 'longbench-v2' else
                             provenance[1]['selected_task_ids'].index(r['task_id']),
                             0 if r['dataset_id'] == 'longbench-v2' else 1))
    for name, data in [('tasks.jsonl', tasks), ('answers.jsonl', answers)]:
        (args.out / name).write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in data), encoding='utf-8')
    manifest = {'kind': 'mixed-research', 'source': 'Existing fixed LongBench-v2 and HotpotQA manifests',
                'sources': provenance, 'ordering': 'Alternate long and short roots within each fixed split.',
                'calibration': 8, 'evaluation': 16,
                'quality_protocol': 'Report LongBench-v2 option accuracy and HotpotQA EM/F1 separately; a mixed aggregate is not a uniform quality measure.',
                'sha256': {name: hashlib.sha256((args.out/name).read_bytes()).hexdigest() for name in ['tasks.jsonl','answers.jsonl']}}
    (args.out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'out':str(args.out),'calibration':8,'evaluation':16,'roots':[t['dataset_id'] for t in tasks]}))


if __name__ == '__main__':main()
