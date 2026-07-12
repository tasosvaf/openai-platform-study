# Environment setup — macOS

Commands to set up and run the SWE-bench Lite experiments on a Mac.
Run everything from inside this `SWE-bench_experiments/` folder.

## 1. Prerequisites

- **Docker Desktop for Mac** — installed and running (verify below).
- **Python 3.10** — from python.org, `pyenv`, or Homebrew (`brew install python@3.10`).
- Internet access (first run downloads the dataset + Docker images).

```bash
# Verify Docker is installed and running
docker run hello-world

# Verify Python 3.10 is available
python3.10 --version
```

## 2. Create the virtual environment and install dependencies

> Do NOT reuse a `.venv` built on Windows — create a fresh one on the Mac.

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
chmod +x run_experiment.sh   # first time only
```

Quick check that the harness imports:

```bash
python -c "import swebench; print('swebench ok')"
```

## 3. Run the experiments

### Intel Mac (x86_64) — pulls prebuilt images

```bash
./run_experiment.sh easy          # one level
./run_experiment.sh               # all three (default)
./run_experiment.sh all 3         # all three, 3 workers
```

### Apple Silicon (M-series) — build images locally with --local

```bash
./run_experiment.sh easy 2 --local
./run_experiment.sh all 2 --local
./run_experiment.sh hard 2 --local
```

## 4. Read the results

- Summary report in this folder: `gold.assignment-<level>.json` (a correct setup shows `resolved = 1` per level).
- Detailed logs: `logs/run_evaluation/assignment-<level>/gold/<instance_id>/`.

## 5. Cleanup (Docker images accumulate)

```bash
docker system df          # see usage
docker container prune    # remove stopped containers
docker system prune -a    # aggressive: remove all unused images/containers
```
