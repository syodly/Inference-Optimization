"""Audit normalized, measured Harness JSONL; this is not a DSH collector."""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

STATES = {"materializing", "running", "wait_tool", "wait_children", "parked_inbox", "stopping", "other"}


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def analyze(events):
    runs = defaultdict(list)
    for event in events:
        if not isinstance(event, dict) or not all(k in event for k in ("run_id", "policy", "event", "ts_ms")):
            raise ValueError("Each event needs run_id, policy, event, ts_ms")
        if not number(event["ts_ms"]):
            raise ValueError("ts_ms must be a finite number")
        runs[event["run_id"]].append(event)
    reports = []
    for run_id, rows in runs.items():
        rows.sort(key=lambda x: x["ts_ms"])
        policies = {e["policy"] for e in rows}
        if len(policies) != 1:
            raise ValueError(f"{run_id}: a run cannot mix policies")
        tasks, requests, accepted, consumed, slots = {}, {}, {}, {}, {}
        slot_ms, reads, modes = Counter(), Counter(), Counter()
        rejected = Counter()
        live_slots = peak_slots = 0
        for event in rows:
            kind, now = event["event"], event["ts_ms"]
            if kind == "delegate":
                modes[event["mode"]] += 1
            elif kind == "task_start":
                task = event["task_id"]
                if task in tasks:
                    raise ValueError(f"{run_id}: duplicate task_start {task}")
                tasks[task] = {"start": now, "finish": None, "success": None}
            elif kind == "task_end":
                task = event["task_id"]
                if task not in tasks or tasks[task]["finish"] is not None:
                    raise ValueError(f"{run_id}: unmatched task_end {task}")
                if event.get("success") is not None and not isinstance(event["success"], bool):
                    raise ValueError("success must be bool or null")
                tasks[task].update(finish=now, success=event.get("success"))
            elif kind == "llm_end":
                request = event["request_id"]
                if request in requests:
                    raise ValueError(f"{run_id}: duplicate request {request}")
                if event["actor"] not in {"parent", "child"}:
                    raise ValueError("actor must be parent or child")
                for key in ("input_tokens", "output_tokens", "cached_tokens"):
                    val = event.get(key)
                    if val is not None and (not number(val) or val < 0 or val != int(val)):
                        raise ValueError(f"invalid measured usage {key}")
                if event.get("cached_tokens") is not None and event.get("input_tokens") is not None:
                    if event["cached_tokens"] > event["input_tokens"]:
                        raise ValueError("cached_tokens exceeds input_tokens")
                requests[request] = event
            elif kind == "artifact_read":
                reads[(event["artifact_id"], event["version"])] += 1
            elif kind == "message_accepted":
                message = event["message_id"]
                if message in accepted:
                    raise ValueError(f"{run_id}: duplicate accepted message {message}")
                accepted[message] = now
            elif kind == "message_consumed":
                message = event["message_id"]
                if message in consumed or message not in accepted:
                    raise ValueError(f"{run_id}: unmatched/repeated first consumption {message}")
                consumed[message] = {"wait_ms": now-accepted[message], "request_id": event["request_id"]}
            elif kind == "activation_reserved":
                identity = event["activation_id"]
                if identity in slots:
                    raise ValueError(f"{run_id}: reused activation identity {identity}")
                slots[identity] = {"at": now, "state": "materializing", "released": False}
                live_slots += 1
                peak_slots = max(peak_slots, live_slots)
            elif kind in {"activation_state", "activation_released"}:
                identity = event["activation_id"]
                if identity not in slots or slots[identity]["released"]:
                    raise ValueError(f"{run_id}: unmatched slot event {identity}")
                slot = slots[identity]
                slot_ms[slot["state"]] += now-slot["at"]
                slot["at"] = now
                if kind == "activation_released":
                    slot["released"] = True
                    live_slots -= 1
                else:
                    if event["state"] not in STATES:
                        raise ValueError("unknown activation state")
                    slot["state"] = event["state"]
            elif kind == "activation_rejected":
                rejected[event["reason"]] += 1
        cutoff = rows[-1]["ts_ms"]
        for slot in slots.values():
            if not slot["released"]:
                slot_ms[slot["state"]] += cutoff-slot["at"]
        usage, coverage = {}, {}
        for key in ("input_tokens", "output_tokens", "cached_tokens"):
            values = [event[key] for event in requests.values() if event.get(key) is not None]
            coverage[key] = {"reported_requests": len(values), "total_requests": len(requests)}
            usage[key] = sum(values) if requests and len(values) == len(requests) else None
        reports.append({
            "run_id": run_id, "policy": next(iter(policies)), "cutoff_ms": cutoff,
            "tasks": [{"task_id": name, "elapsed_ms": t["finish"]-t["start"] if t["finish"] is not None else None,
                       "completed": t["finish"] is not None, "success": t["success"]} for name, t in tasks.items()],
            "delegation_modes": dict(modes), "llm_requests": len(requests),
            "parent_llm_requests": sum(e["actor"] == "parent" for e in requests.values()),
            "usage": usage, "usage_coverage": coverage,
            "accepted_messages": len(accepted), "first_consumed_messages": len(consumed),
            "unconsumed_message_ids": sorted(accepted.keys()-consumed.keys()),
            "message_first_consumption": consumed,
            "distinct_requests_consuming_new_messages": len({x["request_id"] for x in consumed.values()}),
            "repeated_reads_same_artifact_version": sum(n-1 for n in reads.values()),
            "observed_slot_ms_by_state": dict(slot_ms),
            "peak_observed_activation_slots": peak_slots,
            "unreleased_activation_ids": sorted(k for k, s in slots.items() if not s["released"]),
            "activation_rejections": dict(rejected),
            "interpretation": "Measured summaries only. Pending is not lost; resident is not GPU-active; absent usage is unknown."
        })
    return {"format_version": 1, "reports": reports}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    with args.trace.open(encoding="utf-8") as file:
        events = [json.loads(line) for line in file if line.strip()]
    result = json.dumps(analyze(events), ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(result+"\n", encoding="utf-8")
    else:
        print(result)


if __name__ == "__main__":
    main()
