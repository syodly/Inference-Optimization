// Observe native execution. No task, tools, delegation counts or dispatch policy are injected.
import { appendFileSync } from 'node:fs';
import { performance } from 'node:perf_hooks';

export const name = 'natural-dag-observer';
export const inject = ['agents', 'sessions', 'tools'];

export function apply(ctx) {
  const origin = performance.now();
  const write = (event, values = {}) => appendFileSync(process.env.DSH_DAG_EVENT_FILE,
    JSON.stringify({ event, wall_time: Date.now() / 1000,
      process_elapsed_seconds: (performance.now() - origin) / 1000, ...values }) + '\n');
  ctx.on('session/event', (session, record) => write('session_event', { session_id: session.id, record }));
  ctx.on('agent/created', ({ agent, source }) => write('agent_created', {
    session_id: agent.id, source, header: agent.session.header,
  }));
  ctx.on('agent/disposed', ({ agent }) => write('agent_disposed', { session_id: agent.id }));
  ctx.on('agent/request', async ({ agent, turn, step }, next) => {
    const config = await next();
    write('model_request_ready', { session_id: agent.id, turn, step, config });
    return { ...config, temperature: 0, maxTokens: Number(process.env.DSH_DAG_MAX_TOKENS || 4096) };
  });
  ctx.on('agent/assistant-stream', ({ agent, frame }) => {
    if (frame.type !== 'chunk' || ['tool-call-delta', 'block-end', 'finish'].includes(frame.chunk.type)) {
      write('assistant_frame', { session_id: agent.id, frame });
    }
  });
  ctx.on('agent/error', ({ agent, error }) => write('agent_error', {
    session_id: agent.id, error: String(error),
  }));
  ctx.on('tools/execute', async (exec, next) => {
    write('tool_start', { session_id: exec.agent?.id, call_id: exec.callId,
      root_call_id: exec.rootCallId, tool: exec.name, arguments: exec.arguments });
    try {
      const result = await next();
      write('tool_end', { session_id: exec.agent?.id, call_id: exec.callId, tool: exec.name,
        result: { isError: result.isError, content: result.content, value: result.value } });
      return result;
    } catch (error) {
      write('tool_throw', { session_id: exec.agent?.id, call_id: exec.callId,
        tool: exec.name, error: String(error) });
      throw error;
    }
  });
  for (const event of ['subagent/start', 'subagent/end']) {
    ctx.on(event, info => write(event, { info }));
  }
  for (const event of ['workflow/start', 'workflow/end', 'workflow/phase', 'workflow/log',
    'workflow/agent-start', 'workflow/agent-end']) {
    ctx.on(event, (info, detail) => write(event, { info, detail }));
  }
}
