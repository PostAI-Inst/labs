(() => {
  'use strict';
  const dataElement = document.getElementById('project-data');
  if (!dataElement) return;
  let data;
  try { data = JSON.parse(dataElement.textContent); } catch { return; }
  const search = document.getElementById('project-search');
  const status = document.getElementById('project-status');
  const count = document.getElementById('result-count');
  const empty = document.getElementById('empty-state');
  const reset = document.getElementById('reset-filters');
  const buttons = [...document.querySelectorAll('[data-category]')];
  const categoryNames = Object.fromEntries(data.categories.map(category => [category.id, category.label]));
  const normalise = value => String(value || '').normalize('NFKC').toLocaleLowerCase().trim();
  const projects = data.projects.map(project => ({
    ...project,
    element: document.getElementById(project.id),
    haystack: normalise([project.title, project.description, categoryNames[project.category], project.kind, ...(project.tags || [])].join(' '))
  }));
  let category = 'all';

  function update() {
    const query = normalise(search.value);
    const terms = query.split(/\s+/).filter(Boolean);
    let visible = 0;
    for (const project of projects) {
      const match = (category === 'all' || project.category === category)
        && (status.value === 'all' || (project.status || 'ready') === status.value)
        && terms.every(term => project.haystack.includes(term));
      if (project.element) project.element.hidden = !match;
      if (match) visible++;
    }
    count.textContent = visible === projects.length
      ? `显示全部 ${visible} 个项目`
      : `找到 ${visible} 个项目，共 ${projects.length} 个`;
    empty.hidden = visible > 0;
    reset.hidden = !query && category === 'all' && status.value === 'all';
    for (const button of buttons) {
      const selected = button.dataset.category === category;
      button.classList.toggle('active', selected);
      button.setAttribute('aria-pressed', String(selected));
    }
    const params = new URLSearchParams();
    if (query) params.set('q', search.value.trim());
    if (category !== 'all') params.set('topic', category);
    if (status.value !== 'all') params.set('status', status.value);
    const suffix = params.toString();
    try { history.replaceState(null, '', location.pathname + (suffix ? '?' + suffix : '') + location.hash); } catch {}
  }

  function resetAll() {
    search.value = '';
    category = 'all';
    status.value = 'all';
    update();
    search.focus({ preventScroll: true });
  }

  for (const button of buttons) button.addEventListener('click', () => {
    category = button.dataset.category;
    update();
  });
  search.addEventListener('input', update);
  status.addEventListener('change', update);
  reset.addEventListener('click', resetAll);
  document.getElementById('empty-reset').addEventListener('click', resetAll);
  document.addEventListener('keydown', event => {
    const target = event.target;
    const editing = target instanceof HTMLElement && (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName));
    if (event.key === '/' && !editing && !event.ctrlKey && !event.metaKey && !event.altKey) {
      event.preventDefault();
      search.focus();
      search.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }
    if (event.key === 'Escape' && target === search && search.value) {
      search.value = '';
      update();
    }
  });
  const params = new URLSearchParams(location.search);
  search.value = params.get('q') || '';
  const topic = params.get('topic');
  if (data.categories.some(item => item.id === topic)) category = topic;
  const selectedStatus = params.get('status');
  if (['ready', 'external', 'limited'].includes(selectedStatus)) status.value = selectedStatus;
  document.documentElement.classList.add('has-js');
  update();
})();
