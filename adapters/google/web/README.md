# Browser route for the Google entry (T16, D16 route B+)

Firebase Hosting on the free Spark plan serves the viewer. The page answers from `evidence.json` in the
browser (`ask.js`, a port of `../answer.py` and its guard) and may reword the answer with Gemini through
Firebase AI Logic (`ai.js`, Gemini Developer API provider). There is no server and no API key in git.

    node adapters/google/web/test_ask.mjs        # prints ok; same cases as ../test_answer.py

Use it from a page:

    import { answer } from "./ask.js";
    import { makeRewrite } from "./ai.js";       // returns null until FIREBASE_CONFIG is filled in
    const result = await answer(evidence, "Is exit_2 clear?", makeRewrite());

With no Firebase config, or if the model call fails or breaks the guard, the answer is the template text
built from the evidence, so the page still works offline. The verdict never comes from the model.

## Setup state (15 Oct, Kaushal)
- DONE: Firebase project `virtual-safety-hallucinati` (Spark, no billing) with a Web app; the page is deployed at https://virtual-safety-hallucinati.web.app (see docs/firebase-deploy.md).
- DONE in code: `viewer/live.js` loads `ask.js` and `ai.js` and adds a question box when a `firebase-config.json` sits next to the site. That file is NOT in git: `scripts/build_hosting.py` copies it from the repo root (git-ignored) into `hosting-dist/`. Add `"appCheckSiteKey": "<site key of a Fraud Defense (reCAPTCHA Enterprise) web key>"` to it for App Check; the key is public.
- TO DO in the Firebase console (needs the project owner's Google account): AI Services > AI Logic > Get started with the Gemini Developer API provider; a Fraud Defense (reCAPTCHA Enterprise) web key in the Google Cloud console for the hosted domain, then App Check > Apps > register the web app with that key. Until then the box answers from the evidence and says the model call failed (checked locally on 15 Oct: "model call failed: FirebaseError").
- Then redeploy (`python3 scripts/build_hosting.py`, `npx firebase-tools deploy --only hosting --project virtual-safety-hallucinati`) and test one question on the live URL; that is T16's done-when.

## UNVERIFIED
- That the Cup accepts static hosting plus client-side Gemini as "deployed" (D16 option C: Shriyashish Mishra asks Hack2skill).
- That AI Logic works on Spark without a billing step (Firebase's FAQ says yes, its get-started page does not say).
- That `gemini-3.8-flash` (the id in Firebase's web sample, read 14 Oct) is allowed on the free tier, and the free rate limits.
- Which App Check provider is free and works for a demo.
- The SDK is loaded from gstatic at version 13.0.0 (the npm latest on 14 Oct; both files returned HTTP 200); it has not run in a browser here.
