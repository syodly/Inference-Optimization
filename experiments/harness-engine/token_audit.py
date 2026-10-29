"""Audit actual chat-template token prefixes; does not infer cache eviction from misses."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path

import httpx

from analyze import read, distribution
from engine import tokenize_payload


async def audit_tokens(directory, url, local_tokenizer=None):
    requests = read(directory / 'requests.jsonl')
    responses = {r['call_id']: r for r in read(directory / 'responses.jsonl')}
    gate = asyncio.Semaphore(3)
    async with httpx.AsyncClient(timeout=120) as client:
        async def tokenize(row):
            p = row['payload']
            payload = tokenize_payload(p)
            async with gate:
                result = await client.post(url.rstrip('/') + '/tokenize', json=payload)
                result.raise_for_status()
                data = result.json()
            return row['call_id'], data['tokens']
        if local_tokenizer is None:
            token_map = dict(await asyncio.gather(*(tokenize(r) for r in requests)))
        else:
            from transformers import AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained(str(local_tokenizer), local_files_only=True)
            token_map = {}
            for row in requests:
                payload = tokenize_payload(row['payload'])
                token_map[row['call_id']] = tokenizer.apply_chat_template(
                    payload['messages'], tokenize=True, add_generation_prompt=True,
                    **payload.get('chat_template_kwargs', {}))
    previous = {}
    records = []
    for r in requests:
        ids = token_map[r['call_id']]
        response = responses[r['call_id']]
        usage = response.get('usage', {})
        cached = (usage.get('prompt_tokens_details') or {}).get('cached_tokens')
        prior = previous.get(r['node_id'])
        common = None
        if prior is not None:
            a = token_map[prior['call_id']]
            common = next((i for i, (x, y) in enumerate(zip(a, ids)) if x != y), min(len(a), len(ids)))
        records.append({
            'call_id': r['call_id'], 'node_id': r['node_id'], 'stage': r['stage'],
            'tokenized_prompt_tokens': len(ids), 'reported_prompt_tokens': usage.get('prompt_tokens'),
            'token_count_matches_usage': len(ids) == usage.get('prompt_tokens'),
            'token_ids_sha256': hashlib.sha256(json.dumps(ids).encode()).hexdigest(),
            'previous_call_id': prior['call_id'] if prior else None,
            'common_input_prefix_tokens': common, 'cached_tokens': cached,
            'uncached_common_input_tokens': max(0, common - cached) if common is not None and cached is not None else None,
        })
        previous[r['node_id']] = r
    summary = {
        'run_id': directory.name, 'calls': len(records),
        'tokenization_backend': 'local pinned model tokenizer' if local_tokenizer else 'actual engine /tokenize',
        'local_tokenizer': str(local_tokenizer) if local_tokenizer else None,
        'all_token_counts_match_usage': all(r['token_count_matches_usage'] for r in records),
        'stage': {s: {
            'calls': sum(r['stage'] == s for r in records),
            'common_input_prefix_tokens': distribution([r['common_input_prefix_tokens'] for r in records if r['stage'] == s]),
            'uncached_common_input_tokens': distribution([r['uncached_common_input_tokens'] for r in records if r['stage'] == s]),
        } for s in sorted({r['stage'] for r in records})},
        'interpretation': 'A shared input prefix is an opportunity, not proof that this hybrid engine saved a reusable state checkpoint. Misses can reflect checkpoint alignment, history rendering, or eviction; investigate separately.',
        'records': records,
    }
    (directory / 'token_audit.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in summary.items() if k != 'records'}, indent=2))
    return summary


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('run', type=Path)
    ap.add_argument('--url', default='http://127.0.0.1:18081')
    ap.add_argument('--local-tokenizer', type=Path,
                    help='Use the pinned model tokenizer on CPU without requests to an active timed engine')
    args = ap.parse_args()
    asyncio.run(audit_tokens(args.run, args.url, args.local_tokenizer))
