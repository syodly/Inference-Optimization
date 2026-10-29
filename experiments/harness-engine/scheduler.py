"""Baseline request policies; optional mechanisms follow measured pain points."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import time
import math


@dataclass
class Pending:
    root_id: str
    node_id: str
    stage: str
    ready: float
    future: asyncio.Future
    prompt_tokens: int = 0


class Controller:
    def __init__(self, policy, cap, engine, journal, session_cap=12, starvation_seconds=10,
                 history_budget_tokens=200000, history_output_reserve=1024):
        self.policy, self.cap, self.engine, self.journal = policy, cap, engine, journal
        self.pending = []
        self.running = 0
        self.remaining = {}
        self.tools = {}
        self.session_cap = session_cap
        self.sessions = set()
        self.session_pending = []
        self.starvation_seconds = starvation_seconds
        self.history_budget_tokens = history_budget_tokens
        self.history_output_reserve = history_output_reserve
        self.history_claims = {}
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

    def history_target(self):
        if self.policy == 'history_pressure':
            m = self.engine.latest
            if (m.get('kv_usage') or 0) > .9:
                return int(self.history_budget_tokens * .8)
            if (m.get('waiting') or 0) > 4:
                return int(self.history_budget_tokens * .9)
        return self.history_budget_tokens

    def claim_size(self, prompt_tokens):
        # A virtual token working-set budget, not a promise of physical KV residency.
        return math.ceil((prompt_tokens + self.history_output_reserve) / 784) * 784

    def eligible(self, p):
        if self.policy not in ['history_budget', 'history_pressure'] or p.stage != 'draft':
            return True
        return not self.history_claims or sum(self.history_claims.values()) + self.claim_size(p.prompt_tokens) <= self.history_target()

    def choose(self, candidates):
        if self.policy in ['progress', 'return_priority', 'session_return', 'size_return', 'history_budget', 'history_pressure']:
            now = time.monotonic()
            return min(candidates, key=lambda p: (
                0 if now - p.ready > self.starvation_seconds else 1,
                0 if p.stage == "synthesis" else 1,
                0 if self.policy in ['return_priority', 'session_return', 'size_return', 'history_budget', 'history_pressure'] and p.stage == 'evidence' else 1,
                self.remaining.get(p.root_id, 99) if self.policy == 'progress' else 0,
                p.prompt_tokens if self.policy == 'size_return' else 0, p.ready))
        return min(candidates, key=lambda p: p.ready)

    async def loop(self):
        while not self.closed:
            while self.session_pending and (self.policy not in ['session_window', 'session_return'] or len(self.sessions) < self.session_cap):
                p = self.session_pending.pop(0)
                if p.future.cancelled():
                    continue
                self.sessions.add(p.node_id)
                self.journal.write('events', event='session_admitted', root_id=p.root_id, node_id=p.node_id,
                                   session_wait=time.monotonic() - p.ready, active_sessions=len(self.sessions),
                                   session_cap=self.session_cap if self.policy in ['session_window', 'session_return'] else None)
                p.future.set_result(None)
            while self.pending and self.running < self.target():
                candidates = [p for p in self.pending if self.eligible(p)]
                if not candidates:
                    break
                p = self.choose(candidates)
                self.pending.remove(p)
                if p.future.cancelled():
                    continue
                self.running += 1
                if self.policy in ['history_budget', 'history_pressure'] and p.stage == 'draft':
                    self.history_claims[p.node_id] = self.claim_size(p.prompt_tokens)
                    self.journal.write('events', event='history_claim_opened', node_id=p.node_id,
                                       history_tokens=self.history_claims[p.node_id],
                                       total_claimed=sum(self.history_claims.values()),
                                       history_target_tokens=self.history_target())
                self.journal.write("events", event="frontend_release", root_id=p.root_id,
                                   node_id=p.node_id, stage=p.stage, frontend_wait=time.monotonic() - p.ready,
                                   inflight_calls=self.running, tools_inflight=len(self.tools), pending=len(self.pending),
                                   active_sessions=len(self.sessions),
                                   history_claimed_tokens=sum(self.history_claims.values()),
                                   history_target_tokens=self.history_target(),
                                   policy=self.policy, target=self.target(), engine_observation=self.engine.latest)
                p.future.set_result(None)
            self.wake.clear()
            try:
                await asyncio.wait_for(self.wake.wait(), timeout=0.1)
            except asyncio.TimeoutError:
                pass

    async def admit(self, root_id, node_id, stage, prompt_tokens=0):
        if node_id in self.history_claims and stage == 'evidence':
            self.history_claims[node_id] = max(self.history_claims[node_id], self.claim_size(prompt_tokens))
            self.journal.write('events', event='history_claim_updated', node_id=node_id,
                               reason='formed_return_input', history_tokens=self.history_claims[node_id],
                               total_claimed=sum(self.history_claims.values()),
                               history_target_tokens=self.history_target())
        future = asyncio.get_running_loop().create_future()
        self.pending.append(Pending(root_id, node_id, stage, time.monotonic(), future, prompt_tokens))
        self.journal.write("events", event="model_ready", root_id=root_id, node_id=node_id,
                           stage=stage, tools_inflight=len(self.tools), pending=len(self.pending), prompt_tokens=prompt_tokens)
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
        released_history = self.history_claims.pop(node_id, None)
        self.journal.write('events', event='session_released', root_id=root_id, node_id=node_id,
                           active_sessions=len(self.sessions), released_history_tokens=released_history,
                           total_claimed=sum(self.history_claims.values()),
                           history_target_tokens=self.history_target())
        self.wake.set()

    def observe_completion(self, node_id, stage, usage):
        if node_id in self.history_claims and stage == 'draft':
            size = (usage.get('prompt_tokens') or 0) + (usage.get('completion_tokens') or 0)
            self.history_claims[node_id] = math.ceil(size / 784) * 784
            self.journal.write('events', event='history_claim_updated', node_id=node_id,
                               reason='actual_draft_usage', history_tokens=self.history_claims[node_id],
                               total_claimed=sum(self.history_claims.values()),
                               history_target_tokens=self.history_target())
        self.wake.set()

    def release(self):
        self.running -= 1
        self.wake.set()

    def close(self):
        self.closed = True
        self.wake.set()
