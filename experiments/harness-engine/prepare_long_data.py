"""Versioned real long-document research tasks; preserve the complete source text."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random
import shutil
import urllib.request

REPO = 'zai-org/LongBench-v2'
REVISION = '2b48e494f2c7a2f0af81aae178e05c7e1dde0fe9'


def main():
    from transformers import AutoTokenizer
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, default=Path('datasets/longbench-v2'))
    ap.add_argument('--model', type=Path, required=True)
    ap.add_argument('--seed', type=int, default=2718)
    ap.add_argument('--calibration', type=int, default=4)
    ap.add_argument('--evaluation', type=int, default=12)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    raw = args.out / 'data.json'
    url = f'https://hf-mirror.com/datasets/{REPO}/resolve/{REVISION}/data.json'
    if not raw.exists():
        temporary = raw.with_suffix('.json.part')
        with urllib.request.urlopen(url, timeout=60) as response, temporary.open('wb') as output:
            shutil.copyfileobj(response, output)
        json.loads(temporary.read_text())
        temporary.rename(raw)
    rows = json.loads(raw.read_text())
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=False)
    buckets = defaultdict(list)
    candidates = []
    for row in rows:
        if row['domain'] != 'Multi-Document QA' or not 45000 <= len(row['context']) <= 180000:
            continue
        text = row['context']
        total = len(tokenizer.encode(text, add_special_tokens=False))
        if not 18000 <= total <= 36000:
            continue
        boundaries = [0]
        for i in range(1, 9):
            target = len(text) * i // 9
            nearby = text.rfind('\n', max(boundaries[-1] + 1, target - 300), target + 300)
            boundaries.append(nearby + 1 if nearby >= 0 else target)
        boundaries.append(len(text))
        docs = [{'doc_id': f'd{i}', 'title': f'Original source segment {i + 1}/9',
                 'text': text[a:b], 'char_start': a, 'char_end': b}
                for i, (a, b) in enumerate(zip(boundaries, boundaries[1:]))]
        assert ''.join(d['text'] for d in docs) == text
        shard_tokens = [len(tokenizer.encode(''.join(d['text'] for d in docs[b::3]), add_special_tokens=False))
                        for b in range(3)]
        if max(shard_tokens) > 14000:
            continue
        candidate = {'row': row, 'documents': docs, 'context_tokens': total,
                     'shard_tokens': shard_tokens}
        buckets[row['sub_domain']].append(candidate)
        candidates.append({'id': row['_id'], 'subdomain': row['sub_domain'], 'tokens': total,
                           'shard_tokens': shard_tokens})
    rng = random.Random(args.seed)
    for bucket in buckets.values():
        rng.shuffle(bucket)
    selected = []
    wanted = args.calibration + args.evaluation
    if sum(map(len, buckets.values())) < wanted:
        raise ValueError(f'Only {sum(map(len, buckets.values()))} eligible sources for {wanted} requested; inspect rather than trim text')
    while len(selected) < wanted:
        for name in sorted(buckets):
            if buckets[name] and len(selected) < wanted:
                selected.append(buckets[name].pop())
    tasks, answers = [], []
    for i, selected_row in enumerate(selected):
        row = selected_row['row']
        question = row['question'] + '\n\n' + '\n'.join(f'{c}. {row["choice_" + c]}' for c in 'ABCD')
        tasks.append({'task_id': row['_id'], 'split': 'calibration' if i < args.calibration else 'evaluation',
                      'question': question, 'type': row['sub_domain'], 'level': row['difficulty'],
                      'context_chars': len(row['context']), 'context_tokens': selected_row['context_tokens'],
                      'shard_tokens': selected_row['shard_tokens'], 'documents': selected_row['documents'],
                      'answer_format': 'The answer string must contain ONLY one option label: A, B, C, or D.',
                      'source_context_sha256': hashlib.sha256(row['context'].encode()).hexdigest()})
        answers.append({'task_id': row['_id'], 'answer': row['answer'], 'format': 'multiple_choice',
                        'supporting_facts': {'title': [], 'sent_id': []}})
    for name, data in [('tasks.jsonl', tasks), ('answers.jsonl', answers)]:
        (args.out / name).write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in data), encoding='utf-8')
    manifest = {'source': REPO, 'revision': REVISION, 'license': 'apache-2.0', 'download_url': url,
                'canonical_url': url.replace('hf-mirror.com', 'huggingface.co'), 'seed': args.seed,
                'source_rows': len(rows), 'domain': 'Multi-Document QA', 'candidates': candidates,
                'selection': '18000–36000 actual Qwen tokens, full original context, no truncation or padding; max shard 14000 tokens',
                'chunking': 'Nine contiguous character segments, paragraph boundaries preferred; concatenate exactly equals original context; three strided shards',
                'task_ids': [r['task_id'] for r in tasks], 'calibration': args.calibration, 'evaluation': args.evaluation,
                'sha256': {n: hashlib.sha256((args.out / n).read_bytes()).hexdigest()
                           for n in ['data.json', 'tasks.jsonl', 'answers.jsonl']},
                'quality_protocol': 'Strict option-label accuracy; hidden labels used only by offline analysis.',
                'subdomains': dict(Counter(r['type'] for r in tasks))}
    (args.out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'tasks': len(tasks), 'context_tokens': [r['context_tokens'] for r in tasks],
                      'subdomains': manifest['subdomains']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
