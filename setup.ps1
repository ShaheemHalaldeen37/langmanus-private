# LangManus setup script for Windows (PowerShell)
# Run from the project root:  .\setup.ps1
#
# If you get an execution-policy error run this first (once, as Administrator):
#   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Find Python 3.11+ ────────────────────────────────────────────────────────
$python = $null
foreach ($candidate in @("python3.11", "python3.12", "python3", "python")) {
    try {
        $ver = & $candidate -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        $parts = $ver -split "\."
        if ([int]$parts[0] -ge 3 -and [int]$parts[1] -ge 11) {
            $python = $candidate
            Write-Host "Using Python $ver at $(Get-Command $candidate | Select-Object -ExpandProperty Source)"
            break
        }
    } catch { }
}

if (-not $python) {
    Write-Error "Python 3.11 or higher is required but was not found. Install it from https://www.python.org/downloads/"
    exit 1
}

# ── Create virtual environment ───────────────────────────────────────────────
if (-not (Test-Path ".venv")) {
    Write-Host "Creating .venv..."
    & $python -m venv .venv
} else {
    Write-Host ".venv already exists, skipping creation."
}

# ── Activate ─────────────────────────────────────────────────────────────────
$activateScript = ".venv\Scripts\Activate.ps1"
if (-not (Test-Path $activateScript)) {
    Write-Error "Could not find $activateScript. The venv may be corrupted — delete .venv and rerun."
    exit 1
}
& $activateScript

# ── Upgrade pip ──────────────────────────────────────────────────────────────
pip install --upgrade pip --quiet

# ── Install project dependencies ─────────────────────────────────────────────
Write-Host "Installing dependencies..."
pip install -e ".[dev]" --quiet

# ── Install Playwright Chromium ──────────────────────────────────────────────
Write-Host "Installing Playwright browsers..."
playwright install chromium

# ── Remind about .env ────────────────────────────────────────────────────────
if (-not (Test-Path ".env")) {
    Write-Host ""
    Write-Host "⚠  No .env file found."
    Write-Host "   Copy the example and fill in your API keys before starting the server:"
    Write-Host ""
    Write-Host "     copy .env.example .env"
    Write-Host "     # then edit .env with your GROQ / TAVILY keys"
    Write-Host ""
} else {
    Write-Host ".env found."
}

Write-Host ""
Write-Host "Setup complete. See instructions.md for how to start the server and web UI."
