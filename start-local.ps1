$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Cannot create virtual environment' }
}
& .venv/Scripts/python.exe -c "import importlib.util,sys; sys.exit(0 if all(importlib.util.find_spec(m) for m in ['numpy','sklearn','ziglang']) else 1)"
if ($LASTEXITCODE -ne 0) {
    & .venv/Scripts/python.exe -m pip install -r requirements-local.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
}
if (-not (Test-Path -LiteralPath 'models/demo.forest') -or -not (Test-Path -LiteralPath 'build/ai-vids.exe')) {
    & .venv/Scripts/python.exe tools/prepare.py
    if ($LASTEXITCODE -ne 0) { throw 'Build/train failed' }
}
& .venv/Scripts/python.exe tools/serve.py
