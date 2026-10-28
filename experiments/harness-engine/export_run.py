"""Publish compact measured evidence, including one complete root's raw prompts."""
import json
from pathlib import Path
import shutil

from analyze import read


def export(run: Path, root: Path):
    destination = root / 'results' / run.name
    destination.mkdir(parents=True, exist_ok=True)
    for name in ['config.json', 'summary.json', 'audit.json', 'scored.jsonl', 'research_record.md',
                 'workload_fingerprints.json', 'batch_entry.json']:
        if (run / name).exists():
            shutil.copy2(run / name, destination / name)
    config = json.loads((run / 'config.json').read_text())
    example_id = config['task_ids'][0]
    sample = {'run_id': run.name, 'root_id': example_id,
              'source': json.loads((root / 'datasets/hotpot/manifest.json').read_text()),
              'task': next(r for r in read(root / 'datasets/hotpot/tasks.jsonl') if r['task_id'] == example_id),
              'notice': 'Real requests/responses. Gold scoring is offline; controller did not receive answers.',
              'remote_full_trace_directory': str(run),
              'streams': {}}
    for stream in ['requests', 'responses', 'sessions', 'tools', 'roots', 'events', 'scored']:
        sample['streams'][stream] = [r for r in read(run / (stream + '.jsonl')) if r.get('root_id') == example_id]
    (destination / 'raw-example.json').write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding='utf-8')
    index = []
    for summary_path in sorted((root / 'results').glob('*/summary.json')):
        summary = json.loads(summary_path.read_text())
        index.append({'run_id': summary['run_id'], 'summary': summary,
                      'paths': {n: f"{summary['run_id']}/{n}" for n in
                                ['config.json', 'scored.jsonl', 'raw-example.json', 'research_record.md', 'audit.json']}})
    (root / 'results/index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')
    return destination


if __name__ == '__main__':
    import sys
    root = Path(__file__).resolve().parent
    for directory in sys.argv[1:]:
        print(export(Path(directory).resolve(), root))
