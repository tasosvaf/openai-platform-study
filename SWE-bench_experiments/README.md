# SWE-bench Lite — Assignment Experiments

Three ready-to-run [SWE-bench Lite](https://www.swebench.com/) experiments at increasing
difficulty (**easy → medium → hard**). Each one applies a patch to a real GitHub project
inside a Docker container and runs that project's test suite to check whether the issue is
resolved.

This folder is **answer-free**: the shipped `predictions/*.jsonl` contain an **empty**
`model_patch` for each of the three instances, so agents can't peek at a reference fix. Your
job (or an agent's) is to fill in each `model_patch` and then run the harness. The gold
(reference) patches and any prior result reports are kept **outside** the repo, under
`/Users/tasosvaf/repos/testRepos/experiment_results/SWE-bench_results/answers/`, purely for
after-the-fact checking. See [Use your own model](#use-your-own-model).

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
| `predictions/easy.jsonl` | Prediction slot for the easy instance (empty `model_patch`). |
| `predictions/medium.jsonl` | Prediction slot for the medium instance (empty `model_patch`). |
| `predictions/hard.jsonl` | Prediction slot for the hard instance (empty `model_patch`). |
| `harness/` | Comparison harness: prompts + `swe_experiment_runner.py` that exports results. |
| `run_experiment.ps1` | Runner for Windows (PowerShell). |
| `run_experiment.sh` | Runner for macOS / Linux (bash). |
| `run_all.sh` | macOS + Colima one-shot wrapper (starts Colima, sets `DOCKER_HOST`, runs levels). |
| `.gitignore` | Ignores `.venv/`, `logs/`, and report `*.assignment-*.json`. |

Each `predictions/*.jsonl` file has one line in the standard SWE-bench format (shipped with an
empty patch you fill in):

```json
{"instance_id": "<repo>__<name>-<number>", "model_name_or_path": "GPT 5.4-mini", "model_patch": ""}
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

From inside this `SWE-bench_experiments/` folder:

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

### macOS + Colima one-shot wrapper (recommended on Apple Silicon)

`run_all.sh` wraps the whole flow so you don't have to remember the Colima steps. It:

1. Starts the Colima Docker VM if it isn't already running.
2. Points `DOCKER_HOST` at Colima's socket (the `swebench` Python SDK needs this —
   without it you get a `FileNotFoundError` on `/var/run/docker.sock`).
3. Activates the local `.venv`.
4. Runs `run_experiment.sh` with `--local`.

```bash
./run_all.sh                    # all three levels (2 workers), builds images locally
./run_all.sh easy               # just easy
./run_all.sh medium             # just medium
./run_all.sh hard               # just hard
./run_all.sh all 3              # all three, 3 workers
./run_all.sh easy 2 --no-local  # Intel Mac: pull prebuilt x86_64 images instead of building
./run_all.sh --help             # show all options
```

Options:

| Option | Default | Meaning |
|--------|:-------:|---------|
| `LEVEL` (1st positional) | `all` | `easy` \| `medium` \| `hard` \| `all` |
| `WORKERS` (2nd positional) | `2` | Max parallel workers |
| `--no-local` | off | Skip `--local` (pull prebuilt images; Intel Macs only) |
| `--cpu N` | `8` | CPUs to give Colima **when it starts it** |
| `--memory N` | `12` | Memory (GiB) for Colima on start |
| `--disk N` | `100` | Disk (GiB) for Colima on start |

> The `--cpu` / `--memory` / `--disk` flags only apply the first time Colima is started;
> if Colima is already running they're ignored (stop it with `colima stop` to resize).

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

- **Summary report** in this folder: `<model_name_or_path>.assignment-<level>.json` — counts
  of instances submitted / completed / **resolved** (git-ignored; treated as a result).
- **Detailed logs** under `logs/run_evaluation/assignment-<level>/<model_name_or_path>/<instance_id>/`:
  - `run_instance.log` — build & apply steps
  - `test_output.txt` — the actual test run
  - `report.json` — per-instance pass/fail
  - `patch.diff` — the patch that was applied

A run also prints a summary table to the console at the end.

---

## Use your own model

The shipped predictions start with an **empty** `model_patch`. To evaluate a real model/agent,
edit the relevant `predictions/<level>.jsonl` and set **`model_patch`** to your model's unified
diff (keep the same `instance_id`; set `model_name_or_path` to your model's name, e.g.
`GPT 5.4-mini`). Then run the harness. An empty/incorrect patch simply reports the instance as
unresolved. You can also add more instances (one JSON object per line) and point
`--predictions_path` at that file.

The original gold patches (for checking your work) live outside the repo at
`/Users/tasosvaf/repos/testRepos/experiment_results/SWE-bench_results/answers/predictions/`.

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
