"""Start a separate DSH model endpoint without resuming paused experiments."""
import json
import os
from pathlib import Path
import socket
import subprocess
import time


def main():
    root = Path('/home/Liangyijia_Hu/dsh-lab')
    previous = Path('/home/Liangyijia_Hu/harness-engine')
    metadata = json.loads((previous/'state/model.json').read_text())
    assert metadata['status'] == 'complete'
    probe = subprocess.check_output(['nvidia-smi', '--query-gpu=index,memory.used,utilization.gpu',
                                     '--format=csv,noheader,nounits'], text=True)
    for line in probe.splitlines():
        index, memory, utilization = map(int, line.split(','))
        if index in (0, 1) and (memory > 512 or utilization > 0):
            raise RuntimeError('Requested GPU is occupied: '+line)
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 18082))
    command = [str(previous/'.venv-engine/bin/vllm'), 'serve', metadata['result']['path'],
               '--host', '127.0.0.1', '--port', '18082', '--served-model-name', 'qwen27b',
               '--tensor-parallel-size', '2', '--dtype', 'bfloat16', '--language-model-only',
               '--max-model-len', '65536', '--max-num-seqs', '48', '--max-num-batched-tokens', '8192',
               '--gpu-memory-utilization', '.9', '--enable-prefix-caching', '--enable-chunked-prefill',
               '--enable-request-id-headers', '--enable-per-request-metrics', '--enable-prompt-tokens-details',
               '--kv-cache-metrics', '--kv-cache-metrics-sample', '1.0', '--reasoning-parser', 'qwen3',
               '--enable-auto-tool-choice', '--tool-call-parser', 'qwen3_xml',
               '--scheduling-policy', 'priority', '--default-chat-template-kwargs',
               json.dumps({'enable_thinking': True, 'reasoning_effort': 'low'})]
    env = {**os.environ, 'CUDA_VISIBLE_DEVICES': '0,1', 'OMP_NUM_THREADS': '1',
           'VLLM_SERVER_DEV_MODE': '1',
           'CUDA_HOME': '/usr/local/cuda-13.2', 'PATH': '/usr/local/cuda-13.2/bin:'+os.environ['PATH']}
    log_path = root/'logs/qwen-engine.log'
    with log_path.open('ab', buffering=0) as log:
        process = subprocess.Popen(command, cwd=root, env=env, stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    info = {'pid': process.pid, 'started': time.time(), 'command': command, 'gpu_before': probe,
            'log': str(log_path), 'purpose': 'Official DSH deployment and explicitly requested small E1 comparison.',
            'env_overrides': {'CUDA_VISIBLE_DEVICES': '0,1', 'OMP_NUM_THREADS': '1',
                              'VLLM_SERVER_DEV_MODE': '1', 'CUDA_HOME': '/usr/local/cuda-13.2'},
            'legacy_stop_untouched': (previous/'state/STOP').exists()}
    (root/'state/engine.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
    print(json.dumps(info, indent=2))


if __name__ == '__main__':
    main()
