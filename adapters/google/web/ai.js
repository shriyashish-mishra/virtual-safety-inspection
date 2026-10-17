// Gemini rewording through Firebase AI Logic, Gemini Developer API provider (D16, route B+).
// The browser calls Gemini directly: no server, no API key in this file. The Firebase web config is
// not a secret, but App Check must be on in the Firebase console or the calls are rejected (UNVERIFIED
// which provider; see README). Pass the result to ask.answer(evidence, question, rewrite).
import { initializeApp } from "https://www.gstatic.com/firebasejs/13.0.0/firebase-app.js";
import { initializeAppCheck, ReCaptchaEnterpriseProvider } from "https://www.gstatic.com/firebasejs/13.0.0/firebase-app-check.js";
import { getAI, getGenerativeModel, GoogleAIBackend } from "https://www.gstatic.com/firebasejs/13.0.0/firebase-ai.js";
import { PROMPT } from "./ask.js";

// The Firebase web config is read at run time from firebase-config.json next to the site (untracked, written by
// scripts/build_hosting.py from a local file). Without it rewording is off and every answer is the template text.
// An optional "appCheckSiteKey" field in that file is the public site key of a Google Cloud Fraud Defense
// (reCAPTCHA Enterprise) web key, used for App Check; reCAPTCHA Classic is deprecated.
export const FIREBASE_CONFIG = null;

export async function loadConfig(url = "../firebase-config.json") {
  try {
    const r = await fetch(url, { cache: "no-store" });
    return r.ok ? await r.json() : null;
  } catch (e) {
    return null;
  }
}
// Model id taken from the Firebase AI Logic web sample read 14 Oct; whether the free tier allows it is UNVERIFIED.
export const MODEL = "gemini-3.8-flash";

export function makeRewrite(config = FIREBASE_CONFIG, modelId = MODEL) {
  if (!config) return null;
  const { appCheckSiteKey, ...firebaseConfig } = config;
  const app = initializeApp(firebaseConfig);
  if (appCheckSiteKey) initializeAppCheck(app, { provider: new ReCaptchaEnterpriseProvider(appCheckSiteKey), isTokenAutoRefreshEnabled: true });
  // thinkingBudget 0: measured 17 Oct on the live project, gemini-3.8-flash answered in 8.4 to 9.0 s by default and in 4.3 s with
  // thinking off, and a reword of a one-line answer needs no reasoning. thinkingLevel is rejected (HTTP 400) on this model.
  const model = getGenerativeModel(getAI(app, { backend: new GoogleAIBackend() }), { model: modelId, generationConfig: { thinkingConfig: { thinkingBudget: 0 } } });
  return async template => (await model.generateContent(PROMPT + template)).response.text().trim();
}
