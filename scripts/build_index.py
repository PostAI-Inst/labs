#!/usr/bin/env python3
"""Generate the public Labs directory from projects.json (standard library only)."""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
COLORS = ['#66dfbd', '#8dc9ff', '#e5b27b', '#c2acff', '#b8d97b', '#ef9bb3', '#9dc9ca']
STATUS = {'ready': '在线体验', 'external': '外部项目', 'limited': '部分功能受限'}


def esc(value):
    return html.escape(str(value or ''), quote=True)


def safe_url(value):
    value = str(value or '')
    parsed = urlsplit(value)
    if parsed.scheme and parsed.scheme not in ('http', 'https'):
        raise ValueError(f'Unsupported URL scheme: {value!r}')
    if value.startswith('//'):
        raise ValueError(f'Protocol-relative URL is not allowed: {value!r}')
    return esc(value)


def build(data):
    categories = data.get('categories', [])
    projects = data.get('projects', [])
    category_map = {c['id']: c for c in categories}
    palette = {c['id']: COLORS[i % len(COLORS)] for i, c in enumerate(categories)}
    projects = sorted(projects, key=lambda p: (p.get('updated_at', ''), p.get('title', '')), reverse=True)
    counts = {c['id']: sum(p.get('category') == c['id'] for p in projects) for c in categories}
    dates = [p.get('updated_at', '') for p in projects]
    updated = data.get('updated_at') or max(dates, default='')
    featured = [p for p in projects if p.get('featured')][:4]
    if not featured:
        featured = projects[:3]

    def featured_card(p):
        cat = category_map.get(p.get('category'), {})
        return f'''<a class="featured-card" href="{safe_url(p['entry'])}" style="--accent:{palette.get(p.get('category'), COLORS[0])}">
          <span class="eyebrow">{esc(cat.get('label', p.get('category', '探索')))} <span class="feature-kind">{esc(p.get('kind', '交互项目'))}</span></span>
          <h3>{esc(p['title'])}</h3><p>{esc(p.get('description', ''))}</p>
          <span class="feature-action">{esc(STATUS.get(p.get('status', 'ready'), '打开项目'))}</span>
        </a>'''

    def project_card(p):
        cat = category_map.get(p.get('category'), {})
        status = p.get('status', 'ready')
        tags = ''.join(f'<span>{esc(t)}</span>' for t in p.get('tags', [])[:5])
        notes = f'<p class="project-note">{esc(p["notes"])}</p>' if p.get('notes') else ''
        source = p.get('source') or {}
        source_link = f'<a class="source-link" href="{safe_url(source["url"])}" target="_blank" rel="noopener noreferrer">{esc(source.get("label", "项目来源"))}</a>' if source.get('url') else ''
        return f'''<article class="project-card" id="{esc(p['id'])}" data-project="{esc(p['id'])}" style="--accent:{palette.get(p.get('category'), COLORS[0])}">
          <div class="card-top"><span class="category-label">{esc(cat.get('label', p.get('category', '探索')))}</span><span class="project-kind">{esc(p.get('kind', '交互项目'))}</span></div>
          <h3><a href="{safe_url(p['entry'])}">{esc(p['title'])}</a></h3>
          <p class="project-description">{esc(p.get('description', ''))}</p>
          <div class="project-tags" aria-label="关键词">{tags}</div>{notes}
          <div class="card-bottom"><a class="open-project status-{esc(status)}" href="{safe_url(p['entry'])}">{esc(STATUS.get(status, '打开项目'))}</a><time datetime="{esc(p.get('updated_at', ''))}">{esc(p.get('updated_at', ''))}</time></div>{source_link}
        </article>'''

    category_buttons = ''.join(f'''<button class="category-filter" type="button" data-category="{esc(c['id'])}" aria-pressed="false" style="--accent:{palette[c['id']]}"><span>{esc(c['label'])}</span><span class="filter-count">{counts[c['id']]}</span></button>''' for c in categories)
    all_cards = '\n'.join(project_card(p) for p in projects)
    featured_cards = '\n'.join(featured_card(p) for p in featured)
    ready_count = sum(p.get('status', 'ready') == 'ready' for p in projects)
    external_count = sum(p.get('status') == 'external' for p in projects)
    compact_data = {'updated_at': updated, 'categories': categories, 'projects': projects}
    embedded_json = json.dumps(compact_data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    featured_section = f'''<section class="featured-section" aria-labelledby="featured-title"><div class="section-heading"><div><span class="section-kicker">START EXPLORING</span><h2 id="featured-title">从这里开始探索</h2></div><p>改变一个变量，看看世界如何响应。</p></div><div class="featured-grid">{featured_cards}</div></section>''' if featured else ''
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#0a1113">
  <meta name="description" content="后AI研究所交互实验室：用在线模型、三维沙盘、未来游戏与研究工具，探索技术如何改变人的处境与文明的可能。">
  <meta property="og:title" content="后AI研究所 · Labs 交互实验室">
  <meta property="og:description" content="关注人的处境，开拓文明的可能。探索后AI时代的在线模型、沙盘与游戏。">
  <title>后AI研究所 · Labs 交互实验室</title>
  <link rel="icon" href="assets/logo.png" type="image/png">
  <link rel="stylesheet" href="assets/labs.css">
  <script src="assets/labs.js" defer></script>
</head>
<body>
  <a class="skip-link" href="#catalog">跳到项目目录</a>
  <header class="site-header"><div class="header-inner">
    <a class="brand" href="./" aria-label="后AI研究所 Labs 首页"><img src="assets/logo.png" alt="后AI研究所标志" width="56" height="56"><span><strong>后AI研究所</strong><span>POST-AI INSTITUTE <b>LABS</b></span></span></a>
    <nav aria-label="主导航"><a href="#catalog">项目目录</a><a href="https://github.com/PostAI-Inst/labs" target="_blank" rel="noopener noreferrer">GitHub</a><a href="https://postai.institute/" target="_blank" rel="noopener noreferrer">研究所</a></nav>
  </div></header>
  <main class="main-wrap">
    <section class="hero" aria-labelledby="hero-title"><div class="hero-copy"><span class="eyebrow">AN OPEN FIELD FOR POSSIBLE FUTURES</span><h1 id="hero-title">未来，<br>可以亲手探索。</h1><p class="hero-statement">关注人的处境，开拓文明的可能。</p><p class="hero-description">把关于技术、经济、文明与日常生活的问题，变成可以调整、推演和体验的模型、沙盘与游戏。</p><a class="primary-link" href="#catalog">浏览全部项目</a></div><div class="hero-field" aria-hidden="true"><div class="field-label top">TECHNOLOGY / SOCIETY / HUMAN FUTURES</div><div class="orbit orbit-one"></div><div class="orbit orbit-two"></div><div class="orbit orbit-three"></div><span class="field-point p-one"></span><span class="field-point p-two"></span><span class="field-point p-three"></span><div class="field-center"><span>POST-AI</span><strong>可能性的<br>实验场</strong></div><div class="field-label bottom">探索边界 · 看见机制 · 体验后果</div></div></section>
    <section class="metrics" aria-label="目录概览"><div><strong>{len(projects)}</strong><span>个探索项目</span></div><div><strong>{len(categories)}</strong><span>个研究方向</span></div><div><strong>{ready_count}</strong><span>个在线入口</span></div><div class="metric-date"><strong>{esc(updated)}</strong><span>最近一次目录整理</span></div></section>
    {featured_section}
    <section class="catalog-section" id="catalog" aria-labelledby="catalog-title"><div class="section-heading"><div><span class="section-kicker">EXPERIMENT DIRECTORY</span><h2 id="catalog-title">全部探索项目</h2></div><p>从技术边界，走向产业、制度与生活。</p></div>
      <form class="search-toolbar" role="search" onsubmit="return false;"><label class="search-label" for="project-search">搜索项目</label><div class="search-input-wrap"><svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"></circle><path d="m15.5 15.5 5 5"></path></svg><input id="project-search" type="search" placeholder="搜索主题、项目或关键词" autocomplete="off"><kbd aria-hidden="true">/</kbd></div><label class="status-label" for="project-status">入口状态</label><select id="project-status"><option value="all">所有入口</option><option value="ready">在线体验</option><option value="external">外部项目</option><option value="limited">部分功能受限</option></select></form>
      <div class="category-filters" role="group" aria-label="按研究方向筛选"><button class="category-filter active" type="button" data-category="all" aria-pressed="true"><span>全部方向</span><span class="filter-count">{len(projects)}</span></button>{category_buttons}</div>
      <div class="catalog-meta"><p id="result-count" role="status" aria-live="polite">显示全部 {len(projects)} 个项目</p><button id="reset-filters" class="reset-filters" type="button" hidden>清除筛选</button><span class="catalog-order">按最近整理日期排序</span></div>
      <noscript><p class="no-script">完整目录已显示。搜索与筛选需要浏览器启用 JavaScript；各项目可以直接打开。</p></noscript>
      <div class="project-grid" id="project-grid">{all_cards}</div><div id="empty-state" class="empty-state" hidden><h3>这个方向还没有匹配的项目</h3><p>试试更短的关键词，或选择其他研究方向。</p><button type="button" id="empty-reset">查看全部项目</button></div>
    </section>
    <aside class="lab-note"><span class="note-mark">LAB NOTES</span><div><h2>在实验中理解未来</h2><p>这里收录研究过程中的交互原型。模型的参数、边界与假设见各项目说明；情景推演帮助提出问题，不代表对未来的确定预测。</p><p class="note-links"><a href="https://github.com/PostAI-Inst/labs">查看项目源码与更新记录</a><span>·</span><a href="https://github.com/PostAI-Inst/boardgame-lab">桌游实验室原仓库</a></p></div></aside>
  </main>
  <footer class="site-footer"><div><strong>后AI研究所 · POST-AI INSTITUTE</strong><p>关注人的处境，开拓文明的可能。</p></div><p>交互模型 / 未来游戏 / 开放探索<br><span>目录更新：{esc(updated)}</span></p></footer>
  <script id="project-data" type="application/json">{embedded_json}</script>
</body>
</html>
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'projects.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'index.html')
    parser.add_argument('--check', action='store_true', help='Fail if the committed index differs from projects.json.')
    args = parser.parse_args()
    try:
        data = json.loads(args.manifest.read_text(encoding='utf-8'))
        result = build(data)
        if args.check:
            if not args.output.is_file() or args.output.read_text(encoding='utf-8') != result:
                print('Index is out of date. Run: python3 scripts/build_index.py', file=sys.stderr)
                return 1
            print(f'Index is current: {len(data.get("projects", []))} projects.')
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(result, encoding='utf-8')
            print(f'Generated {args.output}: {len(data.get("projects", []))} projects.')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'Cannot build index: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
