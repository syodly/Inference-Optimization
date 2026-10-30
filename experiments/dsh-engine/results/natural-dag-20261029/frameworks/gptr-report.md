

# Orchestration Mechanisms in Deep Research Systems: A Comparative Analysis of Open Deep Research, GPT Researcher, and DeepSeek Harness

## 1. Introduction

The orchestration of autonomous research agents represents a critical design challenge in modern LLM-based systems. Three prominent implementations—LangChain's Open Deep Research, GPT Researcher, and DeepSeek Harness—each adopt fundamentally different architectural approaches to decomposing a research request into parallelizable sub-tasks, bounding concurrent execution, and managing dependencies between successive research phases. This report synthesizes source-level evidence from each system to compare their orchestration mechanisms and evaluate the extent to which each constitutes a "dynamic agent DAG."

## 2. From Request to Independent Research Work

### 2.1 GPT Researcher: Static Recursive Decomposition

GPT Researcher transforms a single research query into a tree of sub-queries through a recursive depth-first process. At each level, the system generates a fixed number of search queries (determined by the `breadth` parameter) via an LLM call, then processes them concurrently. The critical design choice is that the *shape* of the tree is predetermined: at each recursion depth, the breadth is halved deterministically via `new_breadth = max(2, breadth // 2)` ([GPT Researcher source](https://github.com/assafelovic/gpt-researcher/blob/3582a6841fe7dc801e2a34e34ee408641aea9bce/gpt_researcher/skills/deep_research.py)). This means the branching factor is fixed by initial parameters and never adapts to evidence quality or information gaps discovered during research.

However, the *content* of each branch is data-dependent: the next query is constructed from the LLM-generated `researchGoal` and `followUpQuestions` from the parent result, making the direction of exploration adaptive even though the tree shape is not ([GPT Researcher source](https://github.com/assafelovic/gpt-researcher/blob/3582a6841fe7dc801e2a34e34ee408641aea9bce/gpt_researcher/skills/deep_research.py)).

### 2.2 Open Deep Research: Dynamic Supervisor-Driven Fan-Out

Open Deep Research employs a fundamentally different decomposition strategy. A Research Supervisor LLM decides *how many* `conduct_research` tool calls to issue in each iteration, bounded by `max_concurrent_research_units` (default 5, max 20) ([Open Deep Research configuration](https://github.com/langchain-ai/open_deep_research/blob/1b7d2e80db9faa586165c60e09096dbbfd483a64/src/open_deep_research/configuration.py)). The supervisor then reflects on accumulated results and decides whether to spawn additional sub-researchers, iterating up to `max_researcher_iterations` (default 6, max 10) times ([Open Deep Research configuration](https://github.com/langchain-ai/open_deep_research/blob/1b7d2e80db9faa586165c60e09096dbbfd483a64/src/open_deep_research/configuration.py)). This constitutes true data-dependent fan-out: both the number and the topics of child research units are determined by the LLM's assessment of current evidence.

### 2.3 DeepSeek Harness: Activation Tree with Delegation

DeepSeek Harness uses an "activation tree" model where a parent agent delegates work to child subagents. The delegation depth is controlled by `maxDepth` (default 1, meaning only direct children are permitted by default) ([DeepSeek Harness documentation](https://github.com/deepseek-ai/deepseek-harness/blob/687f282e8625c6b8d11ff58211a90524be2e4317/packages/subagent/subagent/README.zh.md)). The tool immediately returns a child session ID, and the parent receives a completion notification after the background activation settles. This is an asynchronous, event-driven model rather than a synchronous recursive one.

## 3. Which Layer Creates Each Child Execution

| System | Creation Layer | Mechanism | Hierarchy Depth |
|--------|---------------|-----------|-----------------|
| GPT Researcher | Recursive function call within `deep_research()` | Each successful result spawns a recursive call with halved breadth | Configurable (depth parameter) |
| Open Deep Research | Research Supervisor node in LangGraph | Supervisor issues `conduct_research` tool calls; each becomes a `researcher_subgraph.ainvoke()` | Fixed at 1 level (supervisor → sub-researchers) |
| DeepSeek Harness | Parent agent via delegation tool | Tool call creates a new activation; parent receives session ID immediately | Configurable via `maxDepth` (default 1) |

In GPT Researcher, the recursive function itself is the creation layer—each iteration of the `for result in results` loop that satisfies `depth > 1` spawns a new recursive call ([GPT Researcher source](https://github.com/assafelovic/gpt-researcher/blob/3582a6841fe7dc801e2a34e34ee408641aea9bce/gpt_researcher/skills/deep_research.py)). In Open Deep Research, the supervisor node within the LangGraph state machine is the sole creation layer; sub-researchers cannot further delegate ([Open Deep Research source](https://github.com/langchain-ai/open_deep_research/blob/1b7d2e80db9faa586165c60e09096dbbfd483a64/src/open_deep_research/deep_researcher.py)). In DeepSeek Harness, any agent at a depth below `maxDepth` can create children, making the creation layer potentially distributed across the tree.

## 4. Parallelism Bounding and Joining

### 4.1 Bounding Mechanisms

The three systems employ three distinct bounding strategies:

**GPT Researcher — Semaphore-based throttling:** Uses `asyncio.Semaphore(self.concurrency_limit)` to limit how many queries execute simultaneously. All tasks are created upfront and submitted to `asyncio.gather`, but the semaphore ensures no more than `concurrency_limit` execute in parallel at any moment ([GPT Researcher source](https://github.com/assafelovic/gpt-researcher/blob/3582a6841fe7dc801e2a34e34ee408641aea9bce/gpt_researcher/skills/deep_research.py)). This is a *non-lossy, blocking* approach: all work is eventually executed, but some tasks wait.

**Open Deep Research — Truncate-and-drop:** When the LLM generates more `conduct_research` calls than `max_concurrent_research_units`, the excess calls are silently discarded. The code explicitly slices: `allowed_conduct_research_calls = conduct_research_calls[:configurable.max_concurrent_research_units]` and `overflow_conduct_research_calls = conduct_research_calls[configurable.max_concurrent_research_units:]`, executing only the allowed batch via `asyncio.gather` ([Open Deep Research source](https://github.com/langchain-ai/open_deep_research/blob/1b7d2e80db9faa586165c60e09096dbbfd483a64/src/open_deep_research/deep_researcher.py)). This is a *lossy, non-blocking* approach: overflow work is permanently lost in that iteration.

**DeepSeek Harness — Reserve-before-execute slot pool:** New and cold-recovery activations must reserve a slot from the `maxActiveSubagents` pool (default 8) *before* yielding execution. Slots are only released after resource cleanup completes. Waiting descendants, pending inbox content, and stopping activations all count toward capacity ([DeepSeek Harness documentation](https://github.com/deepseek-ai/deepseek-harness/blob/687f282e8625c6b8d11ff58211a90524be2e4317/packages/subagent/subagent/README.zh.md)). This is a *non-lossy, blocking* approach where new activations are rejected until capacity frees up, but existing work continues uninterrupted.

### 4.2 Joining Mechanisms

| System | Joining Strategy | Failure Handling |
|--------|-----------------|-----------------|
| GPT Researcher | `asyncio.gather(*tasks)` then filter `None` results | If ALL branches fail, halt descent entirely |
| Open Deep Research | `asyncio.gather(*research_tasks)` on allowed calls only | Overflow calls dropped; no retry mechanism observed |
| DeepSeek Harness | Asynchronous completion notification to parent | Crashed subagent holds slot until cleanup finishes |

GPT Researcher's failure detection is notable: after gathering results, it filters out `None` values and checks if *all* branches failed. If so, it stops descent to prevent infinite work from empty goals ([GPT Researcher source](https://github.com/assafelovic/gpt-researcher/blob/3582a6841fe7dc801e2a34e34ee408641aea9bce/gpt_researcher/skills/deep_research.py)). Open Deep Research has no equivalent guard for the case where all allowed sub-researchers fail—the supervisor simply receives empty or error results and may or may not generate follow-ups in the next iteration.

## 5. How Later Work Depends on Earlier Findings

This is where the architectural differences become most consequential.

**GPT Researcher** constructs the next query by concatenating the parent's `researchGoal` and `followUpQuestions` into a single flat string: `f"Follow-up questions: {' '.join(result['followUpQuestions'])}"` ([GPT Researcher source](https://github.com/assafelovic/gpt-researcher/blob/3582a6841fe7dc801e2a34e34ee408641aea9bce/gpt_researcher/skills/deep_research.py)). This loses individual question structure and prevents targeted re-investigation of specific gaps. The dependency is *sequential and lossy*: each deeper level sees only a flattened summary of its parent's findings.

**Open Deep Research** maintains a richer dependency structure. The Research Supervisor accumulates all sub-researcher results across iterations and uses them to inform subsequent reflection and question generation. The `max_researcher_iterations` parameter (default 6) controls how many times this reflect-and-decide cycle repeats ([Open Deep Research configuration](https://github.com/langchain-ai/open_deep_research/blob/1b7d2e80db9faa586165c60e09096dbbfd483a64/src/open_deep_research/configuration.py)). The dependency is *iterative and cumulative*: each iteration sees all prior results, enabling the supervisor to identify gaps and direct new research accordingly.

**DeepSeek Harness** uses an asynchronous notification model: the parent receives a completion notification after the child's activation settles. The parent can then decide whether to delegate further work based on the child's output. The dependency is *event-driven and potentially multi-level* (up to `maxDepth`), though the default of 1 limits this to a single hop.

## 6. Evidence Required for "Dynamic Agent DAG" Classification

A "dynamic agent DAG" implies: (a) the graph structure is determined at runtime based on data, (b) nodes represent autonomous agents with their own decision loops, and (c) edges represent data dependencies that are not predetermined.

| Criterion | GPT Researcher | Open Deep Research | DeepSeek Harness |
|-----------|---------------|-------------------|-----------------|
| Runtime-determined structure | Partial (content adaptive, shape static) | Yes (supervisor decides fan-out count and topics) | Yes (delegation decisions are runtime) |
| Autonomous agent nodes | No (recursive function calls, not independent agents) | Partial (sub-researchers have their own ReAct loop bounded by `max_react_tool_calls`) | Yes (each activation is an independent agent session) |
| Non-predetermined edges | No (breadth halving is deterministic) | Yes (supervisor decides which topics to pursue next) | Yes (parent decides what to delegate based on child results) |

Based on this analysis, **Open Deep Research most closely approximates a dynamic agent DAG** among the three systems, though it is constrained to a single level of delegation (supervisor → sub-researchers), making it technically a dynamic *star* topology rather than a full DAG. **DeepSeek Harness** has the architectural capacity for a true DAG (multi-level delegation, independent agent sessions, event-driven dependencies) but is limited by the default `maxDepth=1` configuration. **GPT Researcher** is best characterized as a *static tree with adaptive content*—the DAG structure is fixed at initialization, and only the data flowing through it is dynamic.

## 7. Comparative Summary

| Dimension | GPT Researcher | Open Deep Research | DeepSeek Harness |
|-----------|---------------|-------------------|-----------------|
| **Tree shape** | Static (halving) | Dynamic (LLM-decided) | Dynamic (delegation-driven) |
| **Max parallelism** | `concurrency_limit` (semaphore) | `max_concurrent_research_units` (default 5, max 20) | `maxActiveSubagents` (default 8) |
| **Overflow handling** | Queue (semaphore blocks) | Drop (lossy truncation) | Reject (blocking reservation) |
| **Depth control** | `depth` parameter (recursive) | `max_researcher_iterations` (default 6, max 10) | `maxDepth` (default 1) |
| **Per-node tool budget** | N/A (single search per branch) | `max_react_tool_calls` (default 10, max 30) | N/A (agent-level) |
| **Joining** | `asyncio.gather` + None filter | `asyncio.gather` on allowed calls | Async completion notification |
| **Failure guard** | Halt if all branches fail | None observed | Slot held until cleanup |
| **Dependency richness** | Flat string concatenation | Cumulative supervisor context | Event-driven parent notification |

## 8. Assessment

Based on the source-level evidence, I assess that **Open Deep Research represents the most architecturally sophisticated orchestration** of the three for research-specific workloads, despite its lossy overflow strategy. Its combination of a dynamic supervisor loop, per-node ReAct tool budgets, and cumulative context accumulation creates a system where the research trajectory genuinely adapts to evidence. The truncate-and-drop overflow is a pragmatic trade-off that accepts information loss in exchange for predictable resource usage—a reasonable choice for a system where the supervisor can simply generate alternative queries in the next iteration.

**DeepSeek Harness** is the most architecturally general-purpose system, with its activation tree model supporting true multi-level delegation and independent agent lifecycles. However, its default configuration (`maxDepth=1`) effectively reduces it to a star topology similar to Open Deep Research, and its slot reservation model introduces a potential liveness concern: a crashed subagent holds its slot until cleanup completes, which could block new activations in a pool of only 8 ([DeepSeek Harness documentation](https://github.com/deepseek-ai/deepseek-harness/blob/687f282e8625c6b8d11ff58211a90524be2e4317/packages/subagent/subagent/README.zh.md)).

**GPT Researcher** is the most constrained system architecturally, but its simplicity is not without merit. The static halving strategy provides predictable resource usage, and the failure-detection guard (halting when all branches produce no results) is a practical safeguard absent from the other two systems. Its primary weakness—the flattening of follow-up questions into a single string—represents a genuine information bottleneck that limits the system's ability to perform targeted deep-dive research on specific gaps.

## References

- Assaf Elovic. (n.d.). *GPT Researcher: deep_research.py*. GitHub. [https://github.com/assafelovic/gpt-researcher/blob/3582a6841fe7dc801e2a34e34ee408641aea9bce/gpt_researcher/skills/deep_research.py](https://github.com/assafelovic/gpt-researcher/blob/3582a6841fe7dc801e2a34e34ee408641aea9bce/gpt_researcher/skills/deep_research.py)
- LangChain AI. (n.d.). *Open Deep Research: configuration.py*. GitHub. [https://github.com/langchain-ai/open_deep_research/blob/1b7d2e80db9faa586165c60e09096dbbfd483a64/src/open_deep_research/configuration.py](https://github.com/langchain-ai/open_deep_research/blob/1b7d2e80db9faa586165c60e09096dbbfd483a64/src/open_deep_research/configuration.py)
- LangChain AI. (n.d.). *Open Deep Research: deep_researcher.py*. GitHub. [https://github.com/langchain-ai/open_deep_research/blob/1b7d2e80db9faa586165c60e09096dbbfd483a64/src/open_deep_research/deep_researcher.py](https://github.com/langchain-ai/open_deep_research/blob/1b7d2e80db9faa586165c60e09096dbbfd483a64/src/open_deep_research/deep_researcher.py)
- DeepSeek AI. (n.d.). *DeepSeek Harness: Subagent README (Chinese)*. GitHub. [https://github.com/deepseek-ai/deepseek-harness/blob/687f282e8625c6b8d11ff58211a90524be2e4317/packages/subagent/subagent/README.zh.md](https://github.com/deepseek-ai/deepseek-harness/blob/687f282e8625c6b8d11ff58211a90524be2e4317/packages/subagent/subagent/README.zh.md)