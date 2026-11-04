// Visitors to bapas-diary.com, for Darpan's private dashboard at /darpan/visitors/ (Darpan, 4 Nov 2026: "a dashboard
// showing analytics from cloudfare, showing how many visitors, where from and what tab was most used"). Website only:
// nothing here touches the daily 2pm picture. Behind the /darpan/ password (functions/darpan/_middleware.js runs first).
//
//   GET /darpan/api/visitors?days=7|30|90
//
// It asks Cloudflare's own analytics (the GraphQL Analytics API) with a read only key, the Pages secret
// CF_ANALYTICS_TOKEN (the deploy copies it from the GitHub secret of the same name; never in the code). Two sources:
//   site traffic   every visit to the domain, kept by Cloudflare for every site: visitors and page views each day,
//                  and the countries the requests came from
//   Web Analytics  Cloudflare's privacy friendly page counter (no cookies), once it is switched on for the Pages
//                  project: which page (tab) each visit opened, countries by visits, phone or computer, and the
//                  site people came from (WhatsApp, Google ...)
// Either one may be missing; the answer then says why in plain words and the page shows what it has.

const GQL = 'https://api.cloudflare.com/client/v4/graphql';
const answer = (body, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'private, no-store' },
});
const ours = (h) => /(^|\.)bapas-diary\.com$/.test(h || '') && !/^photos\./.test(h || '');
const day = (d) => d.toISOString().slice(0, 10);

async function ask(token, query, variables) {
  const r = await fetch(GQL, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, variables }),
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok || (j.errors && j.errors.length)) {
    throw new Error((j.errors && j.errors.map((e) => e.message).join('; ')) || `Cloudflare said ${r.status}`);
  }
  return j.data;
}

const ZONE_Q = `query($zone: String!, $since: Date!, $until: Date!) { viewer { zones(filter: {zoneTag: $zone}) {
  httpRequests1dGroups(limit: 100, filter: {date_geq: $since, date_leq: $until}, orderBy: [date_ASC]) {
    dimensions { date }
    sum { pageViews requests countryMap { clientCountryName requests } }
    uniq { uniques }
  } } } }`;

// one question per kind; requestHost is asked too so only bapas-diary.com is counted
const RUM_Q = `query($acct: String!, $since: Time!, $until: Time!) { viewer { accounts(filter: {accountTag: $acct}) {
  paths: rumPageloadEventsAdaptiveGroups(limit: 1000, filter: {datetime_geq: $since, datetime_lt: $until}) {
    count sum { visits } dimensions { requestHost requestPath } }
  countries: rumPageloadEventsAdaptiveGroups(limit: 1000, filter: {datetime_geq: $since, datetime_lt: $until}) {
    count sum { visits } dimensions { requestHost countryName } }
  devices: rumPageloadEventsAdaptiveGroups(limit: 100, filter: {datetime_geq: $since, datetime_lt: $until}) {
    count sum { visits } dimensions { requestHost deviceType } }
  days: rumPageloadEventsAdaptiveGroups(limit: 1000, filter: {datetime_geq: $since, datetime_lt: $until}) {
    count sum { visits } dimensions { requestHost date } }
  refs: rumPageloadEventsAdaptiveGroups(limit: 1000, filter: {datetime_geq: $since, datetime_lt: $until}) {
    count sum { visits } dimensions { requestHost refererHost } }
} } }`;

const add = (m, k, v) => m.set(k, (m.get(k) || 0) + v);
const list = (m, key) => [...m].map(([k, v]) => ({ [key]: k, ...v })).sort((a, b) => b.visits - a.visits || b.views - a.views);

async function siteTraffic(env, since, until) {
  const d = await ask(env.CF_ANALYTICS_TOKEN, ZONE_Q, { zone: env.CF_ZONE_ID, since: day(since), until: day(until) });
  const rows = (d.viewer.zones[0] || {}).httpRequests1dGroups || [];
  const countries = new Map();
  for (const r of rows) for (const c of r.sum.countryMap || []) add(countries, c.clientCountryName, c.requests);
  return {
    days: rows.map((r) => ({ date: r.dimensions.date, visitors: r.uniq.uniques, views: r.sum.pageViews })),
    countries: [...countries].map(([code, requests]) => ({ code, requests })).sort((a, b) => b.requests - a.requests),
  };
}

async function webAnalytics(env, since, until) {
  // Cloudflare answers at most about a month per question, so longer spans are asked in 30 day pieces
  const parts = [];
  for (let a = new Date(since); a < until; a = new Date(a.getTime() + 30 * 864e5)) {
    const b = new Date(Math.min(a.getTime() + 30 * 864e5, until.getTime()));
    parts.push(ask(env.CF_ANALYTICS_TOKEN, RUM_Q, { acct: env.CF_ACCOUNT_ID, since: a.toISOString(), until: b.toISOString() }));
  }
  const paths = new Map(), countries = new Map(), devices = new Map(), days = new Map(), refs = new Map();
  const put = (m, k, r) => { const o = m.get(k) || { visits: 0, views: 0 }; o.visits += r.sum.visits; o.views += r.count; m.set(k, o); };
  for (const d of await Promise.all(parts)) {
    const a = d.viewer.accounts[0] || {};
    for (const r of a.paths || []) if (ours(r.dimensions.requestHost)) put(paths, r.dimensions.requestPath || '/', r);
    for (const r of a.countries || []) if (ours(r.dimensions.requestHost)) put(countries, r.dimensions.countryName || '', r);
    for (const r of a.devices || []) if (ours(r.dimensions.requestHost)) put(devices, r.dimensions.deviceType || 'other', r);
    for (const r of a.days || []) if (ours(r.dimensions.requestHost)) put(days, r.dimensions.date, r);
    // the site the visitor came from (WhatsApp, Google ...); moving between our own tabs is not counted
    for (const r of a.refs || []) if (ours(r.dimensions.requestHost) && !ours(r.dimensions.refererHost)) put(refs, r.dimensions.refererHost || '', r);
  }
  return {
    paths: list(paths, 'path'),
    countries: list(countries, 'code'),
    devices: list(devices, 'type'),
    refs: list(refs, 'host'),
    days: list(days, 'date').sort((a, b) => a.date.localeCompare(b.date)),
  };
}

export async function onRequestGet({ request, env }) {
  if (!env.CF_ANALYTICS_TOKEN) return answer({ ready: false, why: 'no-key' });
  const n = [7, 30, 90].includes(Number(new URL(request.url).searchParams.get('days')))
    ? Number(new URL(request.url).searchParams.get('days')) : 30;
  const until = new Date();
  const since = new Date(until.getTime() - n * 864e5);
  const [site, web] = await Promise.allSettled([
    env.CF_ZONE_ID ? siteTraffic(env, since, until) : Promise.reject(new Error('no zone')),
    env.CF_ACCOUNT_ID ? webAnalytics(env, since, until) : Promise.reject(new Error('no account')),
  ]);
  const out = { ready: true, days: n, since: day(since), until: day(until) };
  if (site.status === 'fulfilled') out.site = site.value; else out.siteError = String(site.reason.message || site.reason);
  if (web.status === 'fulfilled') out.web = web.value; else out.webError = String(web.reason.message || web.reason);
  return answer(out);
}
