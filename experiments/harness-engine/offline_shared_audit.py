"""Exercise tenant separation using an actual already-completed v2 trace.

This checks accounting, not shared-load performance. It never contacts the engine
and never changes source artifacts or pretends that the original run had tenants.
"""
import argparse
import json
from pathlib import Path
import tempfile

from analyze import read
from shared import score_tenants


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('source', type=Path)
    ap.add_argument('--out', type=Path, default=Path('evidence/shared-offline-accounting.json'))
    args = ap.parse_args()
    cfg = json.loads((args.source/'config.json').read_text())
    if cfg.get('trace_semantics_version') != 2:
        raise ValueError('Use real trace with separately logged Agent executions and model calls')
    tasks = {t['task_id']: t for t in read(Path(cfg['tasks']))}
    answers = {t['task_id']: t for t in read(Path(cfg['tasks']).parent/'answers.jsonl')}
    # A real ledger belongs to its complete controller. Splitting its roots
    # would invalidate the recorded totals, unlike two actual controllers.
    has_ledger = cfg['policy'] in ['history_budget', 'history_pressure']
    assignments = {root: 'target' if has_ledger or i % 2 == 0 else 'background'
                   for i, root in enumerate(cfg['task_ids'])}
    with tempfile.TemporaryDirectory(prefix='shared-accounting-') as directory:
        tmp = Path(directory)
        corpus = tmp/'data'; corpus.mkdir()
        for name, source in [('tasks.jsonl', tasks), ('answers.jsonl', answers)]:
            (corpus/name).write_text(''.join(json.dumps({**source[k], 'tenant_id': assignments[k],
                                                        **({'dataset_id': source[k].get('dataset_id', Path(cfg['tasks']).parent.name)}
                                                           if name == 'tasks.jsonl' else {})}, ensure_ascii=False)+'\n'
                                            for k in cfg['task_ids']), encoding='utf-8')
        run = tmp/'run'; run.mkdir()
        local_cfg = {**cfg, 'tasks': str(corpus/'tasks.jsonl'),
                     'tenant_specs': {tenant: {'policy': cfg['policy'], 'measure_prompts': cfg['measure_prompts'],
                                              'session_cap': cfg['session_cap']}
                                      for tenant in sorted(set(assignments.values()))}}
        (run/'config.json').write_text(json.dumps(local_cfg), encoding='utf-8')
        for name in ['requests', 'responses', 'events', 'sessions', 'tools', 'roots', 'metrics']:
            # Engine records have a root ID; history-ledger records only a node ID.
            rows = []
            for record in read(args.source/(name+'.jsonl')):
                owner = assignments.get(record.get('root_id'))
                if owner is None and record.get('node_id'):
                    owner = assignments.get(record['node_id'].split('/')[0])
                rows.append({**record, **({'tenant_id': owner} if owner else {})})
            (run/(name+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in rows), encoding='utf-8')
        result = score_tenants(run, local_cfg)
        report = {'source': str(args.source), 'experiment': False,
                  'notice': ('Existing trace used only to validate offline filtering; no shared-load performance claim. '
                             'For a history budget, preserve its entire original controller ledger without repartitioning totals.'),
                  'trace_audit': result['trace_audit'], 'quality_by_tenant': result['quality_by_tenant']}
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'passed': report['trace_audit']['passed'],
                          'request_counts': {k: v['model_calls'] for k, v in report['quality_by_tenant'].items()}}, indent=2))
        if not report['trace_audit']['passed']:
            raise RuntimeError('Fix tenant filtering before interpreting any shared-load experiment')


if __name__ == '__main__':
    main()
