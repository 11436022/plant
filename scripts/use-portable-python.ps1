$pythonRoot = "D:\git\Portable Python-3.10.5 x64\App\Python"
$pythonExe = Join-Path $pythonRoot "python.exe"
$scriptsDir = Join-Path $pythonRoot "Scripts"

if (-not (Test-Path $pythonExe)) {
    throw "Portable Python not found: $pythonExe"
}

$env:PATH = "$pythonRoot;$scriptsDir;$env:PATH"
$env:PYTHONUTF8 = "1"

Write-Host "Portable Python environment loaded."
Write-Host "python: $pythonExe"
Write-Host "scripts: $scriptsDir"
Write-Host ""
Write-Host "You can now run:"
Write-Host "  python --version"
Write-Host "  python -m uvicorn app.main:app --reload"
Write-Host "  python -m alembic current"
