import { GENERATED_LAW_META } from '../generatedLawMeta';

// ─── Storage ──────────────────────────────────────────────────────────────────

function readGroup()    { try { return localStorage.getItem('law-group') || 'year'; } catch { return 'year'; } }
function writeGroup(v)  { try { localStorage.setItem('law-group', v); } catch {} }

// ─── URL helpers ──────────────────────────────────────────────────────────────

function lawIdFromPath(path) { const m = (path || '').match(/\/laws\/(\d+)/); return m ? m[1] : null; }
function lawIdFromHref(href) { const m = (href || '').match(/\/laws\/(\d+)/); return m ? m[1] : null; }

// ─── Sidebar grouping ─────────────────────────────────────────────────────────

const STATUS_HE = { 'In Effect': 'תקף', 'Cancelled': 'בטל', 'Expired': 'פקע' };

function groupKey(by, meta) {
  switch (by) {
    case 'year':     return meta.year ? String(meta.year) : '?';
    case 'category': return meta.categoryLabelHe || meta.categoryLabel || 'אחר';
    case 'minister': return meta.ministerHe || meta.minister || 'אחר';
    case 'status':   return meta.statusHe || STATUS_HE[meta.status] || meta.status || '?';
    default:         return meta.year ? String(meta.year) : '?';
  }
}

function makeGroupEl(label, items) {
  const li  = document.createElement('li');
  li.className = 'menu__list-item law-group';

  const wrap = document.createElement('div');
  wrap.className = 'menu__list-item-collapsible';

  const btn = document.createElement('button');
  btn.className = 'menu__link menu__link--sublist menu__link--sublist-caret';
  btn.type = 'button';
  btn.textContent = label;
  btn.addEventListener('click', () => li.classList.toggle('menu__list-item--collapsed'));

  wrap.appendChild(btn);
  li.appendChild(wrap);

  const ul = document.createElement('ul');
  ul.className = 'menu__list';
  for (const item of items) ul.appendChild(item);
  li.appendChild(ul);
  return li;
}

function applyGroup(by) {
  const lawList = document.querySelector('ul.theme-doc-sidebar-menu.menu__list');
  if (!lawList) return;

  // Purge our custom group containers FIRST so they don't pollute collection.
  // (React hydration can re-add fresh flat items alongside our old group nodes,
  //  causing duplicates if we collect before purging.)
  for (const g of lawList.querySelectorAll(':scope > li.law-group')) g.remove();

  // Collect direct-child law items, deduplicated by law ID.
  const byId = new Map();
  for (const a of lawList.querySelectorAll('a[href*="/laws/"]')) {
    const id = lawIdFromHref(a.getAttribute('href'));
    if (!id) continue;
    const li = a.closest('li.menu__list-item');
    if (li && li.parentNode === lawList) byId.set(id, li);
  }
  if (byId.size === 0) return;

  for (const li of byId.values()) li.remove();

  const groups = new Map();
  for (const [id, li] of byId) {
    const key = groupKey(by, GENERATED_LAW_META[id] || {});
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(li);
  }

  const sorted = [...groups.keys()].sort((a, b) =>
    by === 'year' ? Number(a) - Number(b) : a.localeCompare(b, 'he')
  );

  for (const key of sorted) lawList.appendChild(makeGroupEl(key, groups.get(key)));
}

// ─── Metadata bar ─────────────────────────────────────────────────────────────

let _barObserver  = null;
let _currentLawId = null;

function buildBar(lawId) {
  const meta = GENERATED_LAW_META[lawId];
  if (!meta) return null;

  const bar = document.createElement('div');
  bar.className = 'law-meta-bar';
  bar.dataset.lawId = lawId;

  const badge = (text, type) => {
    if (!text) return;
    const s = document.createElement('span');
    s.className = `law-meta-badge law-meta-badge--${type}`;
    s.textContent = text;
    bar.appendChild(s);
  };

  // Fixed order, all Hebrew: year · category · ministry · status
  badge(meta.year ? String(meta.year) : null, 'year');
  badge(meta.categoryLabelHe || meta.categoryLabel || null, 'category');
  badge(meta.ministerHe || null, 'minister');
  if (meta.statusHe) badge(meta.statusHe, 'status-' + (meta.status || '').toLowerCase().replace(/\s+/g, '-'));

  return bar;
}

function tryInjectBar(lawId) {
  const bar = buildBar(lawId);
  if (!bar) return false;
  const container = document.querySelector('.markdown');
  if (!container) return false;
  document.querySelectorAll('.law-meta-bar').forEach(el => el.remove());
  container.insertBefore(bar, container.firstChild);
  return true;
}

function stopBarObserver() {
  if (_barObserver) { _barObserver.disconnect(); _barObserver = null; }
}

function watchForBar(lawId) {
  stopBarObserver();
  _currentLawId = lawId;

  // Try immediately — on initial load .markdown is usually already present.
  if (tryInjectBar(lawId)) return;

  // Otherwise watch for .markdown to appear. Disconnects after first successful
  // inject so it can never fire twice for the same page.
  let safetyTimer = setTimeout(stopBarObserver, 4000);

  _barObserver = new MutationObserver(() => {
    if (_currentLawId !== lawId) { clearTimeout(safetyTimer); stopBarObserver(); return; }
    if (tryInjectBar(lawId))     { clearTimeout(safetyTimer); stopBarObserver(); }
  });
  _barObserver.observe(document.getElementById('__docusaurus') || document.body, {
    childList: true,
    subtree: true,
  });
}

function handleRoute(pathname) {
  const lawId = lawIdFromPath(pathname);
  if (lawId) {
    watchForBar(lawId);
  } else {
    stopBarObserver();
    _currentLawId = null;
    document.querySelectorAll('.law-meta-bar').forEach(el => el.remove());
  }
}

// ─── Navbar group-by ──────────────────────────────────────────────────────────

let _showGroupBy = false;

function syncGroupByVisibility() {
  document.querySelectorAll('[id="navbar-sortby"]').forEach(el => {
    el.style.display = _showGroupBy ? 'flex' : 'none';
  });
}

function syncSelect() {
  const val = readGroup();
  document.querySelectorAll('[id="law-sort-select"]').forEach(sel => { sel.value = val; });
}

// ─── Docusaurus lifecycle hook ────────────────────────────────────────────────

export function onRouteDidUpdate({ location }) {
  _showGroupBy = location.pathname.includes('/laws');
  syncGroupByVisibility();
  syncSelect();
  requestAnimationFrame(() => {
    applyGroup(readGroup());
    handleRoute(location.pathname);
  });
}

// ─── Init ─────────────────────────────────────────────────────────────────────

if (typeof window !== 'undefined') {
  window.addEventListener('DOMContentLoaded', () => {
    _showGroupBy = window.location.pathname.includes('/laws');
    syncGroupByVisibility();
    syncSelect();

    document.addEventListener('change', e => {
      if (e.target?.id === 'law-sort-select') {
        writeGroup(e.target.value);
        syncSelect();
        applyGroup(e.target.value);
      }
    });

    // Re-sync group-by visibility when Docusaurus mounts mobile hamburger.
    let rafId = null;
    const obs = new MutationObserver(() => {
      if (rafId) return;
      rafId = requestAnimationFrame(() => { syncGroupByVisibility(); syncSelect(); rafId = null; });
    });
    obs.observe(document.body, { childList: true, subtree: true });

    applyGroup(readGroup());
    // onRouteDidUpdate fires on initial load in Docusaurus — bar injection handled there.
  });
}
