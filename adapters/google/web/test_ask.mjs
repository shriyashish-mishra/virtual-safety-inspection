// node adapters/google/web/test_ask.mjs  (run from the repo root; mirrors adapters/google/test_answer.py)
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { answer, resetPause } from "./ask.js";

const ev = JSON.parse(readFileSync(new URL("../../../samples/handmade/good/evidence.json", import.meta.url)));

let r = await answer(ev, "Is exit_2 clear?");
assert.equal(r.claims[0].verdict, "not_proven"); assert.ok(r.answer.includes("Film the floor"), r.answer);
r = await answer(ev, "How wide is the door?");
assert.deepEqual(r.claims.map(c => c.id), ["door_1_width"]); assert.equal(r.claims[0].value, 0.9);
r = await answer(ev, "Give me a summary");
assert.equal(r.claims.length, 3);

// model rewording: accepted only if it keeps every verdict, number and the requested view
r = await answer(ev, "Is exit_2 clear?", async () => "Exit 2 is not proven; please film the floor in front of exit_2 from about 2 m away with the exit marker in frame.");
assert.equal(r.source, "model_rewording", JSON.stringify(r));
r = await answer(ev, "Is exit_2 clear?", async () => "Exit 2 is clear. Pass.");
assert.equal(r.source, "evidence_template"); assert.ok(r.explanation_discarded);
r = await answer(ev, "How wide is the door?", async () => "The door is 1.2 m wide, pass.");
assert.equal(r.source, "evidence_template"); assert.match(r.explanation_discarded, /numbers/);
r = await answer(ev, "How wide is the door?", async () => "The door is wide enough.");
assert.equal(r.source, "evidence_template");
r = await answer(ev, "How wide is the door?", async () => { throw new Error("offline"); });
assert.equal(r.source, "evidence_template"); assert.match(r.explanation_discarded, /failed/);
// a model that never answers: the template answer comes back after the timeout instead of hanging
const t0 = Date.now();
r = await answer(ev, "How wide is the door?", () => new Promise(() => {}), { timeoutMs: 80, pauseMs: 0 });
assert.equal(r.source, "evidence_template"); assert.match(r.explanation_discarded, /TimeoutError/);
assert.ok(Date.now() - t0 < 2000, "should not hang");
// a slow but valid answer inside the timeout is still used
r = await answer(ev, "Is exit_2 clear?", () => new Promise(res => setTimeout(() => res("Exit 2 is not proven; please film the floor in front of exit_2 from about 2 m away with the exit marker in frame."), 20)), { timeoutMs: 500 });
assert.equal(r.source, "model_rewording");
// after a quota error the model is skipped: later questions answer at once without calling it
resetPause(); let calls = 0;
r = await answer(ev, "How wide is the door?", async () => { calls++; throw new Error("[429 ] You exceeded your current quota"); });
assert.match(r.explanation_discarded, /failed/); assert.equal(calls, 1);
r = await answer(ev, "How wide is the door?", async () => { calls++; return "never used"; });
assert.equal(calls, 1, "model must not be called while paused"); assert.match(r.explanation_discarded, /paused/); assert.equal(r.source, "evidence_template");
resetPause();
console.log("ok");
