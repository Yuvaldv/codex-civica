import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'Codex Civica',
  tagline: 'Civic legislation, made readable.',
  favicon: 'img/favicon.ico',

  future: {
    v4: true,
  },

  url: 'https://yuvaldv.github.io',
  baseUrl: '/codex-civica/',

  organizationName: 'Yuvaldv',
  projectName: 'codex-civica',
  trailingSlash: false,

  onBrokenLinks: 'warn',
  onBrokenAnchors: 'ignore',

  markdown: {
    hooks: {
      onBrokenMarkdownLinks: 'warn',
    },
  },

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  clientModules: ['./src/clientModules/lawSort.js'],

  presets: [
    [
      'classic',
      {
        docs: {
          path: '../laws/israel',
          routeBasePath: 'laws/israel',
          sidebarPath: './sidebars.ts',
          showLastUpdateTime: false,
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  plugins: [
    [
      '@docusaurus/plugin-client-redirects',
      {
        // Every previously indexed /laws/<id> URL (111 laws, indexed before the
        // Phase 10 route rebase) must keep resolving. Derived from whatever
        // exists at build time rather than a hardcoded id list, so it never
        // drifts from the actual laws/israel/ content.
        createRedirects(existingPath: string) {
          if (existingPath.startsWith('/laws/israel/')) {
            return [existingPath.replace('/laws/israel/', '/laws/')];
          }
          return [];
        },
      },
    ],
  ],

  themeConfig: {
    image: 'img/social-card.jpg',
    colorMode: {
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'Codex Civica',
      items: [
        {
          type: 'html',
          position: 'left',
          value: '<a href="/codex-civica/laws/israel" class="navbar__link navbar-flag" title="Israel">🇮🇱</a>',
        },
        {
          type: 'html',
          position: 'right',
          className: 'navbar-groupby-item',
          value: '<div class="navbar-sortby" id="navbar-sortby" style="display:none"><span class="navbar-sortby__label">Group by</span><select id="law-sort-select" class="navbar-sortby__select"><option value="year">Year</option><option value="category">Category</option><option value="minister">Ministry</option><option value="status">Status</option></select></div>',
        },
        {
          href: 'https://justsocial.io',
          label: 'by JustSocial',
          position: 'left',
        },
        {
          href: 'https://github.com/Yuvaldv/codex-civica',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Legal',
          items: [
            {label: 'Terms & Conditions', to: '/terms'},
            {label: 'Privacy Policy', to: '/privacy'},
            {label: 'Accessibility', to: '/accessibility'},
          ],
        },
      ],
      copyright: `Codex Civica — content derived from public legislation of the State of Israel`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
