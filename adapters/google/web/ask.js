// Browser port of adapters/google/answer.py and the guard in explain.py (T16, route B+ of D16).
// No imports, so it runs in a browser and under node. The verdict, value and requested view come from
// evidence.json; a model may only reword, and guard() discards any rewrite that changes a fact.
const VERDICT_WORDS = { pass: "pass", fail: "fail", not_proven: "not proven" };
const TYPE_HINTS = { blocked_exit: ["exit", "blocked", "egress"], door_clear_width: ["door", "width", "wide"] };
const VERDICT_RE = { pass: /\bpass(es|ed)?\b/, fail: /\bfail(s|ed|ure)?\b/, not_proven: /\bnot[ _]proven\b/ };
const NUM_RE = /\d+(?:\.\d+)?/g;

export const PROMPT = "Reword the safety-inspection answer below in one or two plain sentences for a facility manager. " +
  "Do not change any verdict, number or unit. Do not add facts. If a view is missing, keep the request.\n\n";

export function pickClaims(evidence, question) {
  const q = question.toLowerCase().replaceAll("_", " ");
  const claims = evidence.claims;
  const byId = claims.filter(c => q.includes(c.id.toLowerCase().split("_").slice(0, 2).join(" ")));
  if (byId.length) return byId;
  const words = new Set(q.match(/[a-z]+/g) || []);
  const byType = claims.filter(c => (TYPE_HINTS[c.type] || []).some(w => words.has(w)));
  return byType.length ? byType : claims;
}

export function describe(claim, evidence) {
  if (claim.verdict === "not_proven") {
    const ask = (evidence.requested_view || {}).description || "a view that covers it";
    return `${claim.id}: not proven. The evidence does not cover it. Missing view: ${ask}.`;
  }
  return `${claim.id} (${claim.type}): ${VERDICT_WORDS[claim.verdict]}, measured ${claim.value} ${claim.unit} ` +
    `(confidence ${claim.confidence}, frames [${claim.frame_ids.join(", ")}]).`;
}

// Returns null if the rewrite is acceptable, else the reason it was discarded.
export function guard(rewrite, template, claims) {
  const low = rewrite.toLowerCase();
  for (const [verdict, re] of Object.entries(VERDICT_RE)) {
    const wanted = claims.some(c => c.verdict === verdict);
    const found = re.test(low);
    if (wanted && !found) return `missing verdict ${verdict}`;
    if (found && !wanted) return `adds verdict ${verdict}`;
  }
  const allowed = new Set(template.match(NUM_RE) || []);
  const extra = (rewrite.match(NUM_RE) || []).filter(n => !allowed.has(n));
  if (extra.length) return `numbers not in the evidence: ${[...new Set(extra)].sort()}`;
  for (const c of claims) {
    if (c.value === null || c.value === undefined) continue;
    const forms = [String(c.value), Number.isInteger(c.value) ? c.value.toFixed(1) : String(c.value)];
    if (!forms.some(f => rewrite.includes(f))) return `missing value ${c.value}`;
  }
  if (claims.some(c => c.verdict === "not_proven") && !low.includes("view") && !low.includes("film")) return "requested view dropped";
  return null;
}

// A model that never answers must not leave the page on "Asking..." (the free tier stalls and returns 503 at times).
export const REWRITE_TIMEOUT_MS = 7000;
function withTimeout(promise, ms) {
  let timer;
  const stop = new Promise((_, reject) => { timer = setTimeout(() => { const e = new Error("no answer in " + ms + " ms"); e.name = "TimeoutError"; reject(e); }, ms); });
  return Promise.race([promise, stop]).finally(() => clearTimeout(timer));
}

// rewrite: optional async (templateText) => reworded text. Any failure, including a timeout, leaves the template answer standing.
export async function answer(evidence, question, rewrite, { timeoutMs = REWRITE_TIMEOUT_MS } = {}) {
  const claims = pickClaims(evidence, question);
  const template = claims.map(c => describe(c, evidence)).join(" ");
  const out = {
    room_id: evidence.room_id,
    claims: claims.map(({ id, type, verdict, value, unit }) => ({ id, type, verdict, value, unit })),
    answer: template, source: "evidence_template",
  };
  if (rewrite) {
    try {
      const text = await withTimeout(Promise.resolve().then(() => rewrite(template)), timeoutMs);
      const problem = guard(text, template, claims);
      if (problem === null) { out.answer = text; out.source = "model_rewording"; } else out.explanation_discarded = problem;
    } catch (e) {
      out.explanation_discarded = `model call failed: ${e && e.name ? e.name : "error"}`;
    }
  }
  return out;
}
