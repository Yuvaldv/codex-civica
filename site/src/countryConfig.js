// Per-instance jurisdiction config, keyed by the docs route prefix.
// Adding a new country/subdivision (e.g. laws/uk/scotland/ -> /laws/scotland)
// means adding one entry here — no other file should hardcode a country name.
export const COUNTRIES = [
  {
    key: 'israel',
    pathPrefix: '/laws/israel/',
    lang: 'he',
    dir: 'rtl',
    locale: 'he_IL',
    jsonLdCountryName: 'Israel',
    flag: '🇮🇱',
    label: 'Israel',
  },
  {
    key: 'england',
    pathPrefix: '/laws/england/',
    lang: 'en',
    dir: 'ltr',
    locale: 'en_GB',
    jsonLdCountryName: 'United Kingdom',
    flag: '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
    label: 'England',
  },
];

// Matches a doc permalink (or any /laws/-containing path) to its country
// config. Not anchored to the start: metadata.permalink includes the site's
// baseUrl (e.g. /codex-civica/laws/israel/2000001), which varies by deploy
// target, so this looks for the prefix anywhere in the path instead of
// re-deriving baseUrl here. Each instance's own root doc (slug: '/')
// permalinks to the bare prefix with no trailing slash (.../laws/israel,
// not .../laws/israel/) -- match that with endsWith.
export function countryForPath(pathname) {
  if (!pathname) return null;
  return COUNTRIES.find(
    c => pathname.endsWith(c.pathPrefix.slice(0, -1)) || pathname.includes(c.pathPrefix)
  ) || null;
}
