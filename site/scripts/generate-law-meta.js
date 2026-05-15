#!/usr/bin/env node
// Reads laws/israel/*.md frontmatter and writes site/src/generatedLawMeta.js
// Run via prebuild / predeploy npm hooks.
'use strict';

const fs = require('fs');
const path = require('path');

const LAWS_DIR = path.resolve(__dirname, '../../laws/israel');
const OUT_FILE = path.resolve(__dirname, '../src/generatedLawMeta.js');

// Category slug -> English label
const CATEGORY_EN = {
  'administrative-law': 'Administrative Law', 'agriculture': 'Agriculture',
  'asset-management': 'Asset Management', 'aviation': 'Aviation',
  'basic-laws': 'Basic Laws', 'budget': 'Budget',
  'citizenship': 'Citizenship', 'civil-law': 'Civil Law',
  'commerce-industry': 'Commerce & Industry', 'communications': 'Communications',
  'consumer-protection': 'Consumer Protection', 'criminal-law': 'Criminal Law',
  'defense': 'Defense', 'economic-arrangements': 'Economic Arrangements',
  'education': 'Education', 'employment': 'Employment',
  'environment': 'Environment', 'evidence-procedure': 'Evidence & Procedure',
  'foreign-affairs': 'Foreign Affairs', 'heads-of-state': 'Heads of State',
  'health': 'Health', 'holidays': 'Holidays',
  'housing-construction': 'Housing', 'immigration': 'Immigration',
  'infrastructure': 'Infrastructure', 'judiciary': 'Judiciary',
  'knesset': 'Knesset', 'labor': 'Labor',
  'local-authorities': 'Local Government', 'maritime': 'Maritime',
  'personal-status': 'Personal Status', 'public-security': 'Security',
  'real-estate': 'Real Estate', 'religion': 'Religion',
  'sports': 'Sports', 'taxation': 'Taxation',
  'tourism': 'Tourism', 'transportation': 'Transportation',
  'welfare': 'Welfare',
};

// Category slug -> Hebrew label
const CATEGORY_HE = {
  'administrative-law': 'דיני מינהל', 'agriculture': 'חקלאות',
  'asset-management': 'ניהול נכסים', 'aviation': 'תעופה',
  'basic-laws': 'חוקי יסוד', 'budget': 'תקציב',
  'citizenship': 'אזרחות', 'civil-law': 'משפט אזרחי',
  'commerce-industry': 'מסחר ותעשייה', 'communications': 'תקשורת',
  'consumer-protection': 'הגנת הצרכן', 'criminal-law': 'משפט פלילי',
  'defense': 'ביטחון', 'economic-arrangements': 'הסדרים כלכליים',
  'education': 'חינוך', 'employment': 'תעסוקה',
  'environment': 'איכות הסביבה', 'evidence-procedure': 'ראיות וסדר דין',
  'foreign-affairs': 'יחסי חוץ', 'heads-of-state': 'ראשי מדינה',
  'health': 'בריאות', 'holidays': 'חגים ומועדים',
  'housing-construction': 'דיור ובנייה', 'immigration': 'עלייה וקליטה',
  'infrastructure': 'תשתיות', 'judiciary': 'שפיטה',
  'knesset': 'כנסת', 'labor': 'עבודה',
  'local-authorities': 'רשויות מקומיות', 'maritime': 'ים ומשפט ימי',
  'personal-status': 'מעמד אישי', 'public-security': 'ביטחון הציבור',
  'real-estate': 'מקרקעין', 'religion': 'דת',
  'sports': 'ספורט', 'taxation': 'מיסוי',
  'tourism': 'תיירות', 'transportation': 'תחבורה',
  'welfare': 'רווחה',
};

