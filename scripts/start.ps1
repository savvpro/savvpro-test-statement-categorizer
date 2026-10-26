$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    if (-not (Test-Path '.venv\Scripts\python.exe')) {
        throw 'Run .\scripts\setup.ps1 first.'
    }
    & '.\.venv\Scripts\python.exe' scripts/run.py
} finally { Pop-Location }
