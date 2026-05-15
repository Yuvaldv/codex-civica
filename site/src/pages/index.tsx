import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import styles from './index.module.css';

export default function Home(): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout description="חקיקה ישראלית נגישה לכל — קרא, חפש והבן את החוק">
      <main className={styles.hero}>
        <div className={styles.heroInner}>
          <h1 className={styles.heroTitle}>{siteConfig.title}</h1>
          <p className={styles.heroTagline}>{siteConfig.tagline}</p>
          <p className={styles.heroDesc}>
            חוקי מדינת ישראל כטקסט מובנה, נגיש וניתן לחיפוש.
            <br />
            המקור: כנסת ישראל. העיבוד: צינור המרה פתוח.
          </p>
          <Link className={styles.heroButton} to="/laws/147449">
            לכל החוקים ←
          </Link>
        </div>
      </main>
    </Layout>
  );
}
