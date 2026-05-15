import React from 'react';
import Content from '@theme-original/DocItem/Content';
import {useDoc} from '@docusaurus/plugin-content-docs/client';
import {GENERATED_LAW_META} from '../../../generatedLawMeta';
import styles from './styles.module.css';

function LawMetaBubbles() {
  const {frontMatter} = useDoc();
  const {bill_id, law_id, publication_date} = frontMatter;
  const id = String(bill_id || law_id || '');
  if (!id) return null;

  const meta = GENERATED_LAW_META[id] || {};
  const year = publication_date ? new Date(publication_date).getFullYear() : meta.year || null;
  const categoryHe = meta.categoryLabelHe || null;
  const ministerHe = meta.ministerHe || null;
  const statusHe = meta.statusHe || 'תקף';
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
