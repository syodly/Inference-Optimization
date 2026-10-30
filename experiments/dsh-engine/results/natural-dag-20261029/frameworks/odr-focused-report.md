

# Audit: Child Execution Spawning in Open Deep Research, GPT Researcher, and DeepSeek Harness

## Status: Awaiting Source Excerpts

This audit cannot be completed with the evidence currently available. The research brief requires auditing a specific claim about child execution creation in three systems using **supplied official source excerpts**. No such excerpts have been provided at this time.

Per the brief's explicit instruction, this report states the evidence gap rather than filling it with inference from public documentation or general knowledge.

## What Is Required to Proceed

To complete the audit across the four specified dimensions, the following excerpts are needed:

### 1. Trigger or Mechanism for Child Execution Spawning

Source material (code, documentation, or API reference) showing:

- **Open Deep Research:** The logic or prompt that determines when a new subtask or sub-query is generated during a research run.
- **GPT Researcher:** The mechanism that spawns sub-queries from a parent task (e.g., the planning phase, a decomposition step, or a conditional branch).
- **DeepSeek Harness:** The delegation logic showing when and how a parent execution spawns child work units, and under what conditions delegation is optional versus mandatory.

### 2. Creator of the Work

Excerpts identifying whether child executions are created by:

- An orchestrator loop (deterministic code),
- A model call (the LLM decides to decompose),
- A user action (manual splitting), or
- A configuration flag (e.g., a parameter that enables or disables sub-task generation).

### 3. Sequential Dependency vs. Independent Parallelism

Material showing whether:

- Later child executions consume the outputs of earlier ones (indicating sequential dependency), or
- All child executions are generated upfront and run independently (indicating parallelism with no inter-child data flow).

### 4. Concurrency Cap vs. Total Work Volume

Documentation or code that distinguishes:

- A **concurrency cap** (maximum number of child executions running simultaneously at any given moment), from
- The **total work volume** (the aggregate number of child executions that will ultimately be created over the lifetime of a run).

## Evidence Gap Statement

No official source excerpts have been supplied. Without them, no factual claims can be made about the internal spawning logic of any of the three systems. Any description of their behavior based solely on public READMEs, blog posts, or general knowledge would constitute the kind of speculation the brief explicitly prohibits.

## Next Step

Provide the official source excerpts (code files, configuration schemas, API documentation, or architectural notes) for each of the three systems. Once supplied, the audit will map each excerpt to the four dimensions above and produce a structured comparison with direct citations.

### Sources

No sources are cited in this report. The audit is pending the user-supplied excerpts specified in the research brief.