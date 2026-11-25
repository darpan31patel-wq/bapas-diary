// Short words for the special picture (Darpan, 22 Nov 2026: "put some AI into changing the actual design ... not just
// dumping all the text onto the frame"). The Studio sends the stories on the picture; Claude writes each one a short
// heading, about 90 to 130 words for one story (fewer when several share the picture), its highlights as figures, and at
// most one exact quote (25 Nov 2026: "there was this much information but you only decided to use this small amount"). Nothing new is added: names, places, dates
// and quotes come only from the story's own words. The full story still goes out in the 2pm WhatsApp words.
// Behind the /darpan/ password (functions/darpan/_middleware.js runs first).
//   POST /darpan/api/shorten  {stories: [{year, place, heading, words}], count}
//   ->   {stories: [{heading, short, quote}]}            or 503 {why} when the Pages secret ANTHROPIC_API_KEY is not set
// The key is the GitHub secret ANTHROPIC_API_KEY, put on Pages by website-deploy.yml like the other secrets. Never in code.
const answer = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' } });
const s = (v, n) => String(v ?? '').slice(0, n);

const SCHEMA = {
  type: 'object', additionalProperties: false, required: ['stories'],
  properties: { stories: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['heading', 'short', 'quote', 'facts'],
    properties: { heading: { type: 'string' }, short: { type: 'string' }, quote: { type: 'string' },
      facts: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['big', 'small'], properties: { big: { type: 'string' }, small: { type: 'string' } } } } } } } },
};
const SYSTEM = `You write the words for a devotional picture of BAPS Swaminarayan history. The picture is shared each day with a family WhatsApp group and is read on phones, so the words must be short, warm, clear and respectful.
For each story you are given, write:
- heading: at most 9 words, plain English, no date and no year (the picture shows the year separately).
- short: WORDS_RANGE words that tell what happened (PARAS). Darpan wants the picture to carry the real information of the story, so keep its key details, not just the first sentence. Keep the order of events. Use only facts that are in the story: never add a name, number, place, date or detail that is not there. Keep proper names and honorifics exactly as written (Swamishri, Pramukh Swami Maharaj, Shriji Maharaj, Thakorji and so on). Leave out programme lists, speaker lists and links.
- facts: FACTS_RULE
- quote: if the story contains a short spoken sentence that carries its heart (under 20 words), copy it exactly, without quotation marks; otherwise an empty string.
Return the stories in the same order you were given them.`;

export async function onRequestPost({ request, env }) {
  const key = env.ANTHROPIC_API_KEY || '';
  if (!key) return answer({ why: 'The short words are the first sentences of each story, because Claude is not set up on the website yet.' }, 503);
  let body = {};
  try { body = await request.json(); } catch (e) { return answer({ why: 'That was not a list of stories.' }, 400); }
  const stories = (Array.isArray(body.stories) ? body.stories : []).slice(0, 4).map((x) => ({ year: Number(x.year) || '', place: s(x.place, 120), heading: s(x.heading, 400), words: s(x.words, 12000) }));
  if (!stories.length) return answer({ why: 'No stories were sent.' }, 400);
  const count = Math.max(stories.length, Number(body.count) || 1), range = count === 1 ? '90 to 130' : count === 2 ? '45 to 60' : '25 to 35';
  const paras = count === 1 ? 'one or two short paragraphs, separated by a blank line' : 'one paragraph';
  const facts = count === 1 ? 'if the story lists highlights, figures or key facts, up to 6 of them, each as {big, small}: big is the figure or key words exactly as written (at most 4 words, such as "8.1 million" or "100-acre"), small is the rest of that fact in at most 12 words, only from the story. Do not repeat these facts in short. If there are none, an empty list.' : 'always an empty list.';
  const text = stories.map((x, i) => `Story ${i + 1}${x.year ? `, ${x.year}` : ''}${x.place ? `, ${x.place}` : ''}\nHeading: ${x.heading}\nStory: ${x.words}`).join('\n\n');
  let r;
  try {
    r = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: { 'x-api-key': key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json' },
      body: JSON.stringify({
        model: 'claude-opus-5-5', max_tokens: 4000,
        output_config: { effort: 'low', format: { type: 'json_schema', schema: SCHEMA } },
        system: SYSTEM.replace('WORDS_RANGE', range).replace('PARAS', paras).replace('FACTS_RULE', facts),
        messages: [{ role: 'user', content: text }],
      }),
    });
  } catch (e) { return answer({ why: 'Could not reach Claude just now, so the short words are the first sentences.' }, 502); }
  const j = await r.json().catch(() => ({}));
  if (!r.ok) return answer({ why: `Claude said no (${r.status}), so the short words are the first sentences.` }, 502);
  if (j.stop_reason === 'refusal' || j.stop_reason === 'max_tokens') return answer({ why: 'Claude could not shorten these, so the short words are the first sentences.' }, 502);
  const out = (j.content || []).find((b) => b.type === 'text');
  let parsed = null; try { parsed = JSON.parse(out ? out.text : ''); } catch (e) { /* below */ }
  if (!parsed || !Array.isArray(parsed.stories)) return answer({ why: 'Claude’s answer was not readable, so the short words are the first sentences.' }, 502);
  return answer({ stories: parsed.stories.slice(0, stories.length).map((x) => ({ heading: s(x.heading, 200), short: s(x.short, 2000), quote: s(x.quote, 200), facts: (Array.isArray(x.facts) ? x.facts : []).slice(0, 6).map((f) => ({ big: s(f && f.big, 40), small: s(f && f.small, 160) })) })) });
}
