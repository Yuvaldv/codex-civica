import { GENERATED_LAW_META } from '../generatedLawMeta';

// ─── Storage ──────────────────────────────────────────────────────────────────

function readGroup()   { try { return localStorage.getItem('law-group') || 'year'; } catch { return 'year'; } }
function writeGroup(v) { try { localStorage.setItem('law-group', v); } catch {} }

// ─── Group key ────────────────────────────────────────────────────────────────

const STATUS_HE = { 'In Effect': 'תקף', 'Cancelled': 'בטל', 'Expired': 'פקע' };

function groupKey(by, meta) {
  switch (by) {
    case 'category': return meta.categoryLabelHe || meta.categoryLabel || 'אחר';
    case 'minister': return meta.ministerHe || meta.minister || 'אחר';
    case 'status':   return meta.statusHe || STATUS_HE[meta.status] || meta.status || '?';
    default:         return meta.year ? String(meta.year) : '?'; // 'year' + fallback
  }
}

// ─── Sidebar grouping ─────────────────────────────────────────────────────────

function lawIdFromHref(href) {
  const m = (href || '').match(/\/laws\/(\d+)/);
  return m ? m[1] : null;
}

function makeGroupEl(label, items) {
  const li = document.createElement('li');
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

// Applies grouping to a single sidebar <ul>. Safe to call multiple times —
// handles fresh sidebars, already-grouped sidebars, and React hydration hybrids.
function applyGroupToList(lawList, by) {
  // Collect ALL law <li> elements from the full subtree (including inside
  // existing law-group containers). First-occurrence-wins deduplication:
  // in DOM order, React-rendered flat items precede our appended group
  // containers, so first = freshest. This also prevents the "empty sidebar"
  // bug where removing groups first would take their law items with them,
  // leaving nothing to collect.
  const byId = new Map();
  for (const a of lawList.querySelectorAll('a[href*="/laws/"]')) {
    const id = lawIdFromHref(a.getAttribute('href'));
    if (!id) continue;
    const li = a.closest('li.menu__list-item');
    if (li && !byId.has(id)) byId.set(id, li);
  }
  if (byId.size === 0) return;

  // Detach collected items from wherever they live (flat list or inside groups).
  for (const li of byId.values()) li.remove();

  // Now remove group containers — they are empty or fully detached at this point.
  for (const g of lawList.querySelectorAll(':scope > li.law-group')) g.remove();

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

// Applies grouping to ALL sidebar instances in the document.
// Docusaurus renders a second sidebar for the mobile hamburger drawer —
// both must be grouped independently.
function applyGroup(by) {
  for (const list of document.querySelectorAll('ul.theme-doc-sidebar-menu.menu__list')) {
    applyGroupToList(list, by);
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

// ─── DOM observer (mobile sidebar) ───────────────────────────────────────────
// Watches for Docusaurus mounting new sidebar instances (e.g. the mobile
// hamburger drawer). Groups only newly-added sidebar <ul> elements so it
// cannot trigger a mutation loop from its own DOM writes.

function startDomObserver() {
  let rafId = null;

  const obs = new MutationObserver((mutations) => {
    // Sync navbar UI at most once per frame.
    if (!rafId) {
      rafId = requestAnimationFrame(() => {
        syncGroupByVisibility();
        syncSelect();
        rafId = null;
      });
    }

    // Look for newly-added sidebar <ul> elements and group them immediately.
    // We intentionally do NOT call applyGroup() here — that would re-traverse
    // the whole document and could loop. Instead we only touch added nodes.
    for (const mut of mutations) {
      for (const node of mut.addedNodes) {
        if (node.nodeType !== 1) continue;
        // Is the added node itself a sidebar list?
        if (node.matches('ul.theme-doc-sidebar-menu.menu__list')) {
          applyGroupToList(node, readGroup());
          continue;
        }
        // Does it contain sidebar lists? (e.g. the hamburger drawer wrapper)
        for (const list of node.querySelectorAll('ul.theme-doc-sidebar-menu.menu__list')) {
          applyGroupToList(list, readGroup());
        }
      }
    }
  });

  obs.observe(document.body, { childList: true, subtree: true });
}

// ─── Docusaurus lifecycle hook ────────────────────────────────────────────────

export function onRouteDidUpdate({ location }) {
  _showGroupBy = location.pathname.includes('/laws');
  syncGroupByVisibility();
  syncSelect();
  requestAnimationFrame(() => applyGroup(readGroup()));
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

    startDomObserver();
    applyGroup(readGroup());
  });
}
