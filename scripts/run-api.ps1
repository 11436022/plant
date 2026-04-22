$projectRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "use-portable-python.ps1")

Set-Location $projectRoot
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
