"""Engine-side admission gateway with the same observed Session/stage information.

This is an explicit strong placement baseline, not a modification or reproduction
of vLLM's token scheduler. The harness retains tools and dependencies; the broker
can defer first model requests, retain logical Session claims across tools, order
READY requests, and read the same real engine metrics. No gold or future arrivals.
"""
import argparse
from contextlib import asynccontextmanager
import asyncio
import hashlib
import json
from pathlib import Path
import time

from fastapi import FastAPI, Request
from fastapi.responses import Response, StreamingResponse
import uvicorn

from engine import Engine, Journal
from scheduler import Controller


def create_app(args):
    journal = Journal(args.out)
    (args.out/'config.json').write_text(json.dumps({**vars(args), 'out': str(args.out),
        'source_sha256': {name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
                          for name in ['broker.py', 'scheduler.py', 'engine.py']},
        'information': 'Root, Session and stage are encoded in the existing X-Request-Id. Three mandatory children are application-declared. No tool return timestamps or hidden labels.',
        'scope': 'Engine-side admission gateway with equivalent controls for these policies; not the native vLLM token scheduler.'}, indent=2), encoding='utf-8')
    engine = Engine(args.upstream, 'qwen27b', journal, True, 'qwen', 'low')
    controller = Controller(args.policy, args.cap, engine, journal, args.session_cap,
                            args.starvation_seconds, args.history_budget_tokens, 1024)
    stop = asyncio.Event()
    registered = set()

    @asynccontextmanager
    async def lifespan(app):
        await engine.health(); await engine.sample()
        schedule = asyncio.create_task(controller.loop())
        poll = asyncio.create_task(engine.poll(stop))
        try:
            yield
        finally:
            controller.close(); stop.set()
            await schedule; await poll; await engine.close(); journal.close()

    app = FastAPI(lifespan=lifespan)

    async def forward(path, method='GET'):
        result = await engine.client.request(method, engine.url+path)
        return Response(content=result.content, status_code=result.status_code,
                        media_type=result.headers.get('content-type', 'application/json'))

    @app.get('/health')
    async def health():
        return await forward('/health')

    @app.get('/v1/models')
    async def models():
        return await forward('/v1/models')

    @app.get('/metrics')
    async def metrics():
        return await forward('/metrics')

    @app.post('/reset_prefix_cache')
    async def reset():
        if controller.running or controller.pending or controller.history_claims:
            raise RuntimeError('Do not reset a serving broker with unfinished requests')
        return await forward('/reset_prefix_cache', 'POST')

    @app.get('/harness/status')
    async def status():
        return {'policy': controller.policy, 'running': controller.running,
                'pending': len(controller.pending), 'sessions': len(controller.sessions),
                'claimed_history_tokens': sum(controller.history_claims.values()),
                'observed_engine': engine.latest}

    @app.post('/v1/chat/completions')
    async def chat(request: Request):
        payload = await request.json()
        call_id = request.headers['x-request-id']
        root, local_session, stage = call_id.rsplit('-', 2)
        node = root+'/'+local_session
        if stage not in ['query', 'draft', 'evidence', 'synthesis']:
            raise ValueError('Unknown application-declared stage')
        controller.remaining.setdefault(root, args.branches)
        journal.write('requests', call_id=call_id, root_id=root, node_id=node, stage=stage, payload=payload)
        if stage == 'query':
            if node in registered:
                raise ValueError('Duplicate first request for Session: '+node)
            registered.add(node)
            await controller.open_session(root, node)
        measured = 0
        if args.policy in ['size_return', 'history_budget', 'history_pressure']:
            measured = await engine.prompt_tokens(payload['messages'], payload['chat_template_kwargs']['enable_thinking'],
                                                  root_id=root, node_id=node, stage=stage)
        await controller.admit(root, node, stage, measured)
        start = time.monotonic()
        journal.write('events', event='broker_upstream_submit', call_id=call_id, root_id=root, node_id=node, stage=stage)
        try:
            upstream_request = engine.client.build_request('POST', engine.url+'/v1/chat/completions', json=payload,
                                                           headers={'X-Request-Id': call_id})
            result = await engine.client.send(upstream_request, stream=True)
            result.raise_for_status()
        except Exception:
            controller.release()
            raise

        async def stream():
            usage, error, completed = {}, None, False

            def complete():
                nonlocal completed
                if completed:
                    return
                if not usage:
                    raise RuntimeError('Upstream stream ended without required usage accounting')
                controller.observe_completion(node, stage, usage)
                if measured:
                    journal.write('events', event='prompt_measurement_check', root_id=root, node_id=node,
                                  stage=stage, measured_prompt_tokens=measured,
                                  actual_prompt_tokens=usage.get('prompt_tokens'), matches=measured == usage.get('prompt_tokens'))
                if stage == 'evidence':
                    controller.remaining[root] -= 1
                    controller.close_session(root, node)
                completed = True

            try:
                async for line in result.aiter_lines():
                    if line.startswith('data: ') and line[6:] != '[DONE]':
                        packet = json.loads(line[6:])
                        if packet.get('usage'): usage = packet['usage']
                        if packet.get('error'): error = packet['error']
                    if line == 'data: [DONE]':
                        # Clients can close immediately at DONE. Commit the logical
                        # completion before yielding it, including Session claims.
                        complete()
                    yield (line+'\n').encode('utf-8')
                complete()
            except Exception as exc:
                error = repr(exc)
                raise
            finally:
                controller.release()
                journal.write('responses', call_id=call_id, root_id=root, node_id=node, stage=stage,
                              usage=usage, error=error, completed=completed, upstream_duration=time.monotonic()-start)
                await result.aclose()

        return StreamingResponse(stream(), media_type='text/event-stream',
                                 headers={'x-request-id': result.headers.get('x-request-id', call_id)})

    return app


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--upstream', default='http://127.0.0.1:18081')
    ap.add_argument('--port', type=int, default=18082)
    ap.add_argument('--policy', choices=['native', 'return_priority', 'size_return', 'session_return', 'history_budget', 'history_pressure'], default='return_priority')
    ap.add_argument('--cap', type=int, default=24)
    ap.add_argument('--session-cap', type=int, default=18)
    ap.add_argument('--branches', type=int, default=3)
    ap.add_argument('--starvation-seconds', type=float, default=120)
    ap.add_argument('--history-budget-tokens', type=int, default=200000)
    args = ap.parse_args()
    uvicorn.run(create_app(args), host='127.0.0.1', port=args.port, log_level='warning')
