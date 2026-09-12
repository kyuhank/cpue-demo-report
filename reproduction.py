"""Attach the synthetic snapshot and a verified replay package to a report."""
import base64
import hashlib
import io
import json
from pathlib import Path
import zipfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(data, mime):
    return 'data:' + mime + ';base64,' + base64.b64encode(data).decode()


def build(root, out, manifest):
    source = out / 'source.sqlite'
    if not source.exists():
        import os
        source = root / os.getenv('TOY_SOURCE_DATABASE', 'data/toy-fishery.sqlite')
    snapshot = source.read_bytes()
    if sha(snapshot) != manifest['source_sha256']:
        raise ValueError('The report snapshot does not match the analysed data')

    files = {'data/toy-fishery.sqlite': snapshot}
    for name in ('modules.lock.json', 'module-versions.json'):
        if (root / name).exists():
            files[name] = (root / name).read_bytes()
    if manifest.get('data_release'):
        files['data/toy-fishery.release.json'] = (json.dumps(manifest['data_release'], indent=2) + '\n').encode()
    for path in sorted((root / 'pipeline').iterdir()):
        if path.suffix in ('.py', '.sql', '.json'):
            files[str(path.relative_to(root))] = path.read_bytes()
    for name in ('run_stage.py', 'workflow_plan.py', 'reproduce.py'):
        path = root / 'scripts' / name
        if name == 'reproduce.py' and not path.exists():
            path = root / name
        if path.exists():
            files['reproduce.py' if name == 'reproduce.py' else 'scripts/' + name] = path.read_bytes()
    if (root / 'run.py').exists():
        files['run.py'] = (root / 'run.py').read_bytes()

    settings = {k: v for k, v in manifest['configuration']['stage_settings'].items() if v}
    files['config/stages.json'] = (json.dumps(settings, indent=2) + '\n').encode()
    manifest['stage_records'] = {}
    for key in manifest['stages']:
        record = root / 'stages' / key / 'record.json'
        if key != 'report' and record.exists():
            manifest['stage_records'][key] = json.loads(record.read_text())
            files['records/' + key + '.json'] = record.read_bytes()
    references = {}
    for path in sorted(out.iterdir()):
        if path.suffix in ('.csv', '.svg'):
            files['reference/' + path.name] = path.read_bytes()
            references[path.name] = sha(path.read_bytes())
    manifest['reproduction'] = {
        'snapshot': {'file': 'data/toy-fishery.sqlite', 'sha256': sha(snapshot), 'bytes': len(snapshot)},
        'code_files': {name: sha(value) for name, value in files.items()
                       if name.startswith(('pipeline/', 'scripts/')) or name in ('run.py', 'reproduce.py')},
        'reference_outputs': references,
        'entrypoint': 'python3 reproduce.py' if 'reproduce.py' in files else 'python3 run.py',
        'container_image': manifest.get('container_image'),
        'module_sources': manifest.get('workflow_plan', {}).get('module_sources', {}),
        'scope': 'Exact synthetic data, analysis source, settings and reference results. The container image is identified separately by digest.',
    }
    provenance = (json.dumps(manifest, indent=2) + '\n').encode()
    files['provenance.json'] = provenance
    files['README.txt'] = (
        'Synthetic CPUE workflow: saved report inputs and code.\n\n'
        'Run: ' + manifest['reproduction']['entrypoint'] + '\n'
        'The replay uses the recorded container when available, with network access disabled.\n'
        'It recalculates the analyses and checks their CSV/SVG outputs against this report.\n'
        'Python and Docker must be installed; the pinned image must be available to Docker.\n'
        + ('For a native Python comparison: python3 reproduce.py --native\n' if 'reproduce.py' in files else '') +
        'Code and data identities are in provenance.json. File integrity is in SHA256SUMS.json.\n'
        'The container image itself is not embedded. Keep its recorded digest available.\n'
    ).encode()
    files['SHA256SUMS.json'] = (json.dumps({name: sha(value) for name, value in files.items()}, indent=2) + '\n').encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, value in files.items():
            archive.writestr(name, value)
    package = buffer.getvalue()
    return {
        'snapshot': encoded(snapshot, 'application/vnd.sqlite3'),
        'provenance': encoded(provenance, 'application/json'),
        'package': encoded(package, 'application/zip'),
        'package_sha256': sha(package),
        'size_kb': round(len(package) / 1024),
    }
