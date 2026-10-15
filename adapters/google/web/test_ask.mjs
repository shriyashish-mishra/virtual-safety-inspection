// node adapters/google/web/test_ask.mjs  (run from the repo root; mirrors adapters/google/test_answer.py)
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { answer } from "./ask.js";

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
console.log("ok");
