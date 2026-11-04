// Visitors dashboard for the private Interaction page (Darpan, 4 Nov 2026: "I want a dashboard showing analytics from
// cloudflare, showing how many visitors, where from and what tab was most used"). A Cloudflare Pages Function:
//   GET /api/visitors?key=WORD&days=30   {days: [[date, visitors, pageViews]], countries: [[code, n]], tabs: [[tab, n]], tabsFrom, found: [[site, n]], devices: [[kind, n]], notes}
// It asks Cloudflare's own analytics (GraphQL API) with a read only token kept as the ANALYTICS_TOKEN Pages secret
// (from the GitHub secret CF_ANALYTICS_TOKEN; the deploy also puts ZONE_ID and ACCOUNT_ID). Same word as the page
// (MISSED_KEY). Nothing about any one visitor is stored by us: these are Cloudflare's totals.
//   Visitors and countries: the zone's daily totals (httpRequests1dGroups), up to 30 days.
//   Tabs: Cloudflare Web Analytics page views (rumPageloadEventsAdaptiveGroups) when it is switched on for the site,
//   else the zone's last 24 hours of page requests (httpRequestsAdaptiveGroups).

const answer = (body, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
});

const TABS = [
  ['', 'Today'], ['calendar', 'Calendar'], ['search', 'Search'], ['travels', 'Travels'], ['through-the-years', 'Through the years'],
  ['then-and-now', 'Legacy'], ['darshan', 'Darshan'], ['about', 'About'], ['day', 'Share a day'], ['year', 'Year in review'],
  ['favourites', 'Favourites'], ['player', 'TV player'], ['screensaver', 'Screensaver'], ['offline', 'Save for travelling'],
];
const TAB_NAME = Object.fromEntries(TABS);
const PRIVATE = new Set(['darpan', 'interaction', 'missed', 'api', 'data', 'gu', 'share', 'fonts', 'about-img']);
function tabOf(path) {
  const seg = String(path || '/').split('?')[0].replace(/^\/+/, '').split('/')[0].replace(/\.html$/, '').toLowerCase();
  if (seg === 'index') return 'Today';
  if (PRIVATE.has(seg) || /\.(js|css|json|jpg|jpeg|png|webp|svg|ico|txt|xml|webmanifest|woff2?)$/.test(seg)) return null;
  return TAB_NAME[seg] || null;
}

