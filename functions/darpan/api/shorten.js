// Short words for the special picture (Darpan, 22 Nov 2026: "put some AI into changing the actual design ... not just
// dumping all the text onto the frame"). The Studio sends the stories on the picture; Claude writes each one a short
// heading, about 40 to 60 words in plain English, and at most one exact quote. Nothing new is added: names, places, dates
// and quotes come only from the story's own words. The full story still goes out in the 2pm WhatsApp words.
// Behind the /darpan/ password (functions/darpan/_middleware.js runs first).
//   POST /darpan/api/shorten  {stories: [{year, place, heading, words}], count}
//   ->   {stories: [{heading, short, quote}]}            or 503 {why} when the Pages secret ANTHROPIC_API_KEY is not set
// The key is the GitHub secret ANTHROPIC_API_KEY, put on Pages by website-deploy.yml like the other secrets. Never in code.
const answer = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' } });
const s = (v, n) => String(v ?? '').slice(0, n);

const SCHEMA = {
  type: 'object', additionalProperties: false, required: ['stories'],
  properties: { stories: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['heading', 'short', 'quote'],
    properties: { heading: { type: 'string' }, short: { type: 'string' }, quote: { type: 'string' } } } } },
};
const SYSTEM = `You write the words for a devotional picture of BAPS Swaminarayan history. The picture is shared each day with a family WhatsApp group and is read on phones, so the words must be short, warm, clear and respectful.
For each story you are given, write:
- heading: at most 9 words, plain English, no date and no year (the picture shows the year separately).
- short: one paragraph of WORDS_RANGE words that tells what happened. Keep the order of events. Use only facts that are in the story: never add a name, number, place, date or detail that is not there. Keep proper names and honorifics exactly as written (Swamishri, Pramukh Swami Maharaj, Shriji Maharaj, Thakorji and so on). Leave out programme lists, speaker lists and links.
- quote: if the story contains a short spoken sentence that carries its heart (under 20 words), copy it exactly, without quotation marks; otherwise an empty string.
Return the stories in the same order you were given them.`;

export async function onRequestPost({ request, env }) {
  const key = env.ANTHROPIC_API_KEY || '';
  if (!key) return answer({ why: 'The short words are the first sentences of each story, because Claude is not set up on the website yet.' }, 503);
  let body = {};
  try { body = await request.json(); } catch (e) { return answer({ why: 'That was not a list of stories.' }, 400); }
  const stories = (Array.isArray(body.stories) ? body.stories : []).slice(0, 4).map((x) => ({ year: Number(x.year) || '', place: s(x.place, 120), heading: s(x.heading, 400), words: s(x.words, 12000) }));
  if (!stories.length) return answer({ why: 'No stories were sent.' }, 400);
  const count = Math.max(stories.length, Number(body.count) || 1), range = count === 1 ? '45 to 60' : count === 2 ? '35 to 50' : '25 to 35';
  const text = stories.map((x, i) => `Story ${i + 1}${x.year ? `, ${x.year}` : ''}${x.place ? `, ${x.place}` : ''}\nHeading: ${x.heading}\nStory: ${x.words}`).join('\n\n');
  let r;
  try {
    r = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: { 'x-api-key': key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json' },
      body: JSON.stringify({
        model: 'claude-opus-5-5', max_tokens: 4000,
        output_config: { effort: 'low', format: { type: 'json_schema', schema: SCHEMA } },
        system: SYSTEM.replace('WORDS_RANGE', range),
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
  return answer({ stories: parsed.stories.slice(0, stories.length).map((x) => ({ heading: s(x.heading, 200), short: s(x.short, 1200), quote: s(x.quote, 200) })) });
}
