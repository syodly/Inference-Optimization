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
    def __init__(self, policy, cap, engine, journal, session_cap=12):
        self.policy, self.cap, self.engine, self.journal = policy, cap, engine, journal
        self.pending = []
        self.running = 0
        self.remaining = {}
        self.tools = {}
        self.session_cap = session_cap
        self.sessions = set()
        self.session_pending = []
        self.wake = asyncio.Event()
        self.closed = False

    def target(self):
        if self.policy in ["native", "backend_priority"]:
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
        if self.policy in ['progress', 'return_priority']:
            now = time.monotonic()
            return min(self.pending, key=lambda p: (
                0 if now - p.ready > 10 else 1,
                0 if p.stage == "synthesis" else 1,
                0 if self.policy == 'return_priority' and p.stage == 'evidence' else 1,
                self.remaining.get(p.root_id, 99) if self.policy == 'progress' else 0, p.ready))
        return min(self.pending, key=lambda p: p.ready)

    async def loop(self):
        while not self.closed:
            while self.session_pending and (self.policy != 'session_window' or len(self.sessions) < self.session_cap):
                p = self.session_pending.pop(0)
                if p.future.cancelled():
                    continue
                self.sessions.add(p.node_id)
                self.journal.write('events', event='session_admitted', root_id=p.root_id, node_id=p.node_id,
                                   session_wait=time.monotonic() - p.ready, active_sessions=len(self.sessions),
                                   session_cap=self.session_cap if self.policy == 'session_window' else None)
                p.future.set_result(None)
            while self.pending and self.running < self.target():
                p = self.choose()
                self.pending.remove(p)
                if p.future.cancelled():
                    continue
                self.running += 1
                self.journal.write("events", event="frontend_release", root_id=p.root_id,
                                   node_id=p.node_id, stage=p.stage, frontend_wait=time.monotonic() - p.ready,
                                   inflight_calls=self.running, tools_inflight=len(self.tools), pending=len(self.pending),
                                   active_sessions=len(self.sessions),
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

    async def open_session(self, root_id, node_id):
        future = asyncio.get_running_loop().create_future()
        self.session_pending.append(Pending(root_id, node_id, 'session', time.monotonic(), future))
        self.journal.write('events', event='session_ready', root_id=root_id, node_id=node_id)
        self.wake.set()
        await future

    def close_session(self, root_id, node_id):
        self.sessions.remove(node_id)
        self.journal.write('events', event='session_released', root_id=root_id, node_id=node_id,
                           active_sessions=len(self.sessions))
        self.wake.set()

    def release(self):
        self.running -= 1
        self.wake.set()

    def close(self):
        self.closed = True
        self.wake.set()
