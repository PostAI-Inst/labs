#!/usr/bin/env python3
"""Audit the Labs catalogue and static local dependencies without third-party packages."""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import html.parser
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[1]
ID = re.compile(r'^[a-z0-9][a-z0-9-]*$')
CSS_URL = re.compile(r'''url\(\s*(['"]?)(.*?)\1\s*\)''', re.I)
CSS_IMPORT = re.compile(r'''@import\s+['"]([^'"]+)['"]''', re.I)
JS_IMPORT = re.compile(r'''(?:\bimport\s+(?:[^'";]*?\s+from\s*)?|\bexport\s+[^'";]*?\s+from\s*|\bimport\s*\()\s*['"]([^'"]+)['"]''')
SKIP_SCHEMES = {'http', 'https', 'data', 'mailto', 'tel', 'javascript', 'blob', 'about'}
RESERVED_IDS = {'catalog', 'project-grid', 'project-search', 'project-status', 'project-data', 'result-count', 'empty-state', 'reset-filters', 'empty-reset', 'hero-title', 'featured-title', 'catalog-title'}


class References(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs = []
        self.base = ''
        self.css = []
        self.in_style = False
        self.in_script = False
        self.js = []
        self.is_module = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'base':
            self.base = attrs.get('href', '')
        if tag == 'style':
            self.in_style = True
        if tag == 'script':
            self.in_script = True
            self.is_module = attrs.get('type') == 'module'
        for attribute in ('src', 'poster'):
            if attrs.get(attribute):
                self.refs.append((attrs[attribute], f'{tag}[{attribute}]', self.getpos()[0]))
        if tag in ('a', 'link', 'area') and attrs.get('href'):
            self.refs.append((attrs['href'], f'{tag}[href]', self.getpos()[0]))
        if tag == 'object' and attrs.get('data'):
            self.refs.append((attrs['data'], 'object[data]', self.getpos()[0]))
        if attrs.get('style'):
            self.css.append(attrs['style'])
        srcset = attrs.get('srcset', '')
        if srcset and 'data:' not in srcset:
            for candidate in srcset.split(','):
                parts = candidate.strip().split()
                if parts:
                    self.refs.append((parts[0], f'{tag}[srcset]', self.getpos()[0]))

    def handle_endtag(self, tag):
        if tag == 'style':
            self.in_style = False
        if tag == 'script':
            self.in_script = False
            self.is_module = False

    def handle_data(self, data):
        if self.in_style:
            self.css.append(data)
        if self.in_script and self.is_module:
            self.js.append(data)


def audit(root, manifest):
    errors, warnings = [], []
    external = set()
    visited = set()
    local_entries = set()
    auxiliary = set()
    missing_seen = set()
    dependency_count = 0

    def issue(bucket, code, message, **extra):
        bucket.append({'code': code, 'message': message, **extra})

    def relative(path):
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            return str(path)

    try:
        data = json.loads(manifest.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        return {'ok': False, 'errors': [{'code': 'manifest', 'message': str(exc)}], 'warnings': [], 'counts': {}}
    if data.get('schema_version') != 1:
        issue(errors, 'schema_version', 'projects.json must declare schema_version: 1.')
    projects = data.get('projects', [])
    categories = data.get('categories', [])
    if not isinstance(projects, list) or not isinstance(categories, list):
        issue(errors, 'manifest_shape', 'projects and categories must be arrays.')
        return {'ok': False, 'errors': errors, 'warnings': warnings, 'counts': {}}
    category_ids = [c.get('id') for c in categories if isinstance(c, dict) and isinstance(c.get('id'), str)]
    if len(category_ids) != len(categories):
        issue(errors, 'category_shape', 'Every category must have a string id.')
    for category_id, count in collections.Counter(category_ids).items():
        if count > 1:
            issue(errors, 'duplicate_category', f'Duplicate category id: {category_id}')
    category_set = set(category_ids)
    ids, entries = set(), set()
    base_path = data.get('base_path', '/labs/').rstrip('/') + '/'

    def resolve_ref(source, target, context='', line=None, base=''):
        nonlocal dependency_count
        target = str(target).strip()
        if not target or target.startswith('#'):
            return None
        if '{{' in target or '${' in target or '<%' in target:
            issue(warnings, 'dynamic_reference', 'Dynamic reference requires runtime verification.', source=relative(source), target=target, context=context)
            return None
        try:
            parsed = urlsplit(target)
        except ValueError as exc:
            issue(errors, 'invalid_reference', str(exc), source=relative(source), target=target)
            return None
        if parsed.scheme in ('http', 'https') or target.startswith('//'):
            external.add(target)
            if parsed.scheme == 'http' and context != 'a[href]':
                issue(warnings, 'mixed_content', 'HTTP resource may be blocked on HTTPS.', source=relative(source), target=target)
            return None
        if parsed.scheme in SKIP_SCHEMES:
            return None
        if parsed.scheme:
            issue(errors, 'unsupported_reference', 'Unsupported or nonportable URL.', source=relative(source), target=target, context=context)
            return None
        if target.startswith('sandbox:') or '/mnt/data/' in target:
            issue(errors, 'temporary_reference', 'A temporary workspace link cannot be published.', source=relative(source), target=target)
            return None
        if base:
            combined = urljoin(base, target)
            if combined != target:
                return resolve_ref(source, combined, context, line)
        path = unquote(parsed.path)
        if not path:
            return None
        if path.startswith('/'):
            path = path[len(base_path):] if path.startswith(base_path) else path.lstrip('/')
            candidate = (root / path).resolve()
        else:
            candidate = (source.parent / path).resolve()
        if not candidate.is_relative_to(root):
            issue(errors, 'outside_repository', 'Local reference leaves the repository.', source=relative(source), target=target, context=context)
            return None
        dependency_count += 1
        if candidate.is_dir():
            candidate = candidate / 'index.html'
        if not candidate.is_file():
            signature = (relative(source), target)
            if signature not in missing_seen:
                missing_seen.add(signature)
                issue(errors, 'missing_dependency', 'Referenced local file does not exist.', source=relative(source), target=target, resolved=relative(candidate), context=context, line=line)
            return None
        return candidate

    pending = []
    for project in projects:
        if not isinstance(project, dict):
            issue(errors, 'project_shape', 'Every project must be an object.')
            continue
        project_id = project.get('id', '')
        if not isinstance(project_id, str) or not ID.match(project_id) or project_id in RESERVED_IDS:
            issue(errors, 'project_id', f'Invalid or reserved project id: {project_id!r}')
            if not isinstance(project_id, str):
                continue
        if project_id in ids:
            issue(errors, 'duplicate_id', f'Duplicate project id: {project_id}')
        ids.add(project_id)
        for field in ('title', 'description', 'entry', 'category', 'updated_at'):
            if not isinstance(project.get(field), str) or not project.get(field):
                issue(errors, 'required_field', f'{project_id}: missing or invalid {field}.')
        if not isinstance(project.get('category'), str) or project.get('category') not in category_set:
            issue(errors, 'unknown_category', f'{project_id}: unknown category {project.get("category")!r}.')
        if project.get('status', 'ready') not in ('ready', 'external', 'limited'):
            issue(errors, 'invalid_status', f'{project_id}: status must be ready, external or limited.')
        if not isinstance(project.get('tags', []), list):
            issue(errors, 'invalid_tags', f'{project_id}: tags must be an array.')
        try:
            dt.date.fromisoformat(project.get('updated_at', ''))
        except (TypeError, ValueError):
            issue(errors, 'invalid_date', f'{project_id}: updated_at must be YYYY-MM-DD.')
        entry = project.get('entry', '')
        if not isinstance(entry, str) or not entry:
            continue
        if entry in entries:
            issue(errors, 'duplicate_entry', f'Multiple projects use the same entry: {entry}')
        entries.add(entry)
        try:
            parsed = urlsplit(entry)
        except ValueError as exc:
            issue(errors, 'invalid_entry', str(exc), project=project_id, entry=entry)
            continue
        if parsed.scheme:
            if parsed.scheme not in ('http', 'https'):
                issue(errors, 'entry_scheme', f'{project_id}: entry URL must use HTTP(S) or a relative path.')
            else:
                external.add(entry)
        else:
            resolved = resolve_ref(root / 'index.html', entry, 'project.entry')
            if resolved:
                local_entries.add(relative(resolved))
                pending.append(resolved)
        for extra in project.get('auxiliary_entries', []):
            resolved = resolve_ref(root / 'index.html', extra, 'project.auxiliary_entries')
            if resolved:
                auxiliary.add(relative(resolved))
                pending.append(resolved)

    for candidate in sorted((root / 'projects').glob('**/index.html')):
        if relative(candidate) not in local_entries | auxiliary:
            issue(errors, 'unindexed_entry', 'A project entry exists but is absent from the catalogue.', path=relative(candidate))
    if (root / 'index.html').is_file():
        pending.append(root / 'index.html')
    else:
        issue(errors, 'missing_index', 'Generate index.html before auditing.')

    while pending:
        path = pending.pop()
        if path in visited:
            continue
        visited.add(path)
        suffix = path.suffix.lower()
        if suffix not in ('.html', '.htm', '.css', '.js', '.mjs'):
            continue
        try:
            text = path.read_text(encoding='utf-8-sig')
        except (OSError, UnicodeError) as exc:
            issue(errors, 'unreadable_text', str(exc), source=relative(path))
            continue
        refs, css, js, base = [], [], [], ''
        if suffix in ('.html', '.htm'):
            parser = References()
            try:
                parser.feed(text)
            except Exception as exc:
                issue(errors, 'invalid_html', str(exc), source=relative(path))
                continue
            refs, css, js, base = parser.refs, parser.css, parser.js, parser.base
        elif suffix == '.css':
            css = [text]
        else:
            js = [text]
        for chunk in css:
            refs.extend((match.group(2), 'css url()', None) for match in CSS_URL.finditer(chunk))
            refs.extend((match.group(1), 'css @import', None) for match in CSS_IMPORT.finditer(chunk))
        for chunk in js:
            for match in JS_IMPORT.finditer(chunk):
                reference = match.group(1)
                if reference.startswith(('.', '/', 'http:', 'https:')):
                    refs.append((reference, 'module import', None))
                else:
                    issue(warnings, 'bare_module', 'Bare module import requires an import map or a build step.', source=relative(path), target=reference)
        for target, context, line in refs:
            resolved = resolve_ref(path, target, context, line, base)
            if resolved:
                pending.append(resolved)

    # Standalone HTML projects can arrive with names other than index.html.
    # Require every HTML file to be reachable from the catalogue or explicitly
    # registered as an auxiliary page, so a newly copied tool cannot disappear.
    for candidate in sorted((root / 'projects').rglob('*')):
        if candidate.is_file() and candidate.suffix.lower() in ('.html', '.htm'):
            candidate = candidate.resolve()
            if candidate not in visited and candidate not in auxiliary and candidate not in local_entries:
                issue(errors, 'unreachable_html', 'HTML file is not reachable from any indexed project; register it or link it as an auxiliary page.', path=relative(candidate))

    if external:
        issue(warnings, 'external_dependencies', 'External URLs were inventoried; their availability and browser behaviour require a separate live check.', count=len(external))
    return {
        'ok': not errors,
        'catalogue_updated_at': data.get('updated_at'),
        'counts': {'projects': len(projects), 'categories': len(categories), 'local_entries': len(local_entries), 'auxiliary_entries': len(auxiliary), 'files_checked': len(visited), 'local_references': dependency_count, 'external_urls': len(external)},
        'errors': errors,
        'warnings': warnings,
        'external_urls': sorted(external),
        'verification_scope': 'Manifest, generated index, static HTML/CSS references and literal module imports. Dynamic fetches, browser execution and external availability are not verified by this audit.'
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--output', type=Path, help='Optional path for the complete machine-readable JSON report.')
    args = parser.parse_args()
    root = args.root.resolve()
    report = audit(root, args.manifest or root / 'projects.json')
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding='utf-8')
    print(serialized)
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
