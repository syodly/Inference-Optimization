// Research application on the unmodified official DSH Agent/Workflow runtime.
// All variants use identical tools, instructions and request configuration.
import { readFileSync, appendFileSync } from 'node:fs';
import { randomUUID } from 'node:crypto';
import { defineTool } from './runtime/node_modules/@deepseek-ai/dsh-tools/lib/index.js';

export const name = 'e1-research-application';
export const inject = ['tools', 'workflowEngine'];

export function apply(ctx) {
  const task = JSON.parse(readFileSync(process.env.DSH_BENCH_TASK_FILE, 'utf8'));
  const broker = process.env.DSH_BENCH_BROKER;
  const logFile = process.env.DSH_BENCH_EVENT_FILE;
  const write = (event, values = {}) => appendFileSync(logFile,
    JSON.stringify({ wall_time: Date.now() / 1000, event, task_id: task.task_id, ...values }) + '\n');
  const post = async (path, body, signal) => {
    const response = await fetch(broker + path, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body), signal,
    });
    if (!response.ok) throw new Error(`E1 broker ${path}: ${response.status} ${await response.text()}`);
    return response.json();
  };
  const output = { schema: { type: 'string' }, render: (_args, value) => [{ type: 'text', text: value }] };
  const prompts = [0, 1, 2].map(branch =>
    `Research branch ${branch}. Question: ${task.question}\n` +
    `Call bench_search exactly once with branch=${branch} and a short useful search query. ` +
    'Read all returned source text. Then finish with a concise JSON evidence report: ' +
    '{"answer_fragment":"...","facts":[{"doc_id":"...","quote":"exact source quote","inference":"..."}],"missing":"..."}. ' +
    'Use only retrieved sources. Report missing information honestly. ' +
    'Do not call research_workflow, delegate, send messages, or use other tools. Return the report as your final answer.');

  ctx.tools.register(defineTool({
    name: 'bench_search',
    description: 'Search your assigned document shard with actual BM25 and return the top three full original documents.',
    parameters: {
      branch: { type: 'integer', required: true, description: 'Assigned branch number, 0, 1 or 2.' },
      query: { type: 'string', required: true, description: 'Short query relevant to the task question.' },
    },
    output,
    async execute(args, exec) {
      const result = await post('/search', { task_id: task.task_id, agent_id: exec.agent.id, ...args }, exec.signal);
      return JSON.stringify(result);
    },
  }));
  ctx.tools.register(defineTool({
    name: 'research_workflow',
    description: 'Execute the task\'s three mandatory research branches in parallel using native DSH agents. Wait for all three complete reports. Call exactly once as the parent.',
    parameters: {}, output,
    async execute(_args, exec) {
      write('workflow_start', { parent_session: exec.agent.id });
      const run = ctx.workflowEngine.start({
        parent: exec.agent, signal: exec.signal,
        meta: { name: 'three-shard-research', description: 'Three mandatory BM25 research agents and one complete parent synthesis.' },
        script: 'return await parallel(args.prompts.map((prompt, i) => () => agent(prompt, { label: "Research shard " + i })));',
        args: { prompts }, maxTotalAgents: 3,
      });
      try {
        const result = await run.result;
        write('workflow_result', { run_id: run.id, result });
        if (result.stopReason !== 'completed') throw new Error(JSON.stringify(result));
        return JSON.stringify(result);
      } finally { await run.dispose(); }
    },
  }));

  let root;
  const stages = new Map();
  const permits = new Map();
  ctx.on('agent/created', ({ agent }) => {
    root ??= agent.id;
    agent.ctx.tools.restrict({ allow: ['bench_search', 'research_workflow'] });
    write('agent_created', { session_id: agent.id, role: agent.id === root ? 'parent' : 'child' });
  });
  ctx.on('agent/disposed', ({ agent }) => write('agent_disposed', { session_id: agent.id }));
  ctx.on('agent/request', async ({ agent, signal, turn, step }, next) => {
    const config = await next();
    const index = (stages.get(agent.id) ?? 0) + 1;
    stages.set(agent.id, index);
    const stage = agent.id === root ? (index === 1 ? 'plan' : 'synthesis') : (index === 1 ? 'query' : 'evidence');
    const call_id = randomUUID();
    const payload = { call_id, task_id: task.task_id, agent_id: agent.id, stage, turn, step };
    const cancel = () => { void post('/cancel', payload).catch(error => write('coordination_error', { error: String(error) })); };
    signal.addEventListener('abort', cancel, { once: true });
    try {
      write('model_ready', payload);
      const permit = await post('/admit', payload, signal);
      permits.set(agent.id, { ...payload, cancel, signal });
      write('model_admitted', { ...payload, ...permit });
      return { ...config, temperature: 0, maxTokens: 2048 };
    } catch (error) {
      signal.removeEventListener('abort', cancel);
      cancel();
      throw error;
    }
  });
  const release = agent => {
    const permit = permits.get(agent.id);
    if (!permit) return;
    permits.delete(agent.id);
    permit.signal.removeEventListener('abort', permit.cancel);
    const { signal, cancel, ...payload } = permit;
    write('model_finished', payload);
    void post('/release', payload).catch(error => write('coordination_error', { error: String(error) }));
  };
  ctx.on('agent/assistant-stream', ({ agent, frame }) => { if (frame.type === 'end') release(agent); });
  ctx.on('agent/error', ({ agent, error }) => { release(agent); write('agent_error', { session_id: agent.id, error: String(error) }); });
  ctx.on('workflow/agent-start', (run, member) => write('workflow_agent_start', { run, member }));
  ctx.on('workflow/agent-end', (run, member) => write('workflow_agent_end', { run, member }));
}
