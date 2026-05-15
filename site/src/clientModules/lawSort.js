const LAW_META = {
  '147453': {year: 1958, categoryLabel: 'Basic Laws',          minister: 'Knesset',         status: 'In Effect'},
  '147468': {year: 1965, categoryLabel: 'Personal Status',     minister: 'Justice',          status: 'In Effect'},
  '147449': {year: 1968, categoryLabel: 'Basic Laws',          minister: 'Knesset',          status: 'Cancelled'},
  '147391': {year: 1973, categoryLabel: 'Commerce & Industry', minister: 'Justice',          status: 'In Effect'},
  '174450': {year: 1984, categoryLabel: 'Basic Laws',          minister: 'Justice',          status: 'In Effect'},
  '149942': {year: 1984, categoryLabel: 'Environment',         minister: 'Interior',         status: 'In Effect'},
  '151459': {year: 1987, categoryLabel: 'Labor',               minister: 'Labor & Welfare',  status: 'In Effect'},
  '174478': {year: 1996, categoryLabel: 'Health',              minister: 'Health',           status: 'In Effect'},
  '163627': {year: 1998, categoryLabel: 'Knesset',             minister: 'Justice',          status: 'In Effect'},
};

function getLawId(href) {
  const m = (href || '').match(/\/laws\/(\d+)/);
  return m ? m[1] : null;
}

function getGroup() {
  try { return localStorage.getItem('law-group') || 'year'; } catch { return 'year'; }
}

function setGroup(v) {
  try { localStorage.setItem('law-group', v); } catch {}
}

function findLawList() {
  for (const link of document.querySelectorAll('.menu__link')) {
    if (link.textContent.trim() === 'State') {
      const stateItem = link.closest('li.menu__list-item');
      if (stateItem) return stateItem.querySelector('ul.menu__list');
    }
  }
  return null;
}

const CATEGORY_HE = {
  'Basic Laws':          'חוקי יסוד',
  'Personal Status':     'מעמד אישי',
  'Commerce & Industry': 'מסחר ותעשייה',
  'Environment':         'איכות הסביבה',
  'Labor':               'עבודה',
  'Health':              'בריאות',
  'Knesset':             'כנסת',
};

const MINISTER_HE = {
  'Knesset':         'כנסת',
  'Justice':         'משרד המשפטים',
  'Interior':        'משרד הפנים',
  'Labor & Welfare': 'משרד העבודה והרווחה',
  'Health':          'משרד הבריאות',
};

const STATUS_HE = {
  'In Effect': 'תקף',
  'Cancelled': 'בטל',
  'Expired':   'פקע',
};

function getGroupKey(groupBy, meta) {
  switch (groupBy) {
    case 'year':     return String(meta.year || '?');
    case 'category': return CATEGORY_HE[meta.categoryLabel] || meta.categoryLabel || 'אחר';
    case 'minister': return MINISTER_HE[meta.minister]      || meta.minister      || 'אחר';
    case 'status':   return STATUS_HE[meta.status]          || meta.status        || '?';
    default:         return String(meta.year || '?');
  }
}

function createGroupElement(label, items) {
  const li = document.createElement('li');
  li.className = 'menu__list-item law-group';

  const wrap = document.createElement('div');
  wrap.className = 'menu__list-item-collapsible';

  const btn = document.createElement('button');
  btn.className = 'menu__link menu__link--sublist menu__link--sublist-caret';
  btn.type = 'button';
  btn.textContent = label;
  btn.addEventListener('click', () => {
    li.classList.toggle('menu__list-item--collapsed');
  });

  wrap.appendChild(btn);
  li.appendChild(wrap);

  const ul = document.createElement('ul');
  ul.className = 'menu__list';
  for (const item of items) ul.appendChild(item);
  li.appendChild(ul);

  return li;
}

function applyGroup(groupBy) {
  const lawList = findLawList();
  if (!lawList) return;

  // Collect all law li's from anywhere in the list hierarchy
  const seen = new Set();
  const lawItems = [];
  for (const a of lawList.querySelectorAll('a[href*="/laws/"]')) {
    const li = a.closest('li.menu__list-item');
    if (li && !seen.has(li)) {
      seen.add(li);
      lawItems.push(li);
    }
  }
  if (lawItems.length === 0) return;

  // Detach law items from wherever they currently live
  for (const item of lawItems) {
    item.parentNode?.removeChild(item);
  }

  // Remove now-empty law-group containers
  for (const g of lawList.querySelectorAll('li.law-group')) {
    g.remove();
  }

  // Group by key
  const groups = new Map();
  for (const item of lawItems) {
    const id  = getLawId(item.querySelector('a')?.getAttribute('href'));
    const meta = LAW_META[id] || {};
    const key = getGroupKey(groupBy, meta);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(item);
  }

  // Sort group keys
  const sortedKeys = [...groups.keys()].sort((a, b) =>
    groupBy === 'year' ? Number(a) - Number(b) : a.localeCompare(b, 'he')
  );

  // Append collapsible group elements
  for (const key of sortedKeys) {
    lawList.appendChild(createGroupElement(key, groups.get(key)));
  }
}

function syncSelect() {
  const sel = document.getElementById('law-sort-select');
  if (sel) sel.value = getGroup();
}

function updateVisibility(pathname) {
  const el = document.getElementById('navbar-sortby');
  if (!el) return;
  el.style.display = pathname.includes('/laws') ? 'flex' : 'none';
}

export function onRouteDidUpdate({location}) {
  updateVisibility(location.pathname);
  syncSelect();
  requestAnimationFrame(() => setTimeout(() => applyGroup(getGroup()), 80));
}

if (typeof window !== 'undefined') {
  window.addEventListener('DOMContentLoaded', () => {
    updateVisibility(window.location.pathname);
    syncSelect();

    const sel = document.getElementById('law-sort-select');
    if (sel) {
      sel.addEventListener('change', e => {
        setGroup(e.target.value);
        applyGroup(e.target.value);
      });
    }

    setTimeout(() => applyGroup(getGroup()), 300);
  });
}
