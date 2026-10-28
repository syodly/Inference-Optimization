"""Verify actual local bytes against the captured ModelScope file hashes."""
import hashlib
import json
from pathlib import Path
import time

root = Path.home() / 'harness-engine'
model = json.loads((root / 'state/model_manifest.json').read_text())
expected = json.loads((root / 'state/modelscope_files.json').read_text())
started = time.time()
records = []
for entry in expected:
    if entry.get('Type') != 'blob':
        continue
    path = Path(model['path']) / entry['Path']
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(8 * 1024 * 1024), b''):
            digest.update(chunk)
    actual = digest.hexdigest()
    records.append({'path': entry['Path'], 'file_revision': entry['Revision'],
                    'bytes': path.stat().st_size, 'expected_bytes': entry['Size'],
                    'sha256': actual, 'expected_sha256': entry['Sha256'],
                    'passed': actual == entry['Sha256'] and path.stat().st_size == entry['Size']})
result = {'model_id': model['model_id'], 'started': started, 'finished': time.time(),
          'passed': all(r['passed'] for r in records), 'files': records}
(root / 'state/model_verification.json').write_text(json.dumps(result, indent=2))
print(json.dumps({'passed': result['passed'], 'files': len(records), 'seconds': time.time() - started}))
if not result['passed']:
    raise RuntimeError('Model file identity mismatch')