async function ask(env, query, variables) {
  const r = await fetch('https://api.cloudflare.com/client/v4/graphql', {
    method: 'POST', headers: { Authorization: `Bearer ${env.ANALYTICS_TOKEN}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, variables }),
  });
  const j = await r.json().catch(() => ({}));
  if (j.errors && j.errors.length) throw new Error(j.errors.map(e => e.message).join('; '));
  if (!r.ok || !j.data) throw new Error(`Cloudflare answered ${r.status}`);
  return j.data;
}

export async function onRequestGet({ request, env }) {
  const url = new URL(request.url), key = url.searchParams.get('key') || '';
  if (!env.MISSED_KEY || key !== env.MISSED_KEY) return answer({ error: 'wrong word' }, 403);
  if (!env.ANALYTICS_TOKEN || !env.ZONE_ID) return answer({ error: 'no token yet' }, 503);
  const days = Math.min(30, Math.max(1, parseInt(url.searchParams.get('days'), 10) || 30));
  const now = new Date(), since = new Date(now.getTime() - days * 864e5);
  const notes = [];
  const out = { range: days, days: [], countries: [], tabs: [], tabsFrom: '', found: [], devices: [], notes };

  // 1. visitors, page views and countries, day by day
  try {
    const d = await ask(env, `query($z: String!, $from: Date!) { viewer { zones(filter: {zoneTag: $z}) {
      httpRequests1dGroups(limit: 40, filter: {date_geq: $from}, orderBy: [date_ASC]) {
        dimensions { date } uniq { uniques } sum { pageViews countryMap { clientCountryName requests } } } } } }`,
      { z: env.ZONE_ID, from: since.toISOString().slice(0, 10) });
    const groups = (((d.viewer || {}).zones || [])[0] || {}).httpRequests1dGroups || [];
    const countries = {};
    for (const g of groups) {
      out.days.push([g.dimensions.date, g.uniq.uniques, g.sum.pageViews]);
      for (const c of g.sum.countryMap || []) countries[c.clientCountryName] = (countries[c.clientCountryName] || 0) + c.requests;
    }
    out.countries = Object.entries(countries).sort((a, b) => b[1] - a[1]).slice(0, 25);
  } catch (e) { notes.push('Visitors: ' + e.message); }

  // 2. which tab: Web Analytics (real page views, up to 30 days) when it is on, else the last 24 hours of page requests
  const tabs = {};
  if (env.ACCOUNT_ID) {
    try {
      const d = await ask(env, `query($a: String!, $since: Time!) { viewer { accounts(filter: {accountTag: $a}) {
        rumPageloadEventsAdaptiveGroups(limit: 500, filter: {datetime_geq: $since, requestHost_like: "%bapas-diary.com"}, orderBy: [count_DESC]) {
          count dimensions { requestPath } } } } }`, { a: env.ACCOUNT_ID, since: since.toISOString() });
      for (const g of (((d.viewer || {}).accounts || [])[0] || {}).rumPageloadEventsAdaptiveGroups || []) {
        const t = tabOf(g.dimensions.requestPath); if (t) tabs[t] = (tabs[t] || 0) + g.count;
      }
      if (Object.keys(tabs).length) out.tabsFrom = `page views, last ${days} days`;
    } catch (e) { notes.push('Web Analytics: ' + e.message); }
    // how people found the site (the site they came from; none = typed, a saved link or the WhatsApp app) and phone or computer
    if (out.tabsFrom) {
      try {
        const d = await ask(env, `query($a: String!, $since: Time!) { viewer { accounts(filter: {accountTag: $a}) {
          ref: rumPageloadEventsAdaptiveGroups(limit: 200, filter: {datetime_geq: $since, requestHost_like: "%bapas-diary.com"}, orderBy: [count_DESC]) {
            count dimensions { refererHost } }
          dev: rumPageloadEventsAdaptiveGroups(limit: 20, filter: {datetime_geq: $since, requestHost_like: "%bapas-diary.com"}, orderBy: [count_DESC]) {
            count dimensions { deviceType } } } } }`, { a: env.ACCOUNT_ID, since: since.toISOString() });
        const acc = ((d.viewer || {}).accounts || [])[0] || {}, found = {}, dev = {};
        for (const g of acc.ref || []) {
          const h = String(g.dimensions.refererHost || '').replace(/^www\./, '').toLowerCase();
          if (h.endsWith('bapas-diary.com')) continue;   // moving between our own pages
          const k = h || 'Typed in, saved link or WhatsApp'; found[k] = (found[k] || 0) + g.count;
        }
        for (const g of acc.dev || []) { const k = { mobile: 'Phone', desktop: 'Computer', tablet: 'Tablet' }[g.dimensions.deviceType] || 'Other'; dev[k] = (dev[k] || 0) + g.count; }
        out.found = Object.entries(found).sort((a, b) => b[1] - a[1]).slice(0, 12);
        out.devices = Object.entries(dev).sort((a, b) => b[1] - a[1]);
      } catch (e) { notes.push('How they found the site: ' + e.message); }
    }
  }
  if (!out.tabsFrom) {
    try {
      const from = new Date(now.getTime() - 864e5 + 6e4).toISOString();
      const d = await ask(env, `query($z: String!, $since: Time!) { viewer { zones(filter: {zoneTag: $z}) {
        httpRequestsAdaptiveGroups(limit: 500, filter: {datetime_geq: $since, edgeResponseContentTypeName: "html", requestSource: "eyeball"}, orderBy: [count_DESC]) {
          count dimensions { clientRequestPath } } } } }`, { z: env.ZONE_ID, since: from });
      for (const g of (((d.viewer || {}).zones || [])[0] || {}).httpRequestsAdaptiveGroups || []) {
        const t = tabOf(g.dimensions.clientRequestPath); if (t) tabs[t] = (tabs[t] || 0) + g.count;
      }
      out.tabsFrom = 'page visits, last 24 hours';
    } catch (e) { notes.push('Tabs: ' + e.message); }
  }
  out.tabs = Object.entries(tabs).sort((a, b) => b[1] - a[1]);
  return answer(out);
}
