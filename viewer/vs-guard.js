/* Browser port of adapters/google/answer.py (pick_claims, describe) and adapters/google/explain.py (guard) (T16).
   Needed because on Firebase Hosting the page calls Gemini itself, so the checks that keep the model from changing a
   verdict must run in the page. No dependencies. tests/test_guard_parity.py runs this file and the Python original
   on the same inputs and fails if they differ; change both together.
   Known limit: JSON turns 1.0 into 1, so whole numbers are printed with one decimal (fmt) to match Python's str(1.0). */
(function (root) {
  const VERDICT_WORDS = { pass: "pass", fail: "fail", not_proven: "not proven" };
  const TYPE_HINTS = { blocked_exit: ["exit", "blocked", "egress"], door_clear_width: ["door", "width", "wide"] };
  const VERDICT_RE = { pass: /\bpass(es|ed)?\b/, fail: /\bfail(s|ed|ure)?\b/, not_proven: /\bnot[ _]proven\b/ };
  const NUM_RE = /\d+(?:\.\d+)?/g;
  const OVERCLAIM_RE = /\b(safe|unsafe|compliant|compliance|certified|hazard[- ]free)\b/;

  const fmt = v => (typeof v === "number" && Number.isInteger(v)) ? v.toFixed(1) : String(v);
  const list = a => "[" + a.join(", ") + "]";

  function pickClaims(evidence, question) {
    const q = question.toLowerCase().replace(/_/g, " ");
    const claims = evidence.claims;
    const byId = claims.filter(c => q.includes(c.id.toLowerCase().split("_").slice(0, 2).join(" ")));
    if (byId.length) return byId;
    const words = new Set(q.match(/[a-z]+/g) || []);
    const byType = claims.filter(c => (TYPE_HINTS[c.type] || []).some(w => words.has(w)));
    return byType.length ? byType : claims;
  }

  function describe(claim, evidence) {
    const word = VERDICT_WORDS[claim.verdict];
    if (claim.verdict === "not_proven") {
      const ask = (evidence.requested_view || {}).description || "a view that covers it";
      return `${claim.id}: not proven. The evidence does not cover it. Missing view: ${ask}.`;
    }
    const tail = `(confidence ${fmt(claim.confidence)}, frames ${list(claim.frame_ids)}).`;
    const val = `${fmt(claim.value)} ${claim.unit}`;
    if (claim.type === "blocked_exit") {
      return claim.verdict === "pass"
        ? `${claim.id} (${claim.type}): ${word}. No obstacle found within ${val} of the exit ${tail}`
        : `${claim.id} (${claim.type}): ${word}. The nearest obstacle is ${val} from the exit ${tail}`;
    }
    return `${claim.id} (${claim.type}): ${word}, measured ${val} ${tail}`;
  }

  /* null if the rewrite is acceptable, else the reason it must be discarded (then show the template text) */
  function guard(rewrite, template, claims) {
    const low = rewrite.toLowerCase();
    for (const [verdict, re] of Object.entries(VERDICT_RE)) {
      const wanted = claims.some(c => c.verdict === verdict);
      const found = re.test(low);
      if (wanted && !found) return `missing verdict ${verdict}`;
      if (found && !wanted) return `adds verdict ${verdict}`;
    }
    if (OVERCLAIM_RE.test(low) && !OVERCLAIM_RE.test(template.toLowerCase())) return "claims beyond the evidence (safe or compliant)";
    const allowed = new Set(template.match(NUM_RE) || []);
    const extra = [...new Set(rewrite.match(NUM_RE) || [])].filter(n => !allowed.has(n));
    if (extra.length) return `numbers not in the evidence: [${extra.sort().map(n => "'" + n + "'").join(", ")}]`;
    for (const c of claims) if (c.value !== null && c.value !== undefined && !rewrite.includes(fmt(c.value))) return `missing value ${fmt(c.value)}`;
    if (claims.some(c => c.verdict === "not_proven") && !low.includes("view") && !low.includes("film")) return "requested view dropped";
    return null;
  }

  /* Template answer for a question, plus the guard's verdict on an optional model rewording. */
  function answer(evidence, question, rewrite) {
    const claims = pickClaims(evidence, question);
    const template = claims.map(c => describe(c, evidence)).join(" ");
    const out = { room_id: evidence.room_id, claims, answer: template, source: "evidence_template" };
    if (rewrite) {
      const problem = guard(rewrite, template, claims);
      if (problem === null) { out.answer = rewrite; out.source = "model_rewording"; } else out.explanation_discarded = problem;
    }
    return out;
  }

  const api = { pickClaims, describe, guard, answer, template: (e, q) => pickClaims(e, q).map(c => describe(c, e)).join(" ") };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.VSGuard = api;
})(typeof window !== "undefined" ? window : globalThis);
