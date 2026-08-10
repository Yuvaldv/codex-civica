import React from 'react';
import Head from '@docusaurus/Head';
import Content from '@theme-original/DocItem/Content';
import {useDoc} from '@docusaurus/plugin-content-docs/client';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import {GENERATED_LAW_META} from '../../../generatedLawMeta';
import {countryForPath} from '../../../countryConfig';
import styles from './styles.module.css';

// Sourced verbatim from https://www.legislation.gov.uk/contributors — additional
// attribution legislation.gov.uk requires on top of the standard OGL v3 notice,
// for content contributed by a named third party rather than Crown-authored directly.
// None of the current England batch triggers these (dc:publisher is uniformly
// "Statute Law Database"), but the branch is real and sourced, not speculative.
const PUBLISHER_ATTRIBUTIONS = {
  'Westlaw UK': 'Westlaw UK derived from Crown Copyright material and contributed to legislation.gov.uk.',
  'British History Online': 'British History Online derived from Crown Copyright material and contributed to legislation.gov.uk.',
};

function LawSeoHead() {
  const {siteConfig} = useDocusaurusContext();
  const {frontMatter, metadata} = useDoc();
  const country = countryForPath(metadata.permalink);
  if (!country) return null;

  const url = siteConfig.url + metadata.permalink;
  let jsonLd;

  if (country.key === 'israel') {
    const {bill_id, law_id, publication_date, law_validity, title_he} = frontMatter;
    const id = String(bill_id || law_id || '');
    jsonLd = {
      '@context': 'https://schema.org',
      '@type': 'Legislation',
      name: title_he || metadata.title,
      ...(id && {legislationIdentifier: id}),
      ...(publication_date && {legislationDate: publication_date}),
      legislationJurisdiction: {'@type': 'Country', name: country.jsonLdCountryName},
      legislationStatus: law_validity === 'תקף' ? 'InForce' : law_validity || undefined,
      inLanguage: country.lang,
      url,
    };
  } else {
    const {enactment_date} = frontMatter;
    jsonLd = {
      '@context': 'https://schema.org',
      '@type': 'Legislation',
      name: metadata.title,
      legislationIdentifier: metadata.id,
      ...(enactment_date && {legislationDate: enactment_date}),
      legislationJurisdiction: {'@type': 'Country', name: country.jsonLdCountryName},
      inLanguage: country.lang,
      url,
    };
  }

  return (
    <Head>
      <html lang={country.lang} dir={country.dir} />
      <meta property="og:locale" content={country.locale} />
      <script type="application/ld+json">{JSON.stringify(jsonLd)}</script>
    </Head>
  );
}

function LawMetaBubbles() {
  const {frontMatter, metadata} = useDoc();
  const country = countryForPath(metadata.permalink);
  if (country?.key !== 'israel') return null;

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
    <div className={`${styles.lawMeta} ${styles.lawMetaRtl}`}>
      {year && <span className={styles.bubble}>{year}</span>}
      {categoryHe && <span className={styles.bubble}>{categoryHe}</span>}
      {ministerHe && <span className={styles.bubble}>{ministerHe}</span>}
      <span className={`${styles.bubble} ${isActive ? styles.active : styles.cancelled}`}>
        {statusHe}
      </span>
    </div>
  );
}

function EnglandMetaBubbles() {
  const {metadata} = useDoc();
  const country = countryForPath(metadata.permalink);
  if (country?.key !== 'england') return null;

  const meta = GENERATED_LAW_META[metadata.id] || {};
  if (!meta.year && !meta.status) return null;

  return (
    <div className={styles.lawMeta}>
      {meta.year && <span className={styles.bubble}>{meta.year}</span>}
      {meta.status && <span className={styles.bubble}>{meta.status}</span>}
    </div>
  );
}

function OglAttribution() {
  const {frontMatter, metadata} = useDoc();
  const country = countryForPath(metadata.permalink);
  if (country?.key !== 'england') return null;

  const extra = frontMatter.publisher && PUBLISHER_ATTRIBUTIONS[frontMatter.publisher];

  return (
    <div className={styles.oglAttribution}>
      <p>
        Contains public sector information from{' '}
        <a href="https://www.legislation.gov.uk/" target="_blank" rel="noopener noreferrer">
          legislation.gov.uk
        </a>
        , licensed under the{' '}
        <a
          href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"
          target="_blank"
          rel="noopener noreferrer">
          Open Government Licence v3.0
        </a>
        .
      </p>
      {extra && <p>{extra}</p>}
    </div>
  );
}

export default function DocItemContentWrapper(props) {
  return (
    <>
      <LawSeoHead />
      <LawMetaBubbles />
      <EnglandMetaBubbles />
      <Content {...props} />
      <OglAttribution />
    </>
  );
}
