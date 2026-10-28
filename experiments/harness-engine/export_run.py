"""Publish compact measured evidence, including one complete root's raw prompts."""
import json
from pathlib import Path
import shutil

from analyze import read


def rebuild_index(root: Path):
    index = []
    artifacts = ['config.json', 'scored.jsonl', 'raw-example.json', 'research_record.md',
                 'audit.json', 'history_audit.json', 'token_audit.json']
    for summary_path in sorted((root / 'results').glob('*/summary.json')):
        summary = json.loads(summary_path.read_text(encoding='utf-8'))
        index.append({'run_id': summary['run_id'], 'summary': summary,
                      'paths': {n: f"{summary['run_id']}/{n}" for n in artifacts
                                if (summary_path.parent / n).exists()}})
    (root / 'results/index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')
    return index


def export(run: Path, root: Path):
    config = json.loads((run / 'config.json').read_text())
    replay = bool(config.get('replay'))
    destination = root / 'results' / ('replays' if replay else '') / run.name
    destination.mkdir(parents=True, exist_ok=True)
    for name in ['config.json', 'summary.json', 'audit.json', 'scored.jsonl', 'research_record.md',
                 'workload_fingerprints.json', 'batch_entry.json', 'token_audit.json',
                 'history_audit.json', 'lifecycle_audit.json']:
        if (run / name).exists():
            shutil.copy2(run / name, destination / name)
    example_id = config['task_ids'][0]
    task_path = root / config['tasks']
    sample = {'run_id': run.name, 'root_id': example_id,
              'source': config.get('data_manifest') or json.loads((task_path.parent / 'manifest.json').read_text()),
              'task': next(r for r in read(task_path) if r['task_id'] == example_id),
              'notice': 'Real requests/responses. Gold scoring is offline; controller did not receive answers.',
              'remote_full_trace_directory': str(run),
              'streams': {}}
    if replay:
        sample['notice'] = ('Fixed-work diagnostic replay. These are actual GPU responses, while downstream '
                            'history and the recorded final root output are frozen from the source trace. '
                            'Do not interpret the root record as live answer quality.')
        sample['replay_protocol'] = config['replay']
    for stream in ['requests', 'responses', 'sessions', 'tools', 'roots', 'events', 'scored',
                   *(['replay_frozen_outputs'] if replay else [])]:
        if replay and stream == 'scored':
            continue
        sample['streams'][stream] = [r for r in read(run / (stream + '.jsonl')) if r.get('root_id') == example_id]
    (destination / 'raw-example.json').write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding='utf-8')
    if replay:
        return destination
    rebuild_index(root)
    return destination


if __name__ == '__main__':
    import sys
    root = Path(__file__).resolve().parent
    for directory in sys.argv[1:]:
        print(export(Path(directory).resolve(), root))
