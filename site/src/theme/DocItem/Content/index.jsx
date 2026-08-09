import React from 'react';
import Head from '@docusaurus/Head';
import Content from '@theme-original/DocItem/Content';
import {useDoc} from '@docusaurus/plugin-content-docs/client';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import {GENERATED_LAW_META} from '../../../generatedLawMeta';
import styles from './styles.module.css';

function LawSeoHead() {
  const {siteConfig} = useDocusaurusContext();
  const {frontMatter, metadata} = useDoc();
  const {bill_id, law_id, publication_date, law_validity, title_he} = frontMatter;
  const id = String(bill_id || law_id || '');
  const title = title_he || metadata.title;
  const url = siteConfig.url + metadata.permalink;

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Legislation',
    name: title,
    ...(id && {legislationIdentifier: id}),
    ...(publication_date && {legislationDate: publication_date}),
    legislationJurisdiction: {'@type': 'Country', name: 'Israel'},
    legislationStatus: law_validity === 'תקף' ? 'InForce' : law_validity || undefined,
    inLanguage: 'he',
    url,
  };

  return (
    <Head>
      <html lang="he" dir="rtl" />
      <meta property="og:locale" content="he_IL" />
      <script type="application/ld+json">{JSON.stringify(jsonLd)}</script>
    </Head>
  );
}

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
      <LawSeoHead />
      <LawMetaBubbles />
      <Content {...props} />
    </>
  );
}
