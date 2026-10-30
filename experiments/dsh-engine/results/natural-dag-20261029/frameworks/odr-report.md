

# Child Execution Creation: Open Deep Research, GPT Researcher, and DeepSeek Harness

## Who Initiates Child Execution

**Open Deep Research.** The Research Supervisor LLM emits `ConductResearch` tool calls. Code in `deep_researcher.py` filters `most_recent_message.tool_calls` for calls named `"ConductResearch"`, then invokes `researcher_subgraph.ainvoke(...)` for each allowed call [1]. The parent worker initiates; no external trigger is involved.

**GPT Researcher.** The parent `deep_research` method calls `self.generate_search_queries(query, num_queries=breadth)` to produce a list of search queries, then spawns a `process_query` coroutine for each query and executes them via `asyncio.gather` [3]. The parent worker initiates.

**DeepSeek Harness.** The parent worker calls a delegation tool that immediately returns a child session ID. The documentation states that "mounting the service alone does not enable delegation" — the caller must explicitly invoke the tool [4]. This is what makes the pattern optional: the capability exists but activation requires an explicit tool call from the parent.

## Sequential Dependency vs. Fan-Out

**Open Deep Research.** Children within a single supervisor turn are independent (fan-out). Each child receives only its own `research_topic` as input; all run simultaneously via `asyncio.gather` [1]. Cross-iteration dependency is parent-mediated: the supervisor reflects on results and may issue new `ConductResearch` calls in subsequent iterations, bounded by `max_researcher_iterations` [2].

**GPT Researcher.** Hybrid model. Within a single depth level, queries are independent and run in parallel (gated by a semaphore) [3]. Across depth levels, dependency is explicit: each child's `researchGoal` and `followUpQuestions` are concatenated into the `next_query` string that seeds the recursive call at `depth − 1` [3]. This is sequential dependency across levels, parallel fan-out within a level.

**DeepSeek Harness.** The available excerpt does not explicitly state whether children are independent or whether later children can consume earlier children's outputs. The asynchronous notification model (tool returns a session ID immediately; parent receives completion later) and the concurrent slot-reservation mechanism are consistent with parallel fan-out, but no source excerpt describes inter-child data dependencies. **Gap.**

## Concurrency Cap vs. Total Cumulative Work

| System | Concurrency Cap | Total Work Bound |
|--------|----------------|-----------------|
| Open Deep Research | `max_concurrent_research_units` (default 5, max 20) — max children per supervisor turn [2] | No explicit total-work parameter. Indirectly bounded by `max_researcher_iterations` (default 6, max 10) × `max_concurrent_research_units` [2] |
| GPT Researcher | `self.concurrency_limit` enforced via `asyncio.Semaphore` [3] | No explicit total-work parameter. Implicitly bounded by breadth halving across depth levels (`breadth + breadth/2 + breadth/4 + …`) [3] |
| DeepSeek Harness | `maxActiveSubagents` (default 8) — max online/in-creation children per activation tree [4] | No total-work cap found in available excerpts. `maxDepth` (default 1) limits tree depth, not total work [4] |

The distinction: a concurrency cap limits how many children execute *at any moment*; total cumulative work is the sum of all child executions over the full task lifecycle. In all three systems the concurrency cap is an explicit, named parameter. None exposes a single named parameter that hard-caps total cumulative child executions.

### Sources

[1] Open Deep Research — deep_researcher.py: https://github.com/langchain-ai/open_deep_research/blob/1b7d2e80db9faa586165c60e09096dbbfd483a64/src/open_deep_research/deep_researcher.py

[2] Open Deep Research — configuration.py: https://github.com/langchain-ai/open_deep_research/blob/1b7d2e80db9faa586165c60e09096dbbfd483a64/src/open_deep_research/configuration.py

[3] GPT Researcher — deep_research.py: https://github.com/assafelovic/gpt-researcher/blob/3582a6841fe7dc801e2a34e34ee408641aea9bce/gpt_researcher/skills/deep_research.py

[4] DeepSeek Harness — Subagent README: https://github.com/deepseek-ai/deepseek-harness/blob/687f282e8625c6b8d11ff58211a90524be2e4317/packages/subagent/subagent/README.zh.md