<#
.SYNOPSIS
    DocBot task runner — replaces Makefile for cross-platform support.
.DESCRIPTION
    Usage: .\tasks.ps1 <command>
    Commands: setup, run, clean, doctor, test
#>

param(
    [Parameter(Position = 0)]
    [ValidateSet("setup", "run", "clean", "doctor", "test", "demo", "help")]
    [string]$Command = "help"
)

function Invoke-Setup {
    uv sync
    Write-Host "`nDependencies installed." -ForegroundColor Green
    Write-Host "  Downloading EasyOCR weights (first time only)..." -ForegroundColor Cyan
    uv run python -c 'import easyocr; easyocr.Reader([''en''], gpu=False)'
    if ($LASTEXITCODE -ne 0) {
        Write-Host "EasyOCR bootstrap failed." -ForegroundColor Red
        exit 1
    }
    Write-Host "  EasyOCR weights downloaded." -ForegroundColor Green
    Write-Host "  Installing Playwright browsers..." -ForegroundColor Cyan
    uv run playwright install chromium
    Write-Host "  Playwright Chromium installed." -ForegroundColor Green
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
    Write-Host "Cleaned." -ForegroundColor Green
}

function Invoke-Doctor {
    Write-Host "=== DocBot Environment Check ===" -ForegroundColor Cyan
    $configCheckScript = @(
        'from core.config import get_settings',
        's = get_settings()',
        'print(f''  API Key  : {s.nvidia_api_key[:8]}...{s.nvidia_api_key[-4:]}'')',
        'print(f''  Base URL : {s.nvidia_base_url}'')',
        'print(f''  Model    : {s.nvidia_model}'')',
        'print(f''  Route    : {s.nvidia_route_model}'')',
        'print(f''  Embed    : {s.nvidia_embed_model}'')'
    ) -join "`n"
    uv run python -c $configCheckScript
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Config check failed. Is .env.local configured?" -ForegroundColor Red
        exit 1
    }
    Write-Host "`n  Running NIM connectivity smoke test..." -ForegroundColor Cyan
    uv run pytest tests/test_smoke_nim.py::test_json_mode_roundtrip -x -q
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Smoke test failed." -ForegroundColor Red
        exit 1
    }
    Write-Host "`nDoctor passed - environment is healthy." -ForegroundColor Green
}

function Invoke-Test {
    uv run pytest tests/ -x -q
}

function Invoke-Demo {
    Write-Host "=== DocBot E2E Demo Dry-Run ===" -ForegroundColor Cyan
    $streamlitProcess = Start-Process -FilePath "uv" -ArgumentList "run", "streamlit", "run", "app.py", "--server.headless", "true" -PassThru -WindowStyle Hidden
    Write-Host "  Waiting for Streamlit server..." -ForegroundColor Cyan
    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8501/_stcore/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($response.StatusCode -eq 200) { $ready = $true; break }
        } catch { }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) {
        Write-Host "Streamlit server failed to start within 30s." -ForegroundColor Red
        if (-not $streamlitProcess.HasExited) { Stop-Process -Id $streamlitProcess.Id -Force }
        exit 1
    }
    Write-Host "  Streamlit server ready. Running E2E tests..." -ForegroundColor Green
    uv run pytest tests/test_e2e_demo.py -x -q
    $testExit = $LASTEXITCODE
    if (-not $streamlitProcess.HasExited) { Stop-Process -Id $streamlitProcess.Id -Force }
    if ($testExit -ne 0) {
        Write-Host "E2E demo dry-run failed." -ForegroundColor Red
        exit 1
    }
    Write-Host "`nE2E demo dry-run passed." -ForegroundColor Green
}

function Show-Help {
    Write-Host "" -ForegroundColor Cyan
    Write-Host "  DocBot Task Runner" -ForegroundColor Cyan
    Write-Host "  ==================" -ForegroundColor Cyan
    Write-Host "  Usage: .\tasks.ps1 COMMAND" -ForegroundColor Cyan
    Write-Host "" -ForegroundColor Cyan
    Write-Host "  Commands:" -ForegroundColor Cyan
    Write-Host "    setup   Install dependencies (uv sync)" -ForegroundColor Cyan
    Write-Host "    run     Launch Streamlit app" -ForegroundColor Cyan
    Write-Host "    clean   Remove generated/cached files" -ForegroundColor Cyan
    Write-Host "    doctor  Verify environment + NIM connectivity" -ForegroundColor Cyan
    Write-Host "    test    Run all tests" -ForegroundColor Cyan
    Write-Host "    demo    Run automated E2E demo dry-run (Playwright)" -ForegroundColor Cyan
    Write-Host "" -ForegroundColor Cyan
}

switch ($Command) {
    "setup"  { Invoke-Setup }
    "run"    { Invoke-Run }
    "clean"  { Invoke-Clean }
    "doctor" { Invoke-Doctor }
    "test"   { Invoke-Test }
    "demo"   { Invoke-Demo }
    "help"   { Show-Help }
}
