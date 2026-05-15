const LAW_META = {
  '147453': {year: 1958, categoryLabel: 'Basic Laws'},
  '147468': {year: 1965, categoryLabel: 'Personal Status'},
  '147449': {year: 1968, categoryLabel: 'Basic Laws'},
  '147391': {year: 1973, categoryLabel: 'Commerce & Industry'},
  '174450': {year: 1984, categoryLabel: 'Basic Laws'},
  '149942': {year: 1984, categoryLabel: 'Environment'},
  '151459': {year: 1987, categoryLabel: 'Labor'},
  '174478': {year: 1996, categoryLabel: 'Health'},
  '163627': {year: 1998, categoryLabel: 'Knesset'},
};

function getLawId(href) {
  const m = (href || '').match(/\/laws\/(\d+)/);
  return m ? m[1] : null;
}

function getSort() {
  try { return localStorage.getItem('law-sort') || 'year'; } catch { return 'year'; }
}

function setSort(v) {
  try { localStorage.setItem('law-sort', v); } catch {}
}

function applySort(sortBy) {
  const allLinks = document.querySelectorAll('.menu__link');
  let stateHeader = null;
  for (const link of allLinks) {
    if (link.textContent.trim() === 'State') { stateHeader = link; break; }
  }
  if (!stateHeader) return;

  const stateItem = stateHeader.closest('li.menu__list-item');
  if (!stateItem) return;

  const lawList = stateItem.querySelector('ul.menu__list');
  if (!lawList) return;

  const items = [...lawList.querySelectorAll(':scope > li.menu__list-item')];
  if (items.length < 2) return;

  items.sort((a, b) => {
    const aId = getLawId(a.querySelector('a')?.getAttribute('href'));
    const bId = getLawId(b.querySelector('a')?.getAttribute('href'));
    const am = LAW_META[aId] || {year: 9999, categoryLabel: 'zzz'};
    const bm = LAW_META[bId] || {year: 9999, categoryLabel: 'zzz'};
    if (sortBy === 'category') {
      const c = am.categoryLabel.localeCompare(bm.categoryLabel);
      return c !== 0 ? c : am.year - bm.year;
    }
    return am.year - bm.year;
  });

  items.forEach(item => lawList.appendChild(item));
}

function syncSelect() {
  const sel = document.getElementById('law-sort-select');
  if (sel) sel.value = getSort();
}

function updateVisibility(pathname) {
  const el = document.getElementById('navbar-sortby');
  if (!el) return;
  el.style.display = pathname.includes('/laws') ? 'flex' : 'none';
}

export function onRouteDidUpdate({location}) {
  updateVisibility(location.pathname);
  syncSelect();
  requestAnimationFrame(() => setTimeout(() => applySort(getSort()), 80));
}

if (typeof window !== 'undefined') {
  window.addEventListener('DOMContentLoaded', () => {
    updateVisibility(window.location.pathname);
    syncSelect();

    const sel = document.getElementById('law-sort-select');
    if (sel) {
      sel.addEventListener('change', e => {
        setSort(e.target.value);
        applySort(e.target.value);
      });
    }

    setTimeout(() => applySort(getSort()), 300);
  });
}
