#!/usr/bin/env python3
"""Build a local static tree from a pinned Release plus repository overrides.

This helper reads GitHub and writes only the requested local output directory.
It never commits, pushes, grants access, or changes a remote repository.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import stat
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ('projects', 'assets', 'scripts', 'index.html', 'projects.json',
           'README.md', 'AGENTS.md', 'MIGRATION.md', '.nojekyll', 'source-archive.json')

def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()

def safe_path(name):
    if not isinstance(name, str) or not name or '\\' in name or '\x00' in name:
        raise ValueError('Unsafe source path: ' + repr(name))
    value = PurePosixPath(name)
    if not value.parts or value.is_absolute() or '..' in value.parts or any(x in value.parts for x in ('.git', '.env', '.openai')):
        raise ValueError('Unsafe source path: ' + name)
    return value

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--archive', type=Path, help='Use an already downloaded source archive; the checksum is always verified.')
    args = parser.parse_args()
    output = args.output.resolve()
    if output == ROOT or ROOT in output.parents or output in ROOT.parents:
        raise SystemExit('Use an output directory outside the repository checkout.')
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise SystemExit('The output must be an empty directory or a path that does not yet exist.')
    config = json.loads((ROOT / 'source-archive.json').read_text())
    # Validate deletions before extraction; a blank or dot path must never target
    # the entire materialized tree.
    excludes = [safe_path(name) for name in config.get('exclude_paths', [])]
    for name in OVERLAY:
        source = ROOT / name
        if source.is_symlink() or (source.is_dir() and any(p.is_symlink() for p in source.rglob('*'))):
            raise SystemExit('Repository overrides must not contain symlinks: ' + name)
    with tempfile.TemporaryDirectory(prefix='postai-labs-') as scratch:
        archive = args.archive or Path(scratch) / 'sources.zip'
        if args.archive is None:
            request = urllib.request.Request(config['url'], headers={'User-Agent': 'PostAI-Labs-Materializer/1.0'})
            with urllib.request.urlopen(request, timeout=60) as source, archive.open('wb') as target:
                shutil.copyfileobj(source, target, 1024 * 1024)
        if archive.stat().st_size != config['bytes'] or digest(archive) != config['sha256']:
            raise SystemExit('Source archive size or SHA-256 does not match source-archive.json.')
        output.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as source:
            for item in source.infolist():
                relative = safe_path(item.filename)
                if stat.S_ISLNK(item.external_attr >> 16):
                    raise SystemExit('Source archive contains a symlink.')
                if relative.parts[0] == '.github':
                    continue
                source.extract(item, output)
        for name in OVERLAY:
            source, target = ROOT / name, output / name
            if source.is_dir():
                shutil.copytree(source, target, dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns('.git', '.env', '.openai', '__pycache__', '*.pyc', 'node_modules'))
            elif source.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        for name in excludes:
            target = output / name
            if target.is_dir():
                shutil.rmtree(target)
            elif target.exists():
                target.unlink()
    projects = json.loads((output / 'projects.json').read_text())['projects']
    print(f'Materialized {len(projects)} catalogue entries at {output}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
