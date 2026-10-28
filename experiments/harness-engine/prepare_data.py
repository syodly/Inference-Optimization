"""Create a fixed public QA evaluation manifest without exposing gold to policies."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
import shutil
import urllib.request

REPO = "hotpotqa/hotpot_qa"
REVISION = "1908d6afbbead072334abe2965f91bd2709910ab"
FILE = "distractor/validation-00000-of-00001.parquet"


def main() -> None:
    import pyarrow.parquet as pq

    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("datasets/hotpot"))
    ap.add_argument("--seed", type=int, default=1729)
    ap.add_argument("--calibration", type=int, default=8)
    ap.add_argument("--evaluation", type=int, default=24)
    ap.add_argument("--download-base", default="https://hf-mirror.com")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    raw = args.out / "validation.parquet"
    canonical_url = f"https://huggingface.co/datasets/{REPO}/resolve/{REVISION}/{FILE}"
    url = f"{args.download_base}/datasets/{REPO}/resolve/{REVISION}/{FILE}"
    if not raw.exists():
        print("DOWNLOAD", url, flush=True)
        temporary = raw.with_suffix('.parquet.part')
        with urllib.request.urlopen(url, timeout=45) as response, temporary.open('wb') as out:
            shutil.copyfileobj(response, out)
        pq.read_metadata(temporary)
        temporary.rename(raw)
    rows = pq.read_table(raw).to_pylist()
    rng = random.Random(args.seed)
    buckets: dict[str, list] = {}
    for row in rows:
        chars = sum(len(" ".join(s)) for s in row["context"]["sentences"])
        bucket = row["type"] + ("_long" if chars >= 16000 else "_normal")
        buckets.setdefault(bucket, []).append((row, chars))
    for values in buckets.values():
        rng.shuffle(values)
    selected = []
    names = sorted(buckets)
    while len(selected) < args.calibration + args.evaluation:
        for name in names:
            if buckets[name] and len(selected) < args.calibration + args.evaluation:
                row, chars = buckets[name].pop()
                selected.append((row, chars, name))
    tasks, answers = [], []
    for i, (row, chars, bucket) in enumerate(selected):
        docs = [{"doc_id": f"d{j}", "title": title, "text": " ".join(sentences)}
                for j, (title, sentences) in enumerate(zip(row["context"]["title"], row["context"]["sentences"]))]
        tasks.append({"task_id": row["id"], "split": "calibration" if i < args.calibration else "evaluation",
                      "question": row["question"], "type": row["type"], "level": row["level"],
                      "context_chars": chars, "bucket": bucket, "documents": docs})
        answers.append({"task_id": row["id"], "answer": row["answer"], "supporting_facts": row["supporting_facts"]})
    for name, values in [("tasks.jsonl", tasks), ("answers.jsonl", answers)]:
        (args.out / name).write_text("".join(json.dumps(v, ensure_ascii=False) + "\n" for v in values), encoding="utf-8")
    manifest = {"source": REPO, "revision": REVISION, "url": canonical_url,
                "download_url": url, "license": "cc-by-sa-4.0",
                "seed": args.seed, "source_rows": len(rows), "calibration": args.calibration,
                "evaluation": args.evaluation, "task_ids": [t["task_id"] for t in tasks],
                "sha256": {name: hashlib.sha256((args.out / name).read_bytes()).hexdigest()
                           for name in [raw.name, "tasks.jsonl", "answers.jsonl"]},
                "quality_protocol": "Gold answers/supporting facts only read by offline analysis, never by runtime/policy.",
                "workload_protocol": "Controlled multi-agent evidence-gathering application over public HotpotQA contexts; not official HotpotQA harness."}
    (args.out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"tasks": len(tasks), "context_chars": [t["context_chars"] for t in tasks], "output": str(args.out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
