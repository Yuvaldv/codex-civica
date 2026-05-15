import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import styles from './index.module.css';

export default function Home(): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout description="Laws of the world — readable, searchable, open.">
      <main className={styles.hero}>
        <div className={styles.heroInner}>
          <h1 className={styles.heroTitle}>{siteConfig.title}</h1>
          <p className={styles.heroTagline}>{siteConfig.tagline}</p>

          <div className={styles.pickSection}>
            <h2 className={styles.pickTitle}>Pick a country</h2>
            <div className={styles.countryGrid}>
              <Link className={styles.countryCard} to="/laws/147449">
                <span className={styles.countryFlag}>🇮🇱</span>
                <span className={styles.countryName}>Israel</span>
              </Link>
            </div>
          </div>
        </div>
      </main>
    </Layout>
  );
}
