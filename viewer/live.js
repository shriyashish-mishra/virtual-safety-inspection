// Live question box (T16, D16 route B+): ask.js answers from the evidence file, ai.js may let Gemini reword it
// (Firebase AI Logic) and the guard in ask.js keeps every verdict and number. Without firebase-config.json
// next to the site this does nothing, so the page still works offline with the stored answers.
const BASES = ["../web/", "../adapters/google/web/"]; // hosted layout, then a local checkout served from the repo root
let ask = null, ai = null;
for (const b of BASES) {
  try {
    [ask, ai] = await Promise.all([import(b + "ask.js"), import(b + "ai.js")]);
    break;
  } catch (e) { /* try the next layout */ }
}
const config = ai ? await ai.loadConfig() : null;
if (ask && ai && config) {
  const rewrite = ai.makeRewrite(config);
  window.VS_LIVE = { answer: (evidence, question) => ask.answer(evidence, question, rewrite) };
  window.dispatchEvent(new Event("vs-live"));
}
