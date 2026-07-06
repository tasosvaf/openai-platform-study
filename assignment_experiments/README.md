# SWE-bench Lite — Assignment Experiments

Three ready-to-run [SWE-bench Lite](https://www.swebench.com/) experiments at increasing
difficulty (**easy → medium → hard**). Each one applies a patch to a real GitHub project
inside a Docker container and runs that project's test suite to check whether the issue is
resolved.

The three patches shipped here are the **gold** (reference) patches, so a correct setup
resolves all three. That makes this folder a portable, end-to-end **setup validator**: clone
it onto any machine, follow the steps below, and confirm the whole harness works before you
plug in your own model. See [Use your own model](#use-your-own-model) to swap them out.

This folder is **self-contained** — you do *not* need to clone the SWE-bench source repo. The
`swebench` PyPI package provides everything.

---

## The three experiments

| Level | Instance ID | Repo | Δ lines | The bug |
|-------|-------------|------|:------:|---------|
| 🟢 easy   | `matplotlib__matplotlib-23563` | matplotlib | 1  | `'Line3D' object has no attribute '_verts3d'` |
| 🟡 medium | `sympy__sympy-22005`           | sympy      | 6  | detection of infinite solution request |
| 🔴 hard   | `django__django-11019`         | django     | 76 | Merging 3+ media objects throws unnecessary `MediaOrderConflictWarnings` |

Difficulty is the size of the gold code change (lines changed). All SWE-bench Lite tasks
edit a single file; the three here span the dataset from the smallest (1 line) to the
largest (76 lines) fix, and deliberately use three different projects so you exercise three
different Docker build environments. See [How difficulty was chosen](#how-difficulty-was-chosen).

---

## Folder contents

| Path | What it is |
|------|-----------|
| `README.md` | This file. |
| `requirements.txt` | The single dependency (`swebench`). |
| `predictions/easy.jsonl` | Prediction (gold patch) for the easy instance. |
| `predictions/medium.jsonl` | Prediction (gold patch) for the medium instance. |
| `predictions/hard.jsonl` | Prediction (gold patch) for the hard instance. |
| `run_experiment.ps1` | Runner for Windows (PowerShell). |
| `run_experiment.sh` | Runner for macOS / Linux (bash). |
| `.gitignore` | Ignores `.venv/`, `logs/`, and report `*.json`. |

Each `predictions/*.jsonl` file has one line in the standard SWE-bench format:

```json
{"instance_id": "<repo>__<name>-<number>", "model_name_or_path": "gold", "model_patch": "<unified diff>"}
```

---

## Prerequisites (per machine)

1. **Docker**, installed and running. The harness builds/pulls Linux containers.
   - Windows / macOS: [Docker Desktop](https://www.docker.com/products/docker-desktop) (Windows needs the WSL 2 backend).
   - Linux: Docker Engine ([post-install steps](https://docs.docker.com/engine/install/linux-postinstall/) to run without `sudo`).
   - Recommended resources: **8+ CPUs, 16 GB+ RAM**, and **≥ 120 GB free disk** (Docker Desktop → Settings → Resources).
   - Verify: `docker run hello-world`
2. **Python 3.10** (used to create the virtual environment below).
   - Get it from [python.org](https://www.python.org/downloads/release/python-31018/), `pyenv`, or a package manager.
3. **Internet access** — the first run downloads the dataset (from Hugging Face) and Docker images.

> **Apple Silicon (M-series) Macs:** prebuilt images are x86_64, so pass `-Local` / `--local`
> to build images locally instead. (See the run commands below.)

---

## Setup (once per machine)

From inside this `assignment_experiments/` folder:

### Windows (PowerShell)

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> If PowerShell blocks activation, run once:
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`

### macOS / Linux (bash/zsh)

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
chmod +x run_experiment.sh   # first time only
```

The runner scripts auto-detect this `.venv`, so you don't strictly need to keep it activated
when running — but activating it is the simplest mental model.

---

## Run the experiments

### With the helper scripts (recommended)

**Windows:**
```powershell
.\run_experiment.ps1 -Level easy            # one level
.\run_experiment.ps1 -Level all             # all three (default)
.\run_experiment.ps1 -Level all -MaxWorkers 3
.\run_experiment.ps1 -Level hard -Local     # Apple Silicon / build locally
```

**macOS / Linux:**
```bash
./run_experiment.sh easy          # one level
./run_experiment.sh               # all three (default)
./run_experiment.sh all 3         # all three, 3 workers
./run_experiment.sh hard 2 --local
```

### Or call the harness directly

```bash
python -m swebench.harness.run_evaluation \
    --dataset_name princeton-nlp/SWE-bench_Lite \
    --predictions_path predictions/easy.jsonl \
    --max_workers 2 \
    --cache_level env \
    --run_id assignment-easy
```

Key flags: `--run_id` is required and names the run; `--max_workers` should stay
`<= min(0.75 × CPU cores, 24)`; `--cache_level env` (the default) is a good speed/disk
tradeoff (`instance` is fastest but can use ~2 TB across the full dataset).

> The **first** run for each project is the slow one — it downloads/builds the base and
> environment images (several GB per repo) and can take a few to tens of minutes. Later runs
> reuse cached images and are much faster.

---

## Reading the results

After a run you get:

- **Summary report** in this folder: `gold.assignment-<level>.json` — counts of instances
  submitted / completed / **resolved**. A correct setup shows `resolved = 1` per level.
- **Detailed logs** under `logs/run_evaluation/assignment-<level>/gold/<instance_id>/`:
  - `run_instance.log` — build & apply steps
  - `test_output.txt` — the actual test run
  - `report.json` — per-instance pass/fail
  - `patch.diff` — the patch that was applied

A run also prints a summary table to the console at the end.

---

## Use your own model

To evaluate a real model/agent instead of the gold patch, edit the relevant
`predictions/<level>.jsonl` and replace **`model_patch`** with your model's unified diff
(keep the same `instance_id`; set `model_name_or_path` to your model's name). Then re-run.
An empty/incorrect patch simply reports the instance as unresolved. You can also add more
instances (one JSON object per line) and point `--predictions_path` at that file.

---

## Cleanup

Docker images accumulate. To reclaim space:

```bash
docker system df          # see usage
docker container prune    # remove stopped containers
docker system prune -a    # remove all unused images/containers (aggressive)
```

You can also pass `--clean True` to the harness to remove instance images as it goes.

---

## How difficulty was chosen

Selected programmatically from all 300 `princeton-nlp/SWE-bench_Lite` test instances:

- Every Lite task edits exactly **one file**, so difficulty is ranked by the number of lines
  the gold patch changes (added + removed).
- **easy** = the smallest change (1 line), **hard** = the largest in the dataset (76 lines),
  **medium** = around the dataset median (~6 lines).
- The three were forced to come from **three different repositories** (matplotlib, sympy,
  django) so each exercises a distinct build/test environment.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Docker CLI not found` / connection errors | Start Docker; verify with `docker run hello-world`. |
| `'swebench' not installed` | Activate `.venv` and `pip install -r requirements.txt`. |
| Very slow / out-of-disk on first run | Free disk or raise Docker's disk limit; keep `--cache_level env`. |
| Apple Silicon build/pull errors | Add `-Local` (PowerShell) or `--local` (bash). |
| Build failures mid-run | Inspect `logs/build_images/` and `logs/run_evaluation/`. |

No local Docker at all? You can evaluate in the cloud instead with
`--modal true` (see `modal setup`) or the hosted [`sb-cli`](https://github.com/swe-bench/sb-cli).
