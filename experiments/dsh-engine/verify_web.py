"""Verify the deployed official Web UI through a temporary SSH tunnel.

The Web login token stays in memory and is never written to the report.
This does not send a model prompt or resume research experiments.
"""
import json
from pathlib import Path
import re
import socket
import subprocess
import time
from urllib.parse import urlsplit, urlunsplit


def main():
    from playwright.sync_api import sync_playwright

    root = Path(__file__).resolve().parent
    output = root/'evidence/deployment-20261029/web'
    output.mkdir(parents=True, exist_ok=True)
    remote = "from pathlib import Path; import re; s=Path('/home/Liangyijia_Hu/dsh-lab/logs/web.log').read_text(); print(re.findall(r'http://127[.]0[.]0[.]1:13080/[^\\s]+',s)[-1])"
    result = subprocess.run(['ssh', 'songprojgpu1', 'python3 -'], input=remote,
                            text=True, capture_output=True, check=True)
    login = urlsplit(result.stdout.strip())
    assert login.query.startswith('token=')
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    command = ['ssh', '-N', '-o', 'ExitOnForwardFailure=yes', '-o', 'ServerAliveInterval=30',
               '-L', f'{port}:127.0.0.1:13080', 'songprojgpu1']
    tunnel = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL,
                              creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    errors = []
    try:
        for _ in range(40):
            if tunnel.poll() is not None:
                raise RuntimeError('SSH tunnel exited')
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=.25):
                    break
            except OSError:
                time.sleep(.25)
        url = urlunsplit((login.scheme, f'127.0.0.1:{port}', login.path, login.query, ''))
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
                headless=True)
            page = browser.new_page(viewport={'width': 1440, 'height': 1000})
            page.on('pageerror', lambda error: errors.append(
                re.sub(r'([?&]token=)[A-Za-z0-9_-]+', r'\1<redacted>', str(error))))
            response = page.goto(url, wait_until='networkidle', timeout=45000)
            page.wait_for_function("document.body.innerText.trim().length > 100", timeout=15000)
            # The server exchanges the process token for a browser cookie and redirects.
            assert not urlsplit(page.url).query
            continuation = page.get_by_role('button', name='继续', exact=True)
            if continuation.count():
                continuation.click()
                page.wait_for_function("!document.body.innerText.includes('预览版说明')")
            body = page.locator('body').inner_text()
            assert 'Qwen3.8-27B BF16' in body
            page.screenshot(path=str(output/'official-dsh-web.png'), full_page=True)
            report = {'http_status': response.status, 'title': page.title(),
                      'token_removed_after_login': True, 'body_text_excerpt': body[:2500],
                      'page_errors': errors, 'temporary_ssh_tunnel_closed_after_check': True,
                      'model_prompt_sent_by_check': False}
            (output/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n',
                                             encoding='utf-8')
            browser.close()
            assert response.status == 200
            assert not errors, errors
        print(json.dumps(report, ensure_ascii=False))
    finally:
        tunnel.terminate()
        tunnel.wait(timeout=10)


if __name__ == '__main__':
    main()
