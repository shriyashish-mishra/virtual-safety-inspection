"""The browser guard (viewer/vs-guard.js) must give the same answers as the Python original (T16).
Runs both on every demo clip, several questions and a set of good and bad rewrites. Skips without node."""
import json, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "adapters" / "google"))
import answer, explain  # noqa: E402

QUESTIONS = ["Is the exit blocked?", "How wide is the door?", "exit_1 status", "Is the room okay?", "tell me about the door width"]


def rewrites(template):
    return [template, "Everything is safe here.", "The exit passes with 5 metres to spare.", "Nothing to report.",
            template.replace("pass", "fail"), template + " The room is compliant.", template.upper()]


def main():
    if not shutil.which("node"):
        print("skip: node not installed"); return
    cases = []
    for d in sorted((ROOT / "viewer" / "demo").iterdir()):
        if (d / "evidence.json").exists():
            ev = json.loads((d / "evidence.json").read_text())
            for q in QUESTIONS:
                claims = answer.pick_claims(ev, q)
                tpl = " ".join(answer.describe(c, ev) for c in claims)
                for rw in rewrites(tpl):
                    cases.append({"ev": ev, "q": q, "rw": rw, "claims": [c["id"] for c in claims], "tpl": tpl, "guard": explain.guard(rw, tpl, claims)})
    js = "const g=require(process.argv[1]);const cases=JSON.parse(require('fs').readFileSync(0,'utf8'));" \
         "console.log(JSON.stringify(cases.map(c=>{const cl=g.pickClaims(c.ev,c.q);return{claims:cl.map(x=>x.id),tpl:g.template(c.ev,c.q),guard:g.guard(c.rw,c.tpl,cl)}})))"
    out = subprocess.run(["node", "-e", js, str(ROOT / "viewer" / "vs-guard.js")], input=json.dumps(cases), capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    got = json.loads(out.stdout)
    bad = [(c["q"], c["rw"][:50], c["tpl"], g) for c, g in zip(cases, got) if (c["claims"], c["tpl"], c["guard"]) != (g["claims"], g["tpl"], g["guard"])]
    assert not bad, f"{len(bad)} differ, first: {bad[0]}"
    print(f"ok: {len(cases)} cases agree between Python and JavaScript")


if __name__ == "__main__":
    main()
