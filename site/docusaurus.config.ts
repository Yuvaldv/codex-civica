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

  markdown: {
    hooks: {
      onBrokenMarkdownLinks: 'warn',
    },
  },

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          path: '../laws/israel',
          routeBasePath: 'laws',
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

  themeConfig: {
    image: 'img/social-card.jpg',
    colorMode: {
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'Codex Civica',
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'lawsSidebar',
          position: 'left',
          label: '🇮🇱',
        },
        {
          href: 'https://justsocial.io',
          label: 'JustSocial',
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
      copyright: `Codex Civica — content derived from public legislation of the State of Israel`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
