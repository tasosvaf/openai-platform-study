#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Run a SWE-bench Lite assignment experiment: easy | medium | hard | all.

.PARAMETER Level
    Which experiment to run. One of: easy, medium, hard, all (default: all).

.PARAMETER MaxWorkers
    Parallel Docker workers. Keep <= min(0.75 * CPU cores, 24). Default: 2.

.PARAMETER Local
    Build evaluation images locally instead of pulling prebuilt x86_64 images.
    Required on Apple Silicon (M-series) Macs. Adds `--namespace ''`.

.EXAMPLE
    ./run_experiment.ps1 -Level easy
    ./run_experiment.ps1 -Level all -MaxWorkers 3
    ./run_experiment.ps1 -Level hard -Local
#>
param(
    [ValidateSet('easy', 'medium', 'hard', 'all')]
    [string]$Level = 'all',
    [int]$MaxWorkers = 2,
    [string]$Dataset = 'princeton-nlp/SWE-bench_Lite',
    [string]$CacheLevel = 'env',
    [switch]$Local
)

Set-Location $PSScriptRoot

# Prefer the folder-local .venv if it exists, otherwise fall back to PATH python.
$venvPy = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$py = if (Test-Path $venvPy) { $venvPy } else { 'python' }

# Pre-flight checks (output captured so nothing noisy leaks to the console)
$null = & $py -c "import swebench" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: 'swebench' is not installed in this Python ($py)." -ForegroundColor Red
    Write-Host "       Activate your .venv, then:  pip install -r requirements.txt   (see README.md > Setup)" -ForegroundColor Red
    exit 1
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Docker CLI not found. Install Docker and start it (verify with: docker run hello-world)." -ForegroundColor Red
    exit 1
}

$levels = if ($Level -eq 'all') { @('easy', 'medium', 'hard') } else { @($Level) }

$failed = @()
foreach ($lvl in $levels) {
    $preds = Join-Path $PSScriptRoot "predictions\$lvl.jsonl"
    Write-Host "`n=== Running '$lvl' experiment ($preds) ===" -ForegroundColor Cyan
    $cliArgs = @(
        '-m', 'swebench.harness.run_evaluation',
        '--dataset_name', $Dataset,
        '--predictions_path', $preds,
        '--max_workers', $MaxWorkers,
        '--cache_level', $CacheLevel,
        '--run_id', "assignment-$lvl"
    )
    if ($Local) { $cliArgs += @('--namespace', '') }
    & $py @cliArgs
    if ($LASTEXITCODE -ne 0) { $failed += $lvl }
}

if ($failed.Count -gt 0) {
    Write-Host "`nWARNING: non-zero exit for: $($failed -join ', ')" -ForegroundColor Yellow
    exit 1
}
Write-Host "`nDone. Summary report(s): gold.assignment-*.json  |  Detailed logs: logs\run_evaluation\" -ForegroundColor Green
