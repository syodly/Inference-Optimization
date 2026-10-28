"""Describe cold admissions across real tool gaps; no future information is given to policies."""
import argparse
import json
from pathlib import Path

from analyze import read, distribution


def audit(directory):
    warm, waiting_tools, ready_returns = set(), set(), set()
    cold_admissions, return_submissions = [], []
    warm_peak = 0
    for e in read(directory/'events.jsonl'):
        node, stage = e.get('node_id'), e.get('stage')
        kind = e['event']
        if kind == 'model_complete' and stage == 'draft':
            warm.add(node)
        elif kind == 'model_complete' and stage == 'evidence':
            warm.discard(node);ready_returns.discard(node)
        elif kind == 'tool_start' and e.get('tool_kind') == 'source_check':
            waiting_tools.add(node)
        elif kind == 'tool_complete' and e.get('tool_kind') == 'source_check':
            waiting_tools.discard(node)
        elif kind == 'model_ready' and stage == 'evidence':
            ready_returns.add(node)
        elif kind == 'frontend_release' and stage == 'draft':
            cold_admissions.append({'t':e['t'],'node_id':node,
                'warm_histories_not_finished':len(warm),'source_checks_inflight':len(waiting_tools),
                'ready_returns':len(ready_returns), 'model_inflight':e['inflight_calls']})
        elif kind == 'model_submit' and stage == 'evidence':
            ready_returns.discard(node)
            return_submissions.append({'t':e['t'],'node_id':node,'warm_histories_not_finished':len(warm)})
        warm_peak=max(warm_peak,len(warm))
    results = {
        'run_id':directory.name,'cold_draft_admissions':len(cold_admissions),
        'cold_admissions_with_unfinished_warm_history':sum(r['warm_histories_not_finished']>0 for r in cold_admissions),
        'cold_admissions_during_source_check':sum(r['source_checks_inflight']>0 for r in cold_admissions),
        'cold_admissions_during_tool_gap_with_no_ready_return':sum(r['source_checks_inflight']>0 and r['ready_returns']==0 for r in cold_admissions),
        'max_completed_draft_histories_awaiting_evidence_completion':warm_peak,
        'warm_histories_at_cold_admission':distribution([r['warm_histories_not_finished'] for r in cold_admissions]),
        'interpretation':'Descriptive causal trace audit. Tool gaps are observed after the run. Counts do not alone prove eviction or mechanism superiority.',
        'cold_admissions':cold_admissions,'return_submissions':return_submissions,
    }
    (directory/'lifecycle_audit.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    return results


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('runs',type=Path,nargs='+');args=ap.parse_args()
    for directory in args.runs:
        result=audit(directory); print(json.dumps({k:v for k,v in result.items() if k not in ['cold_admissions','return_submissions']}))
