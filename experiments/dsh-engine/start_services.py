"""Start the isolated observer and official DSH Web host, after Qwen is healthy."""
import json
from pathlib import Path
import shutil
import socket
import subprocess
import urllib.request


ROOT = Path('/home/Liangyijia_Hu/dsh-lab')


def start(name, port, command):
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', port))
    with (ROOT/'logs'/f'{name}.log').open('ab', buffering=0) as log:
        process = subprocess.Popen(command, cwd=ROOT/'workspaces', stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    (ROOT/'state'/f'{name}.json').write_text(json.dumps(
        {'pid': process.pid, 'command': command}, indent=2)+'\n', encoding='utf-8')
    print(name, 'pid', process.pid, 'port', port)


def main():
    for name in ['home', 'logs', 'state', 'workspaces']:
        (ROOT/name).mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen('http://127.0.0.1:18082/health', timeout=10) as response:
        assert response.status == 200
    node = ROOT/'toolchain/node-v24.22.2-linux-x64/bin'
    wrapper = ROOT/'dsh'
    wrapper.write_text('#!/bin/sh\n'
                       f'export PATH="{node}:$PATH"\n'
                       f'export DSH_HOME="{ROOT}/home"\n'
                       'export DSH_QWEN_API_KEY="local-qwen-no-auth"\n'
                       f'exec "{ROOT}/runtime/node_modules/.bin/dsh" "$@"\n', encoding='utf-8')
    wrapper.chmod(0o755)
    for profile in ['web', 'headless']:
        destination = ROOT/'home/profiles'/profile/'cordis.patch.yml'
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and destination.read_bytes() != (ROOT/'qwen.patch.yml').read_bytes():
            raise RuntimeError('Profile has local changes: '+str(destination))
        shutil.copy2(ROOT/'qwen.patch.yml', destination)
    # Check both listeners before starting either service.
    for port in [18083, 13080]:
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', port))
    start('observer', 18083, ['python3', str(ROOT/'observe_api.py')])
    start('web', 13080, [str(wrapper), 'web', '--host', '127.0.0.1', '--port', '13080', '--no-open'])


if __name__ == '__main__':
    main()
