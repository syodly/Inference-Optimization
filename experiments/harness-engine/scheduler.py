"""Baseline request policies; optional mechanisms follow measured pain points."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import time


@dataclass
class Pending:
    root_id: str
    node_id: str
    stage: str
    ready: float
    future: asyncio.Future


class Controller:
    def __init__(self, policy, cap, engine, journal):
        self.policy, self.cap, self.engine, self.journal = policy, cap, engine, journal
        self.pending = []
        self.running = 0
        self.remaining = {}
        self.tools = {}
        self.wake = asyncio.Event()
        self.closed = False

    def target(self):
        if self.policy == "native":
            return 128
        if self.policy == "pressure":
            m = self.engine.latest
            kv, waiting = m.get("kv_usage"), m.get("waiting")
            if kv is not None and kv > 0.9:
                return max(2, self.cap // 2)
            if waiting is not None and waiting > 2:
                return max(2, self.cap - int(waiting))
        return self.cap

    def choose(self):
        if self.policy == "progress":
            now = time.monotonic()
            return min(self.pending, key=lambda p: (
                0 if now - p.ready > 10 else 1,
                0 if p.stage == "synthesis" else 1,
                self.remaining.get(p.root_id, 99), p.ready))
        return min(self.pending, key=lambda p: p.ready)

    async def loop(self):
        while not self.closed:
            while self.pending and self.running < self.target():
                p = self.choose()
                self.pending.remove(p)
                if p.future.cancelled():
                    continue
                self.running += 1
                self.journal.write("events", event="frontend_release", root_id=p.root_id,
                                   node_id=p.node_id, stage=p.stage, frontend_wait=time.monotonic() - p.ready,
                                   inflight_calls=self.running, tools_inflight=len(self.tools), pending=len(self.pending),
                                   policy=self.policy, target=self.target(), engine_observation=self.engine.latest)
                p.future.set_result(None)
            self.wake.clear()
            try:
                await asyncio.wait_for(self.wake.wait(), timeout=0.1)
            except asyncio.TimeoutError:
                pass

    async def admit(self, root_id, node_id, stage):
        future = asyncio.get_running_loop().create_future()
        self.pending.append(Pending(root_id, node_id, stage, time.monotonic(), future))
        self.journal.write("events", event="model_ready", root_id=root_id, node_id=node_id,
                           stage=stage, tools_inflight=len(self.tools), pending=len(self.pending))
        self.wake.set()
        await future

    def release(self):
        self.running -= 1
        self.wake.set()

    def close(self):
        self.closed = True
        self.wake.set()
