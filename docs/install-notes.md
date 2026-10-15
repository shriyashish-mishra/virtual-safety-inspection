# Install and compute notes

What was run, on which machine, and what failed. VERIFIED means someone ran it and saw the result; UNVERIFIED means nobody has.

## Python
Use Python 3.11 for the model environments (VERIFIED 15 Oct on macOS). The rules, checker, viewer and tests need only the standard library (Python 3.12 or newer is fine); the synthetic-room renderer and the reconstruction script need `numpy` and `opencv-python`.

## VGGT (VERIFIED 15 Oct, macOS, Python 3.11, throwaway venv)
```
python3.11 -m venv .venv-vggt && source .venv-vggt/bin/activate
pip install -r reconstruct/requirements-vggt.txt
git clone https://github.com/facebookresearch/vggt && pip install -e vggt
python -c "from vggt.models.vggt import VGGT"
```
Installs and imports without a GPU. A model run needs a GPU.

## Depth Anything 3
Does NOT install on a Mac (VERIFIED 15 Oct): `xformers` has no macOS wheel and fails to build. It was run on a free Kaggle notebook (GPU T4) instead: `git clone --depth 1 https://github.com/ByteDance-Seed/Depth-Anything-3`, `pip install xformers`, `pip install --ignore-requires-python --no-deps -e <clone>`, then its other dependencies plus `addict`, which its code uses but its pyproject.toml omits. On a 14.5 GiB T4 it ran out of memory at 32 and 12 frames and worked at 8; VGGT took 32 frames in 12.2 s with 8.77 GB. VGGT is the recommendation for the prototype (docs/spike-report.md).

## Free GPU
A Kaggle notebook gives two Tesla T4 (about 15 GB each) and a weekly GPU quota (108,000 s a week, VERIFIED 12 Oct). Python 3.13 and a recent Torch are preinstalled there, so the pinned `torch==2.3.1` is not needed on Kaggle. A dataset has to be attached in the notebook editor for each run.

## Licences of the model weights (read from the READMEs)
- VGGT: the original checkpoint is non-commercial; a separate commercial checkpoint needs an application.
- Depth Anything 3: most weights are CC BY-NC 4.0 (non-commercial); the Base, Small, Metric-Large and Mono-Large models are Apache 2.0.
- This repository is MIT-licensed and contains no model weights. Which weights a deployment may use is for the deployer to check.

## Never in git
No passwords, tokens or API keys, and no large clips. The Firebase web config lives in an untracked `firebase-config.json` (see docs/firebase-deploy.md).
