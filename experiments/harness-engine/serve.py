"""Start only this project's server, preserving command, identity and resource evidence."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import time


root = Path.home() / 'harness-engine'
ap = argparse.ArgumentParser()
ap.add_argument('--mode', choices=['eager', 'graph'], default='graph')
ap.add_argument('--max-model-len', type=int, default=65536)
args = ap.parse_args()
state = json.loads((root / 'state/model.json').read_text())
if state['status'] != 'complete':
    raise RuntimeError('Model download incomplete')
model_path = state['result']['path']
probe = subprocess.run(['nvidia-smi', '--query-gpu=index,memory.used,utilization.gpu', '--format=csv,noheader,nounits'],
                       capture_output=True, text=True, check=True).stdout
for line in probe.splitlines():
    index, memory, utilization = map(int, line.split(','))
    if index in [0, 1] and memory > 512:
        raise RuntimeError('GPU already occupied: ' + line)
with socket.socket() as s:
    s.bind(('127.0.0.1', 18081))
command = [str(root / '.venv-engine/bin/vllm'), 'serve', model_path,
           '--host', '127.0.0.1', '--port', '18081', '--served-model-name', 'qwen27b',
           '--tensor-parallel-size', '2', '--dtype', 'bfloat16', '--language-model-only',
           '--max-model-len', str(args.max_model_len), '--max-num-seqs', '48', '--max-num-batched-tokens', '8192',
           '--gpu-memory-utilization', '.9', '--enable-prefix-caching', '--enable-chunked-prefill',
           '--enable-request-id-headers', '--enable-per-request-metrics', '--enable-prompt-tokens-details',
           '--kv-cache-metrics', '--kv-cache-metrics-sample', '1.0',
           '--reasoning-parser', 'qwen3', '--scheduling-policy', 'priority']
if args.mode == 'eager':
    command.append('--enforce-eager')
overrides = {'CUDA_VISIBLE_DEVICES': '0,1', 'OMP_NUM_THREADS': '1', 'VLLM_SERVER_DEV_MODE': '1',
             'CUDA_HOME': '/usr/local/cuda-13.2', 'PATH': '/usr/local/cuda-13.2/bin:' + os.environ['PATH']}
env = dict(os.environ, **overrides)
log_path = root / f'logs/engine-{args.mode}.log'
with log_path.open('ab', buffering=0) as log:
    proc = subprocess.Popen(command, cwd=root, env=env, stdin=subprocess.DEVNULL,
                            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
metadata = {'pid': proc.pid, 'started': time.time(), 'command': command, 'gpu_probe': probe,
            'env_overrides': overrides,
            'model_path': model_path, 'log': str(log_path),
            'mode': args.mode}
(root / 'state/server.json').write_text(json.dumps(metadata, indent=2))
print(json.dumps(metadata, indent=2))
