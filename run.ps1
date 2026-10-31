$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
  python -m venv .venv
  .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
}

& .\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
