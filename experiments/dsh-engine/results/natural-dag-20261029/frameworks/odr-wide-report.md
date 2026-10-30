

# Orchestration Architecture Comparison: Open Deep Research, GPT Researcher, and DeepSeek Harness

## Introduction

This report provides a detailed architectural comparison of three multi-agent research/orchestration systems across five dimensions: (1) request decomposition, (2) child execution creation, (3) parallelism bounding and join semantics, (4) inter-work-unit dependencies, and (5) evidence for or against characterizing the execution as a "dynamic agent DAG." Each system is analyzed using first-person framing, with framework-level facts (what the code actually does) kept strictly separate from design proposals or speculative interpretations.

A critical attribution note precedes the analysis: the project commonly known as "Open Deep Research" (ODR) is maintained by **LangChain** at [langchain-ai/open_deep_research](https://github.com/langchain-ai/open_deep_research) [1]. It is frequently run against Anthropic's Claude models (its configuration supports an "Anthropic Native Web Search" backend), which creates a natural but incorrect association with Anthropic as the repository owner. No `anthropics/open-deep-research` repository was verified to exist. All ODR findings below are documented against the LangChain repository.

---

## Open Deep Research (LangChain)

**Canonical repository:** [langchain-ai/open_deep_research](https://github.com/langchain-ai/open_deep_research) [1]

**Key files:**
- `src/open_deep_research/deep_researcher.py` — orchestrator node (lines 282–325)
- `src/open_deep_research/configuration.py` — configuration fields (lines 64–118)

### 1. Request Decomposition

**Classification: Dynamic, LLM-decided (not fixed N).**

An incoming user request is decomposed into as many research units as the lead/supervisor model emits `ConductResearch` tool calls for. The number and content of sub-tasks are not hardcoded; they are the model's runtime output.

The decomposition logic lives in the orchestrator node at `src/open_deep_research/deep_researcher.py` (around line 282):

```python
# Handle ConductResearch calls (research delegation)
conduct_research_calls = [
    tool_call for tool_call in most_recent_message.tool_calls
    if tool_call["name"] == "ConductResearch"
]
```

The variable length of `conduct_research_calls` **is** the decomposition. Zero calls means no fan-out this turn; many calls means many sub-tasks. Each sub-task's topic is a free-form string the model chose: `tool_call["args"]["research_topic"]`.

This is a framework-level fact in the code. There is no "always N sub-queries" constant anywhere in the inspected source.

### 2. Child Execution Creation

**Classification: Recursive agent / graph re-invocation driven by the lead agent.**

Each child is created by re-invoking a researcher subgraph once per `ConductResearch` tool call. The orchestrator is a lead "Research Supervisor" agent whose tool-calling decision is the spawning mechanism. There is no separate fixed planner/router class or hand-rolled scheduler object; the spawning **is** the supervisor agent emitting tool calls and the orchestrator node mapping each call to a subgraph invocation.

From `src/open_deep_research/deep_researcher.py`:

```python
research_tasks = [
    researcher_subgraph.ainvoke({
        "researcher_messages": [
            HumanMessage(content=tool_call["args"]["research_topic"])
        ],
        "research_topic": tool_call["args"]["research_topic"]
    }, config)
    for tool_call in allowed_conduct_research_calls
]
```

`researcher_subgraph` is a recursive LangGraph agent — it can itself make tool calls, including search and nested research. Each child is an independent `ainvoke` of that same subgraph.

**Best architectural label:** a **recursive agent** (the subgraph), spawned by a **lead agent** (Research Supervisor). It is not a classic graph scheduler with a declared edge set, and it is not a fixed router.

### 3. Parallelism Bounds and Join Semantics

#### Bounding — List-slicing cap with overflow rejection (NOT a semaphore)

From `src/open_deep_research/deep_researcher.py`:

```python
# Limit concurrent research units to prevent resource exhaustion
allowed_conduct_research_calls = conduct_research_calls[:configurable.max_concurrent_research_units]
overflow_conduct_research_calls = conduct_research_calls[configurable.max_concurrent_research_units:]
```

The cap value is a config field defined in `src/open_deep_research/configuration.py` (line 64):

```python
max_concurrent_research_units: int = Field(
    default=5,
    metadata={
        "x_oap_ui_config": {
            "type": "slider",
            "default": 5,
            "min": 1,
            "max": 20,
            "step": 1,
            "description": "Maximum number of research units to run concurrently. ..."
        }
    }
)
```

The bound is a **per-turn cap with overflow rejection**. Calls beyond the cap are not queued — they are dropped and returned to the model as an error message:

```python
for overflow_call in overflow_conduct_research_calls:
    all_tool_messages.append(ToolMessage(
        content=f"Error: Did not run this research as you have already exceeded the maximum "
                f"number of concurrent research units. Please try again with {configurable.max_concurrent_research_units} or fewer...",
        name="ConductResearch", tool_call_id=overflow_call["id"]))
```

This is neither an `asyncio.Semaphore` nor a "gather with limit" primitive. It is a hard truncation followed by error feedback to the LLM.

#### Join — `asyncio.gather` (barrier / fan-in)

```python
tool_results = await asyncio.gather(*research_tasks)

# Create tool messages with research results
for observation, tool_call in zip(tool_results, allowed_conduct_research_calls):
    all_tool_messages.append(ToolMessage(
        content=observation.get("compressed_research", "Error synthesizing research report: Maximum retries exceeded"),
        name=tool_call["name"],
        tool_call_id=tool_call["id"]
    ))
```

`await asyncio.gather(*research_tasks)` is a **barrier join**: the turn does not proceed until all children in this turn complete. Each child's `compressed_research` output is fed back to the supervisor as a `ToolMessage`.

#### Per-sub-task constraints

No explicit per-subtask wall-clock timeout is present in the inspected code. Per-sub-task work is bounded indirectly by iteration limits in `configuration.py`:

- `max_react_tool_calls` (default 10, max 30) — maximum tool-calling iterations in a single researcher step.
- `max_researcher_iterations` (default 6, max 10) — maximum research iterations for the Research Supervisor (i.e., the number of times it reflects and asks follow-up questions).

These are **budget/iteration caps**, not timeouts.

### 4. Dependency Between Work Units

**Classification: Independent within a turn; gated/conditioned across supervisor iterations.**

The data flow follows three stages:

**Fan-out (independence within a turn):** Each child is seeded with only its own `research_topic`:

```python
"researcher_messages": [HumanMessage(content=tool_call["args"]["research_topic"])],
"research_topic": tool_call["args"]["research_topic"]
```

There is no shared blackboard or state passed into a child. Children do not read each other's outputs. Within one fan-out turn, sub-tasks are independent given the lead agent's decomposition.

**Fan-in (shared memory):** Results accumulate into the supervisor's state. Each child's `compressed_research` is returned as a `ToolMessage`, and raw notes are concatenated into shared state:

```python
raw_notes_concat = "\n".join([
    "\n".join(observation.get("..."
```

This shared context lives in the supervisor's message history (the lead agent), not in a blackboard that children read.

**Sequential gating (conditional re-spawning across iterations):** The supervisor can loop (bounded by `max_researcher_iterations`). On each iteration it reflects on prior research and may emit new `ConductResearch` calls conditioned on earlier findings. This is where inter-stage dependency lives: later waves of sub-tasks depend on earlier results, but only because the lead agent reads the joined results and decides what to spawn next.

**Summary:** The dependency model is supervisor-mediated, sequential-gated, iterative re-decomposition. It is not a shared-memory blackboard and not direct child-to-child edges.

### 5. Evidence for "Dynamic Agent DAG" Characterization

| Evidence | Location | What it proves |
|----------|----------|----------------|
| Variable sub-task count = `len(conduct_research_calls)` | `deep_researcher.py` (filter of `most_recent_message.tool_calls`) | Worker count is decided at runtime by LLM output, not a constant → rules out a static pipeline and a fixed flat map |
| Recursive `researcher_subgraph.ainvoke(...)` per topic | `deep_researcher.py` | Each worker is itself an agent (recursive), not a single map iteration |
| Supervisor iteration loop with re-emitted `ConductResearch` calls | `configuration.py` `max_researcher_iterations`; fan-in `ToolMessage`s feeding the lead agent | Conditional re-spawning based on intermediate results → multiple waves, i.e., depth > 1 |
| Capacity truncation + overflow rejection | `deep_researcher.py` slicing; `configuration.py` `max_concurrent_research_units` | The DAG's width is dynamically bounded at runtime |

**Verdict:** The execution is legitimately not a static pipeline (steps are LLM-emitted and variable) and not a flat parallel map of a fixed set of independent workers (count is variable and there is iterative re-spawning).

**Precision note:** The term "DAG" overstates the structure slightly. In the code, children are siblings under the supervisor. There is no evidence of cross-child edges (child A's output being fed directly into child B). The structure is best described as a **dynamic, capacity-bounded, iteratively-re-spawned tree / fan-in loop** (supervisor → parallel children → join → repeat) of bounded depth. Calling it a "dynamic agent DAG" is defensible in the loose sense (variable, runtime-determined, multi-wave, directed dependency structure), but it is not a general-purpose directed acyclic graph with arbitrary node-to-node edges.

---

## GPT Researcher (Assaf Elovic)

**Canonical repository:** [assafelovic/gpt-researcher](https://github.com/assafelovic/gpt-researcher) [2]

**Key file retrieved:** `gpt_researcher/skills/deep_research.py` (commit `3582a6841fe7dc801e2a34e34ee408641aea9bce`)

**Coverage limitation:** The core orchestration files (`planner.py`, `executor.py`, or their equivalents) were not retrievable from the search corpus. The findings below are based on the `deep_research` skill file, which provides strong evidence of the recursive multi-level pattern, combined with the well-known architectural pattern of the core system (Planner → Executor → Writer). Where the core files' exact paths could not be verified, this is noted explicitly.

### 1. Request Decomposition

**Classification: Dynamic, LLM-generated with parameterized breadth.**

In the `deep_research` skill (the multi-level recursive mode), decomposition occurs via:

```python
serp_queries = await self.generate_search_queries(query, num_queries=breadth)
print(f"✅ Generated {len(serp_queries)} queries: {[q['query'] for q in serp_queries]}", flush=True)
progress.total_queries = len(serp_queries)
```

The function `generate_search_queries` is an LLM call that produces a variable number of sub-queries. The `breadth` parameter sets an upper bound on how many the model should generate, but the actual count is the model's output. This is dynamic decomposition — the content and exact count are determined at runtime.

In the **core (non-skill) mode**, the architectural pattern is a two-stage pipeline: a `Planner` component calls an LLM to generate sub-queries (typically 3–5 by default, configurable), and an `Executor` component runs them. The exact file paths for the core `Planner` and `Executor` classes were not retrieved in this research pass, but the pattern is well-documented in the project's public documentation and README.

**Framework-level fact:** In the `deep_research` skill, `num_queries=breadth` is passed to the LLM as a generation parameter. The LLM decides the actual count up to that bound. This is not a fixed N.

### 2. Child Execution Creation

**Classification: Recursive instantiation of the same researcher class.**

From `gpt_researcher/skills/deep_research.py` (lines 418–466):

```python
async def process_query(serp_query: Dict[str, str]) -> Optional[Dict[str, Any]]:
    async with semaphore:
        try:
            from .. import GPTResearcher
            researcher = GPTResearcher(
                query=serp_query['query'],
                report_type=ReportType.ResearchReport.value,
                report_source=ReportSource.Web.value,
                tone=self.tone,
                websocket=self.websocket,
                config_path=self.config_path,
                headers=self.headers,
                visited_urls=self.visited_urls,
                # Propagate MCP configuration to nested researchers
                mcp_configs=self.researcher.mcp_configs,
                mcp_strategy=self.researcher.mcp_strategy
            )
            context = await researcher.conduct_research()
```

Each sub-query spawns a **new `GPTResearcher` instance** — the same class that handles the top-level request. This is recursive: the child researcher itself can decompose further (in the `deep_research` skill mode, it can invoke `deep_research` again for deeper levels).

The spawning mechanism is the `process_query` closure defined inside the deep research method. There is no separate router or scheduler class visible in the retrieved code. The orchestration is embedded in the method body.

**Architectural label:** A **recursive self-instantiation** pattern. The parent creates children by constructing new instances of its own class with narrower query scope. In the core (non-skill) mode, the `Executor` class is the component that creates and runs child sub-query executions.

### 3. Parallelism Bounds and Join Semantics

#### Bounding — `asyncio.Semaphore`

```python
semaphore = asyncio.Semaphore(self.concurrency_limit)

async def process_query(serp_query: Dict[str, str]) -> Optional[Dict[str, Any]]:
    async with semaphore:
        ...
```

This is a **true semaphore-based concurrency limit**. Unlike ODR's list-slicing approach, GPT Researcher's deep research skill uses a semaphore, which means:
- All tasks are submitted to the event loop.
- At most `concurrency_limit` tasks execute simultaneously.
- Tasks beyond the limit **wait** (they are queued implicitly by the semaphore) rather than being rejected.

This is a fundamentally different bounding strategy from ODR: **queuing vs. rejection**.

#### Join — Implied `asyncio.gather` (barrier)

The retrieved code shows `process_query` defined as an async function within the method. While the exact join line was cut off in the retrieved excerpt, the pattern (defining async closures and then gathering them) is the standard asyncio fan-out/fan-in idiom. The join is a **barrier**: all sub-queries in a level must complete before the level's results are aggregated and passed to the next stage (or to the report writer).

#### Per-sub-task constraints

The `concurrency_limit` parameter bounds width. The `breadth` parameter bounds the number of sub-queries per level. In the core mode, the `Planner` typically generates a fixed small number (3–5) by default. No explicit per-task wall-clock timeout was visible in the retrieved code.

### 4. Dependency Between Work Units

**Classification: Independent within a level; hierarchical/sequential across levels (deep research mode).**

**Within a level:** Each sub-query spawns an independent `GPTResearcher` instance. The `visited_urls` parameter is shared (for deduplication across siblings), but no child reads another child's research output. Siblings are independent given their assigned query.

**Across levels (deep research mode):** The `deep_research` skill is explicitly recursive. After a level completes, the aggregated learnings from that level feed into the generation of the next level's sub-queries. This creates a **sequential, depth-based dependency**: level N+1's sub-queries are generated based on level N's findings. The `breadth` parameter controls fan-out width per level, and the recursion depth controls how many levels exist.

**Shared state:** The `visited_urls` set is shared across nested researchers (passed via constructor), providing a deduplication mechanism. MCP configuration is also propagated. This is a lightweight shared state, not a full blackboard.

**Core mode (non-skill):** The core pipeline is Planner → Executor → Writer. The Planner's output (sub-queries) is the input to the Executor. The Executor's output (research context) is the input to the Writer. This is a **static three-stage pipeline** with parallelism only within the Executor stage.

### 5. Evidence for "Dynamic Agent DAG" Characterization

| Evidence | Location | What it proves |
|----------|----------|----------------|
| `generate_search_queries(query, num_queries=breadth)` — LLM-determined count | `deep_research.py` line 418 | Worker count is runtime-determined, not a constant |
| Recursive `GPTResearcher(...)` instantiation per sub-query | `deep_research.py` line 435+ | Each worker is itself a full researcher (recursive) |
| `asyncio.Semaphore(self.concurrency_limit)` | `deep_research.py` line 431 | Width is dynamically bounded; tasks queue rather than reject |
| Multi-level recursion (deep research mode) | Architectural pattern of the skill | Multiple waves exist; later waves depend on earlier findings |
| Shared `visited_urls` across nested researchers | `deep_research.py` constructor parameter | Lightweight cross-worker shared state |

**Verdict:** In **deep research mode**, the execution is a **dynamic, multi-level, recursively-spawned tree** with LLM-determined width at each level and sequential dependency between levels. This is legitimately "dynamic" (not a fixed pipeline) and has directed dependencies (later levels depend on earlier ones). However, within any single level, siblings are independent — there are no cross-sibling edges. The structure is a **dynamic tree with level-synchronous barriers**, not a general DAG with arbitrary edges.

In **core mode**, the execution is closer to a **static three-stage pipeline** (Plan → Execute → Write) with internal parallelism in the Execute stage. This is less "dynamic" because the stage structure is fixed and the number of sub-queries, while LLM-generated, feeds into a single fixed executor stage.

**Interpretation (separate from facts):** Characterizing GPT Researcher's deep research mode as a "dynamic agent DAG" is defensible if one means "a dynamically-constructed, multi-stage, directed dependency structure with LLM-determined shape." It is not a "DAG" in the strict graph-theoretic sense of arbitrary directed edges between arbitrary nodes.

---

## DeepSeek Harness (DeepSeek AI)

**Canonical repository:** [deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) [3]

**Key package:** `@deepseek-ai/dsh-subagent` at `packages/subagent/subagent/`

**Primary documentation source:** `packages/subagent/subagent/README.md` (commit `687f282e8625c6b8d11ff58211a90524be2e4317`)

**Coverage limitation:** The README provides the architectural contract (API surface, configuration parameters, behavioral semantics) but the internal implementation files (exact class names, data structures, message-passing protocol) were not directly retrieved. The analysis below is grounded in the documented API contract.

### 1. Request Decomposition

**Classification: Dynamic, LLM-decided at runtime via tool invocation.**

Decomposition in DeepSeek Harness is driven by the parent agent's (running on a DeepSeek model) decision to call the `subagent` tool. The mechanism is:

- The parent agent decides to invoke the delegation tool (configured as `@deepseek-ai/dsh-tool-subagent` with `provider: spawn` and `toolName: subagent`).
- The tool call from the model is what triggers delegation. The model itself determines when to decompose work and what tasks to delegate.
- There is no evidence of a separate "planner" component or static decomposition step in the documented architecture. The LLM's tool-calling behavior **is** the decomposition.

The README states: "工具立即返回子会话 ID" (the tool immediately returns a child session ID), confirming that the model invokes the tool and the system responds by spawning. The decomposition logic lives in the model's decision to call the tool, not in framework code.

**Key distinction from ODR and GPT Researcher:** In ODR, the decomposition is visible in the orchestrator node's code (it filters for `ConductResearch` tool calls). In GPT Researcher's deep research mode, there is an explicit `generate_search_queries` LLM call. In DeepSeek Harness, the decomposition is fully opaque to the framework — it is an emergent property of the model's tool-calling behavior. The framework only provides the tool and handles the mechanics of spawning.

### 2. Child Execution Creation

**Classification: Provider-based routing via `startActivation` function.**

The component responsible for creating each child execution is the **subagent service**, accessed via the `startActivation` function:

```
startActivation({ provider, label, request, signal, delivery })
→ { childId, messageId?, result, dispose }
```

The architecture uses a **provider-based router** pattern. The service routes each delegation request to a named provider backend:

| Package | Role |
|---------|------|
| `@deepseek-ai/dsh-subagent` | Service layer (admission, cancellation, ownership, discovery) |
| `@deepseek-ai/dsh-subagent-spawn-in-process` | Provider backend (in-process spawn) |
| `@deepseek-ai/dsh-tool-subagent` | Model-facing tool that triggers delegation |

**Supported providers:** `spawn` (in-process), `fork`, `ACP`, `DSH SDK`, `Codex`, `Claude Code`.

The `provider` parameter in `startActivation` allows **dynamic routing to different backends at runtime**. This is a more flexible spawning mechanism than ODR (which always invokes the same subgraph) or GPT Researcher (which always instantiates the same class).

**Local vs. external children:**
- **Local children** (spawn, fork): Accept follow-up messages, support cold recovery, retain persistent sessions.
- **External children** (ACP, DSH SDK, Codex, Claude Code): Execute once only, reject continued input.

### 3. Parallelism Bounds and Join Semantics

#### Bounding — Admission control with capacity rejection (no queuing)

The `maxActiveSubagents` setting (default: **8**) limits the number of online and in-creation children per activation tree. From the README:

> "在 Host 插件上设置 `maxActiveSubagents`，限制每棵 activation 树中在线和正在创建的子级数量。默认值为 8，接受正安全整数。"

Key behavioral details:
- The top-level parent establishes a pool shared by local and external descendants; the root parent does not occupy a slot.
- New creation and cold recovery **reserve a slot before yielding execution**; it is only returned after resource release completes.
- Waiting descendants, activations with pending inbox content, and stopping activations still count toward capacity.
- Sending messages to resident children **reuses** their slot (no new slot needed).
- When capacity is exhausted, new creation is **rejected** with `ACTIVATION_LIMIT_REACHED` (not queued).

The critical design choice, stated explicitly in the README:

> "接纳不会排队，避免等待后代的父代理又等待自己占用的名额"
> (Admission does not queue, avoiding a parent agent waiting on descendants from also waiting on its own occupied slot.)

This is a **deliberate anti-deadlock design**: if the parent occupies a slot and is waiting for its children, and new admissions queue behind the parent's occupied slot, you get a deadlock. By rejecting instead of queueing, the system guarantees liveness.

**Comparison to other systems:**
- ODR: Rejects overflow (list-slicing), but the rejection is per-turn and the model is informed via error message.
- GPT Researcher: Queues via semaphore (tasks wait).
- DeepSeek Harness: Rejects with a specific error code, with an explicit rationale for avoiding deadlock in a recursive spawning model.

#### Join Semantics — Two delivery modes

The `delivery` parameter in `startActivation` controls how results flow back:

| Mode | Behavior |
|------|----------|
| `delivery: 'parent'` | The parent agent receives a model-facing completion notification (asynchronous). The parent can continue working while children run. |
| `delivery: 'caller'` | The workflow/caller waits for the result directly (synchronous). No parent notification is sent. |

This is a **more flexible join model** than either ODR (always barrier via `asyncio.gather`) or GPT Researcher (barrier at level boundaries). With `delivery: 'parent'`, the parent can spawn multiple children and process their completions in **any order** as they arrive — this is an **asynchronous notification pattern**, not a barrier.

#### Timeout/Budget Constraints

No explicit per-sub-task timeout or token budget was documented in the retrieved material. The capacity mechanism (`maxActiveSubagents`) is the primary concurrency bound. The `maxDepth` setting (default 1) bounds recursion depth.

### 4. Dependency Between Work Units

**Classification: Parent-hub, message-passing, with optional sequential follow-up.**

**Local children (spawn, fork):**
- Accept **follow-up messages** — the parent can send additional messages to a resident child, enabling **sequential gating** within a parent-child relationship.
- Support **cold recovery** — persistent sessions that can be resumed after interruption.
- This means later work can depend on earlier findings: the parent reads a child's result, then sends a follow-up message to the same child (or a different child) conditioned on what it learned.

**External children (ACP, DSH SDK, Codex, Claude Code):**
- Execute **once only** — fire-and-forget with a single result. No follow-up, no continued input.

**Inter-child communication:** The documentation mentions "所有权与发现机制" (ownership and discovery mechanisms) shared across all children, but no explicit inter-child message passing or blackboard was documented. The parent agent is the hub. Children report back to the parent (via completion notification or caller wait). There is no evidence of direct child-to-child communication.

**Data flow summary:** The parent agent is the central coordinator. It spawns children, receives results (via notification or wait), and decides next steps. Dependencies flow through the parent — there are no direct child-to-child edges.

### 5. Evidence for "Dynamic Agent DAG" Characterization

| Evidence | Location | What it proves |
|----------|----------|----------------|
| LLM decides when and how many times to call `subagent` tool | README: "工具立即返回子会话 ID" | Worker count and creation timing are runtime-determined by the model |
| `maxDepth` controls recursion (default 1, configurable higher) | README: Delegation Settings section | Recursive spawning is supported, enabling multi-level structures |
| `provider` parameter allows routing to different backends | README: `startActivation` signature | Dynamic routing — different children can use different execution backends |
| `delivery: 'parent'` enables asynchronous completion notifications | README: Local vs. External Children section | Results can arrive in any order; parent processes them as they complete (not a fixed pipeline) |
| Local children accept follow-up messages | README: Local vs. External Children section | Sequential dependency within a parent-child pair is supported |
| `maxActiveSubagents` with admission rejection | README: Activation Capacity section | Width is dynamically bounded with explicit anti-deadlock design |

**Evidence AGAINST a pure dynamic DAG:**

| Evidence | What it suggests |
|----------|------------------|
| Default `maxDepth: 1` | By default, only one level of delegation is allowed → flat star topology (parent → N children), not a deep DAG |
| No queuing (admission rejection) | More of a bounded concurrent execution model than a true DAG scheduler with topological ordering |
| No explicit DAG data structure | No evidence of a graph data structure, edge definitions, or topological sorting in the documented API |
| No inter-child communication documented | No cross-sibling edges; all dependencies flow through the parent |

**Verdict:** The architecture is best characterized as a **bounded, LLM-driven, hierarchical delegation system** with dynamic task creation. It **supports** a dynamic DAG topology (especially with `maxDepth > 1` and `delivery: 'parent'` for asynchronous result processing), but the **default configuration** produces a flat parallel fan-out/fan-in pattern. It is not a static pipeline (the LLM decides structure at runtime) but also not a fully general DAG scheduler (no explicit dependency graph, no topological execution ordering). The "DAG" emerges implicitly from the parent-child relationship, timing, and follow-up messaging — it is not explicitly represented as a graph data structure.

---

## Cross-System Comparison Table

| Dimension | Open Deep Research (LangChain) | GPT Researcher (Assaf Elovic) | DeepSeek Harness (DeepSeek AI) |
|-----------|-------------------------------|-------------------------------|-------------------------------|
| **Decomposition mechanism** | LLM emits `ConductResearch` tool calls; count = `len(tool_calls)` | LLM generates sub-queries via `generate_search_queries(query, num_queries=breadth)` | LLM calls `subagent` tool; count determined by model's tool-calling behavior |
| **Decomposition is dynamic?** | Yes — fully LLM-determined, no fixed N | Yes — LLM-determined with `breadth` as soft upper bound | Yes — fully LLM-determined, opaque to framework |
| **Child creation component** | Orchestrator node maps each tool call to `researcher_subgraph.ainvoke()` | `process_query` closure instantiates new `GPTResearcher` per sub-query | `startActivation()` function routes to a named provider backend |
| **Child execution type** | Recursive LangGraph subgraph (same subgraph for all children) | Recursive class instantiation (same `GPTResearcher` class) | Provider-routed: spawn, fork, ACP, DSH SDK, Codex, Claude Code |
| **Parallelism bound mechanism** | List-slicing: `calls[:max]` with overflow rejected as error | `asyncio.Semaphore(concurrency_limit)` — tasks queue | `maxActiveSubagents` (default 8) — admission rejection with `ACTIVATION_LIMIT_REACHED` |
| **Default concurrency limit** | 5 (max 20) | Configurable via `concurrency_limit` parameter | 8 (`maxActiveSubagents`) |
| **Overflow behavior** | Rejected; model receives error ToolMessage | Queued (semaphore waits) | Rejected; `ACTIVATION_LIMIT_REACHED` error; explicit anti-deadlock rationale |
| **Join semantics** | `await asyncio.gather(*tasks)` — barrier (all must complete) | Implied `asyncio.gather` at level boundaries — barrier | Two modes: `delivery: 'parent'` (async notification, order-independent) or `delivery: 'caller'` (synchronous wait) |
| **Recursion depth control** | `max_researcher_iterations` (default 6, max 10) bounds supervisor loop | Recursion is implicit in the `deep_research` skill's self-instantiation | `maxDepth` (default 1) — explicit, per-tool or per-host setting |
| **Per-task budget** | `max_react_tool_calls` (default 10, max 30) per researcher step | Not explicitly documented in retrieved code | Not explicitly documented in retrieved material |
| **Wall-clock timeout** | Not present in inspected code | Not visible in retrieved code | Not documented |
| **Within-level independence** | Yes — children receive only their own topic; no shared state passed in | Yes — each child is independent; `visited_urls` shared for dedup only | Yes — children are independent; parent is the hub |
| **Cross-level dependency** | Supervisor reads joined results, re-decomposes (sequential gating) | Level N+1 sub-queries generated from Level N's aggregated learnings | Parent reads child results, can send follow-up messages or spawn new children |
| **Inter-child (sibling) edges** | None in code | None in code | None documented |
| **Shared state mechanism** | Supervisor's message history (ToolMessages, raw_notes_concat) | `visited_urls` set propagated via constructor; MCP config propagated | Ownership and discovery mechanisms (documented but not detailed) |
| **Explicit DAG data structure?** | No — tree/fan-in loop emerges from code flow | No — level-synchronous tree emerges from recursion | No — hierarchy emerges from parent-child activation tree |
| **Topological ordering?** | No — barrier join per turn; turns are sequential | No — level-synchronous barriers | No — `delivery: 'parent'` allows out-of-order completion processing |

---

## Synthesis: What Makes a "Dynamic Agent DAG" Legitimate?

Based on the evidence across all three systems, the following criteria can be distilled for legitimately characterizing an execution as a "dynamic agent DAG" as opposed to a static pipeline or a flat parallel map:

### Criteria for "Dynamic" (vs. static pipeline)

1. **Variable worker count determined at runtime** — All three systems satisfy this. The number of children is LLM-emitted, not a compile-time constant.
2. **Conditional re-spawning based on intermediate results** — ODR satisfies this clearly (supervisor loop with re-emitted tool calls). GPT Researcher's deep research mode satisfies it (later levels generated from earlier findings). DeepSeek Harness satisfies it (parent can spawn new children after reading results).
3. **Non-fixed stage structure** — ODR and DeepSeek Harness: the number of "waves" is not predetermined. GPT Researcher core mode: the three-stage structure (Plan → Execute → Write) is fixed, making it less "