<#
.SYNOPSIS
    DocBot task runner — replaces Makefile for cross-platform support.
.DESCRIPTION
    Usage: .\tasks.ps1 <command>
    Commands: setup, run, clean, doctor, test
#>

param(
    [Parameter(Position = 0)]
    [ValidateSet("setup", "run", "clean", "doctor", "test", "help")]
    [string]$Command = "help"
)

function Invoke-Setup {
    uv sync
    Write-Host "`n✓ Dependencies installed." -ForegroundColor Green
    Write-Host "  Downloading EasyOCR weights (first time only)..." -ForegroundColor Cyan
    uv run python -c "import easyocr; easyocr.Reader(['en'], gpu=False)"
    Write-Host "  EasyOCR weights downloaded." -ForegroundColor Green
    Write-Host "  Copy .env.local.example to .env.local and add your NVIDIA_API_KEY." -ForegroundColor Yellow
}

function Invoke-Run {
    uv run streamlit run app.py
}

function Invoke-Clean {
    $dirs = @(".venv", "__pycache__", "core/__pycache__", "tests/__pycache__",
              "data/uploads", "data/cache", "data/chroma")
    foreach ($dir in $dirs) {
        if (Test-Path $dir) {
            Remove-Item -Recurse -Force $dir
        }
    }
    Write-Host "✓ Cleaned." -ForegroundColor Green
}

function Invoke-Doctor {
    Write-Host "=== DocBot Environment Check ===" -ForegroundColor Cyan
    uv run python -c @"
from core.config import get_settings
s = get_settings()
print(f'  API Key  : {s.nvidia_api_key[:8]}...{s.nvidia_api_key[-4:]}')
print(f'  Base URL : {s.nvidia_base_url}')
print(f'  Model    : {s.nvidia_model}')
print(f'  Route    : {s.nvidia_route_model}')
print(f'  Embed    : {s.nvidia_embed_model}')
"@
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Config check failed. Is .env.local configured?" -ForegroundColor Red
        exit 1
    }
    Write-Host "`n  Running NIM connectivity smoke test..." -ForegroundColor Cyan
    uv run pytest tests/test_smoke_nim.py::test_json_mode_roundtrip -x -q
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Smoke test failed." -ForegroundColor Red
        exit 1
    }
    Write-Host "`n✓ Doctor passed — environment is healthy." -ForegroundColor Green
}

function Invoke-Test {
    uv run pytest tests/ -x -q
}

function Show-Help {
    Write-Host @"

  DocBot Task Runner
  ==================
  Usage: .\tasks.ps1 <command>

  Commands:
    setup   Install dependencies (uv sync)
    run     Launch Streamlit app
    clean   Remove generated/cached files
    doctor  Verify environment + NIM connectivity
    test    Run all tests

"@ -ForegroundColor Cyan
}

switch ($Command) {
    "setup"  { Invoke-Setup }
    "run"    { Invoke-Run }
    "clean"  { Invoke-Clean }
    "doctor" { Invoke-Doctor }
    "test"   { Invoke-Test }
    "help"   { Show-Help }
}
