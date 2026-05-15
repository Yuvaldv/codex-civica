import React from 'react';
import Content from '@theme-original/DocItem/Content';
import {useDoc} from '@docusaurus/plugin-content-docs/client';
import styles from './styles.module.css';

const CATEGORY_HE = {
  'basic-laws':          'חוקי יסוד',
  'personal-status':     'מעמד אישי',
  'commerce-industry':   'מסחר ותעשייה',
  'environment':         'איכות הסביבה',
  'labor':               'עבודה',
  'health':              'בריאות',
  'knesset':             'כנסת',
};

// Keyed by bill_id string
const MINISTER_BY_ID = {
  '147453': 'כנסת',
  '147468': 'משרד המשפטים',
  '147449': 'כנסת',
  '147391': 'משרד המשפטים',
  '174450': 'משרד המשפטים',
  '149942': 'משרד הפנים',
  '151459': 'משרד העבודה והרווחה',
  '174478': 'משרד הבריאות',
  '163627': 'משרד המשפטים',
};

const STATUS_BY_ID = {
  '147449': 'בטל',
};

function LawMetaBubbles() {
  const {frontMatter} = useDoc();
  const {bill_id, publication_date, category} = frontMatter;
  if (!bill_id) return null;

  const id = String(bill_id);
  const year = publication_date ? new Date(publication_date).getFullYear() : null;
  const categoryHe = CATEGORY_HE[category];
  const ministerHe = MINISTER_BY_ID[id];
  const statusHe = STATUS_BY_ID[id] || 'תקף';
  const isActive = statusHe === 'תקף';

  return (
    <div className={styles.lawMeta}>
      {year && <span className={styles.bubble}>{year}</span>}
      {categoryHe && <span className={styles.bubble}>{categoryHe}</span>}
      {ministerHe && <span className={styles.bubble}>{ministerHe}</span>}
      <span className={`${styles.bubble} ${isActive ? styles.active : styles.cancelled}`}>
        {statusHe}
      </span>
    </div>
  );
}

export default function DocItemContentWrapper(props) {
  return (
    <>
      <LawMetaBubbles />
      <Content {...props} />
    </>
  );
}
