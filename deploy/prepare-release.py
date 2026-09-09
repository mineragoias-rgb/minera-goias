#!/usr/bin/env python3
"""Installed as a root-owned script; executed as the unprivileged project user."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import time
import urllib.request

BASE = Path('/srv/minera-goias')
REPO = BASE / 'repository'

def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)

if not REPO.exists():
    run('git', 'clone', '--no-checkout', '--single-branch', '--branch', 'main',
        'https://github.com/mineragoias-rgb/minera-goias.git', str(REPO))
run('git', '-C', str(REPO), 'fetch', '--prune', 'origin', 'main')
sha = subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'origin/main'], text=True).strip()
assert len(sha) == 40 and all(c in '0123456789abcdef' for c in sha)
target = BASE / 'releases' / sha
current = BASE / 'current'
if current.is_symlink() and current.resolve() == target:
    print('Already deployed', sha)
    raise SystemExit(0)
if target.exists():
    shutil.rmtree(target)
target.mkdir()
archive = BASE / 'source.tar'
run('git', '-C', str(REPO), 'archive', '-o', str(archive), sha)
with tarfile.open(archive) as tf:
    members = tf.getmembers()
    for member in members:
        path = Path(member.name)
        if path.is_absolute() or '..' in path.parts or not (member.isfile() or member.isdir()):
            raise RuntimeError('Only regular repository files/directories are accepted')
    tf.extractall(target, members=members)
archive.unlink()
backend = target / 'Squad 3' / 'backend'
venv = target / '.venv'
run('python3', '-m', 'venv', str(venv))
requirements = target / 'deploy' / 'requirements-vps.txt'
if not requirements.is_file():
    raise RuntimeError('Missing deploy/requirements-vps.txt')
run(str(venv / 'bin/python'), '-m', 'pip', 'install', '--disable-pip-version-check',
    '--only-binary=:all:', '-r', str(requirements))
if not (target / 'public' / 'index.html').is_file():
    raise RuntimeError('Missing public/index.html')
run(str(venv / 'bin/python'), '-m', 'compileall', '-q', str(backend))
log = BASE / 'shared' / 'candidate.log'
with log.open('w') as output:
    proc = subprocess.Popen([str(venv / 'bin/python'), '-m', 'uvicorn', 'main:app',
                             '--host', '127.0.0.1', '--port', '18142'],
                            cwd=backend, stdout=output, stderr=subprocess.STDOUT)
    try:
        for _ in range(45):
            if proc.poll() is not None:
                raise RuntimeError('Candidate API exited; see candidate.log')
            try:
                for route in ['projetos', 'projecoes', 'fontes']:
                    with urllib.request.urlopen('http://127.0.0.1:18142/api/' + route, timeout=5) as response:
                        if not isinstance(json.load(response), list):
                            raise RuntimeError('Invalid API response')
                break
            except Exception:
                time.sleep(1)
        else:
            raise RuntimeError('Candidate health check failed; current release preserved')
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
next_link = BASE / 'next'
next_link.unlink(missing_ok=True)
next_link.symlink_to(target)
os.replace(next_link, current)
print('Prepared and verified', sha)