// Legacy ministry ID (KNS_IsraelLawMinistry range 1-50) -> English name
const MINISTRY_EN = {
  1: 'Prime Minister', 2: 'Finance', 3: 'Foreign Affairs', 4: 'Defense',
  5: 'Interior', 6: 'Justice', 7: 'Education', 8: 'Health',
  9: 'Welfare', 10: 'Labor', 11: 'Agriculture', 12: 'Commerce & Industry',
  13: 'Communications', 14: 'Housing', 15: 'Transport', 16: 'Tourism',
  17: 'Energy', 18: 'Environment', 19: 'Defense', 20: 'Religious Affairs',
  21: 'Police', 22: 'Science', 23: 'Culture', 24: 'Knesset',
  25: 'State Comptroller', 26: 'National Infrastructure', 27: 'Immigration',
  28: 'Sports', 29: 'Regional Development', 30: 'Intelligence',
  31: 'Strategic Affairs', 32: 'Diaspora', 33: 'Minorities',
  34: 'Social Equality', 35: 'Economy', 36: 'Innovation',
  37: 'Labor & Welfare', 38: 'Interior', 39: 'Justice', 40: 'Finance',
  41: 'Health', 42: 'Education', 43: 'Agriculture', 44: 'Transport',
  45: 'Environment', 46: 'Housing', 47: 'Communications',
  48: 'Foreign Affairs', 49: 'Defense', 50: 'Prime Minister',
};

function getField(fm, key) {
  const m = fm.match(new RegExp('^' + key + ':\\s*(.+)', 'm'));
  if (!m) return null;
  return m[1].trim().replace(/^["']|["']$/g, '');
}

function getTags(text) {
  // Block sequence: tags:\n  - "x"\n  - "y"
  const block = text.match(/^tags:\n((?:[ \t]+-[^\n]+\n?)+)/m);
  if (block) {
    return block[1]
      .split('\n')
      .map(l => l.replace(/^[ \t]+-\s*/, '').replace(/^["']|["']$/g, '').trim())
      .filter(Boolean);
  }
  // Inline: tags: ["x", "y"]
  const inline = text.match(/^tags:\s*\[([^\]]+)\]/m);
  if (inline) {
    return inline[1].split(',').map(s => s.replace(/["']/g, '').trim()).filter(Boolean);
  }
  return [];
}

function getMinistryIds(text) {
  const m = text.match(/^ministry_ids:\s*\[([^\]]*)\]/m);
  if (!m || !m[1].trim()) return [];
  return m[1].split(',').map(s => parseInt(s.trim(), 10)).filter(n => !isNaN(n));
}

const meta = {};
let count = 0;

for (const fname of fs.readdirSync(LAWS_DIR).sort()) {
  if (!fname.endsWith('.md') || fname === '_index.md') continue;
  const text = fs.readFileSync(path.join(LAWS_DIR, fname), 'utf8');

  // Extract frontmatter block
  const fmMatch = text.match(/^---\n([\s\S]*?)\n---/);
  if (!fmMatch) continue;
  const fm = fmMatch[1];

  const lawId = getField(fm, 'law_id') || getField(fm, 'bill_id');
  if (!lawId) continue;

  const pubDate = getField(fm, 'publication_date') || '';
  const year = pubDate ? parseInt(pubDate.slice(0, 4), 10) : null;

  const slug = getField(fm, 'category') || '';
  const categoryLabel = CATEGORY_EN[slug] || slug || 'Other';
  const categoryLabelHe = CATEGORY_HE[slug] || categoryLabel;

  const ministryIds = getMinistryIds(text);
  const ministerNames = [...new Set(ministryIds.map(id => MINISTRY_EN[id]).filter(Boolean))];
  const minister = ministerNames[0] || 'Unknown';

  const validity = (getField(fm, 'law_validity') || '').trim();
  const status = validity === 'תקף' ? 'In Effect'
               : validity === 'בטל' ? 'Cancelled'
               : validity === 'פקע' ? 'Expired'
               : validity || 'Unknown';
  const statusHe = validity || 'לא ידוע';

  const tags = getTags(text);

  meta[String(lawId)] = { year, categoryLabel, categoryLabelHe, minister, status, statusHe, tags };
  count++;
}

const out = [
  '// AUTO-GENERATED by site/scripts/generate-law-meta.js — do not edit manually',
  'export const GENERATED_LAW_META = ' + JSON.stringify(meta, null, 2) + ';',
].join('\n') + '\n';

fs.writeFileSync(OUT_FILE, out, 'utf8');
console.log('[generate-law-meta] wrote ' + count + ' entries to ' + path.basename(OUT_FILE));
