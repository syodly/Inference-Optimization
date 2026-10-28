"""Real streamed model execution and observed (not simulated) engine telemetry."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
import re
import time

import httpx


class Journal:
    def __init__(self, directory: Path):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=False)
        self.started = time.monotonic()
        self.files = {}

    def write(self, stream: str, **fields):
        if stream not in self.files:
            self.files[stream] = (self.directory / f"{stream}.jsonl").open("a", encoding="utf-8")
        row = {"t": time.monotonic() - self.started, "wall_time": time.time(), **fields}
        f = self.files[stream]
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()
        return row

    def close(self):
        for f in self.files.values():
            f.close()


class Engine:
    def __init__(self, url: str, model: str, journal: Journal, thinking: bool = False,
                 sampling_profile='greedy', reasoning_effort=None):
        self.url = url.rstrip("/")
        self.model, self.journal, self.thinking = model, journal, thinking
        self.sampling_profile, self.reasoning_effort = sampling_profile, reasoning_effort
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(240, connect=15),
                                       limits=httpx.Limits(max_connections=128, max_keepalive_connections=64))
        self.latest = {}
        self.samples = 0

    async def health(self):
        response = await self.client.get(self.url + "/health")
        response.raise_for_status()
        response = await self.client.get(self.url + "/v1/models")
        response.raise_for_status()
        return response.json()

    async def reset_cache(self):
        response = await self.client.post(self.url + "/reset_prefix_cache")
        response.raise_for_status()
        result = response.json()
        self.journal.write("events", event="prefix_cache_reset", status=response.status_code, result=result)
        if result.get('success') is not True:
            raise RuntimeError('Engine did not confirm prefix cache reset: ' + repr(result))

    async def sample(self):
        response = await self.client.get(self.url + "/metrics")
        response.raise_for_status()
        raw = response.text
        metrics = {}
        for line in raw.splitlines():
            if not line or line.startswith("#"):
                continue
            match = re.match(r'([^\s{]+)(?:\{[^}]*\})?\s+([-+\d.eE]+)', line)
            if match:
                name, value = match.groups()
                metrics.setdefault(name, []).append(float(value))
        def observed(fragment, average=False):
            values = [v for k, vals in metrics.items() if k.endswith(fragment) for v in vals]
            return (sum(values) / len(values) if average else sum(values)) if values else None
        self.latest = {
            "time": time.monotonic(), "running": observed("num_requests_running"),
            "waiting": observed("num_requests_waiting"), "kv_usage": observed("kv_cache_usage_perc", True),
            "preemptions": observed("num_preemptions_total"),
            "prefix_queries": observed("prefix_cache_queries_total"),
            "prefix_hits": observed("prefix_cache_hits_total"),
        }
        self.journal.write("metrics", **self.latest)
        if self.samples % 10 == 0:
            self.journal.write("metrics_raw", prometheus=raw)
        self.samples += 1
        return self.latest

    async def poll(self, stop: asyncio.Event, interval=0.25):
        while not stop.is_set():
            try:
                await self.sample()
            except (httpx.HTTPError, ValueError) as exc:
                self.journal.write("events", event="telemetry_error", error=repr(exc))
            try:
                await asyncio.wait_for(stop.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass

    async def generate(self, *, call_id: str, root_id: str, node_id: str, stage: str,
                       messages: list, max_tokens: int, seed: int, priority=0, thinking=None,
                       generation_overrides=None):
        payload = {"model": self.model, "messages": messages, "max_tokens": max_tokens,
                   "temperature": 0.0, "seed": seed, "stream": True,
                   "stream_options": {"include_usage": True},
                   "chat_template_kwargs": {"enable_thinking": self.thinking if thinking is None else thinking}}
        active_thinking = payload['chat_template_kwargs']['enable_thinking']
        if self.sampling_profile == 'qwen':
            payload.update(temperature=1.0 if active_thinking else .7, top_p=.95 if active_thinking else .8,
                           top_k=20, min_p=0.0, presence_penalty=0.0 if active_thinking else 1.5,
                           repetition_penalty=1.0)
        if active_thinking and self.reasoning_effort:
            payload['reasoning_effort'] = self.reasoning_effort
        if priority:
            payload["priority"] = priority
        if generation_overrides:
            payload.update(generation_overrides)
        start = time.monotonic()
        self.journal.write("requests", call_id=call_id, root_id=root_id, node_id=node_id,
                           stage=stage, payload=payload)
        self.journal.write("events", event="model_submit", call_id=call_id,
                           root_id=root_id, node_id=node_id, stage=stage)
        pieces, reasoning, usage = [], [], {}
        first_token = None
        finish_reason, server_id, server_metrics = None, None, None
        try:
            async with self.client.stream("POST", self.url + "/v1/chat/completions", json=payload,
                                          headers={"X-Request-Id": call_id}) as response:
                response.raise_for_status()
                server_id = response.headers.get("x-request-id")
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    content = line[6:]
                    if content == "[DONE]":
                        break
                    data = json.loads(content)
                    if "error" in data:
                        raise RuntimeError(data["error"])
                    if data.get("usage"):
                        usage = data["usage"]
                    if data.get('metrics'):
                        server_metrics = data['metrics']
                    for choice in data.get("choices", []):
                        delta = choice.get("delta", {})
                        text = delta.get("content") or ""
                        thought = delta.get("reasoning_content") or delta.get("reasoning") or ""
                        if (text or thought) and first_token is None:
                            first_token = time.monotonic()
                            self.journal.write("events", event="first_token", call_id=call_id,
                                               root_id=root_id, node_id=node_id)
                        pieces.append(text)
                        reasoning.append(thought)
                        finish_reason = choice.get("finish_reason") or finish_reason
        except Exception as exc:
            self.journal.write("responses", call_id=call_id, root_id=root_id, node_id=node_id,
                               stage=stage, error=repr(exc), text="".join(pieces), usage=usage,
                               duration=time.monotonic() - start)
            raise
        end = time.monotonic()
        result = {"text": "".join(pieces), "reasoning": "".join(reasoning), "usage": usage,
                  "duration": end - start, "ttft": first_token - start if first_token else None,
                  "finish_reason": finish_reason, "server_request_id": server_id,
                  "server_metrics": server_metrics}
        self.journal.write("responses", call_id=call_id, root_id=root_id, node_id=node_id,
                           stage=stage, **result)
        self.journal.write("events", event="model_complete", call_id=call_id,
                           root_id=root_id, node_id=node_id, stage=stage, usage=usage)
        return result

    async def close(self):
        await self.client.aclose()
