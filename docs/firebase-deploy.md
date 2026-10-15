# Deploy the viewer to Firebase Hosting (T16, D16 route B+)

Written 14 Oct by Shriya for Kaushal, who owns D16 and the Firebase project. This puts the static viewer, its demo data and the three synthetic clips' answers online on the free Spark plan. It does NOT yet call Gemini: that needs the Firebase SDK (a dependency, Shriya's yes) and Kaushal's AI Logic setup. Nothing here needs a key or a card. Steps marked UNVERIFIED have not been run by anyone.

## What is in the repo
- `firebase.json`: hosting only, serves `hosting-dist/`. No project id is committed.
- `scripts/build_hosting.py`: copies `viewer/` and `samples/` into `hosting-dist/` (git-ignored) and adds a root page that opens `?clip=clip1_clear`. RAN 14 Oct: 50 files, 353 KB; the folder served locally with `python3 -m http.server` shows the viewer with the checker result, plan, frames and Q&A chips.

## Steps (Kaushal, in your own terminal)
1. Install the Firebase CLI yourself (it is a tool on your machine, not a repo dependency) and run `firebase login` with your account. UNVERIFIED on this project.
2. In the repo root: `firebase use --add`, pick your Spark-plan project, give it an alias. This writes `.firebaserc`; do not commit it unless the team agrees the project id may be public.
3. `python3 scripts/build_hosting.py`
4. `firebase deploy --only hosting`. It prints the Hosting URL. UNVERIFIED.
5. Open the URL logged out (private window), try `?clip=clip2_blocked` and `?clip=clip3_unseen`, and note the link in docs/SUBMISSION.md.

## Limits to know
- Static files only (D16). Spark's Hosting allowance was read from Google's page on 13 Oct: 10 GB storage and 360 MB a day. This site is about 0.35 MB.
- The viewer's Q&A chips show the stored answers; the live question box needs `?api=` or the future Firebase AI Logic call. `viewer/vs-guard.js` is ready so a model reword can be checked in the page.
- Whether Hack2skill counts static Hosting plus AI Logic as "deployed" is UNVERIFIED (Kaushal asked them on 14 Oct).
- Redeploy after any change to `viewer/` or `samples/`: run steps 3 and 4 again.

## Deployed 15 Oct 2026 (Kaushal)
- Project `virtual-safety-hallucinati` (display name "Virtual Safety"), Spark plan, no billing, created with `npx firebase-tools projects:create`. Deployed with `npx firebase-tools deploy --only hosting --project virtual-safety-hallucinati` (no `.firebaserc`, nothing committed about the project).
- URL: https://virtual-safety-hallucinati.web.app . VERIFIED 15 Oct: the viewer opens at `/viewer/?clip=clip2_blocked` in a real browser with no login (checked from a browser signed in to nothing for this site), shows exit_1_clear FAIL 0.7 m with checker PASS, and the chip "Is the exit clear?" shows the stored answer ("fail. The nearest obstacle is 0.7 m from the exit"). No console errors. clip3_unseen files and the demo index return 200.
- Known issue (not fixed): the root page `/` redirects to `viewer/?clip=clip1_clear` and drops any query, so `/?clip=clip2_blocked` shows clip 1. Use `/viewer/?clip=clip2_blocked` and `/viewer/?clip=clip3_unseen`. The redirect is in `scripts/build_hosting.py` (Shriya's).
- NOT done: the live Gemini reword. `viewer/index.html` does not import `adapters/google/web/ask.js` or `ai.js`; `FIREBASE_CONFIG` in `ai.js` is still null; Firebase AI Logic and App Check are not set up on the project. The page answers only from stored answers.
- `hosting-dist/` is tracked in git although `.gitignore` lists it; a rebuild changes `hosting-dist/viewer/demo/index.json`. Not touched here.

## Live Gemini works (15 Oct 2026, Kaushal)
- VERIFIED 15 Oct on https://virtual-safety-hallucinati.web.app/viewer/?clip=clip2_blocked : typing "Is the exit clear?" in the question box returned "The exit_1_clear check failed due to a blocked exit measured at 0.7 m (confidence 0.9, frames [106, 112, 117])." with the note "Reworded by Gemini; the guard checked it keeps every verdict, number and the requested view." It took roughly 10 to 20 seconds.
- Model id `gemini-3.8-flash` is accepted on the free plan through Firebase AI Logic, Gemini Developer API provider, no billing. A direct request once returned HTTP 500 "high demand"; the page then falls back to the evidence answer.
- How: `viewer/live.js` reads the untracked `firebase-config.json`, `ai.js` calls the model, `ask.js` guards the reword. No key in git.
- **App Check is NOT enforced, by choice (Kaushal, 15 Oct).** Reason: App Check needs a reCAPTCHA Enterprise (Google Cloud Fraud Defense) key, and the console asked for billing, which the team ruled out. Done in the console: App Check > APIs > Firebase AI Logic, baseline protection Unenforced, replay protection Disabled (status "Basic - Unenforced"). Google says this leaves the Gemini API open to abuse; here the damage is capped by the free quota because there is no billing, and a reword cannot change a verdict (the guard).
- **Deadline:** Google says that from 2 Nov 2026 App Check enforcement is required for AI Logic and cannot be turned off. After that date the live box falls back to the evidence answer; do not plan a demo that depends on live Gemini after it. Re-enable enforcement before any wider release.
