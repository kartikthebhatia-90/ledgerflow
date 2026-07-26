param(
    [Parameter(Mandatory = $true)]
    [string]$Target
)

$ErrorActionPreference = "Stop"
$Source = Split-Path -Parent $MyInvocation.MyCommand.Path
$Source = (Resolve-Path $Source).Path
$Target = (Resolve-Path $Target).Path

if ($Source -eq $Target) {
    throw "The update package and existing app must be different folders."
}
if (-not (Test-Path (Join-Path $Target "run_app.py"))) {
    throw "The target does not look like a LedgerFlow app: $Target"
}

Write-Host "Applying LedgerFlow 3.3.1 hotfix while preserving .env and data..." -ForegroundColor Cyan

Copy-Item (Join-Path $Source "backend") $Target -Recurse -Force
Copy-Item (Join-Path $Source "agent") $Target -Recurse -Force
Copy-Item (Join-Path $Source "analytics") $Target -Recurse -Force
Copy-Item (Join-Path $Source "docs") $Target -Recurse -Force

$FrontendTarget = Join-Path $Target "frontend"
$DistTarget = Join-Path $FrontendTarget "dist"
if (Test-Path $DistTarget) {
    Remove-Item $DistTarget -Recurse -Force
}
Copy-Item (Join-Path $Source "frontend\dist") $FrontendTarget -Recurse -Force
Copy-Item (Join-Path $Source "frontend\src") $FrontendTarget -Recurse -Force
Copy-Item (Join-Path $Source "frontend\public") $FrontendTarget -Recurse -Force
Copy-Item (Join-Path $Source "frontend\index.html") $FrontendTarget -Force
Copy-Item (Join-Path $Source "frontend\package.json") $FrontendTarget -Force
Copy-Item (Join-Path $Source "frontend\package-lock.json") $FrontendTarget -Force
Copy-Item (Join-Path $Source "frontend\tsconfig.json") $FrontendTarget -Force
Copy-Item (Join-Path $Source "frontend\tsconfig.app.json") $FrontendTarget -Force
Copy-Item (Join-Path $Source "frontend\tsconfig.node.json") $FrontendTarget -Force
Copy-Item (Join-Path $Source "frontend\vite.config.ts") $FrontendTarget -Force

foreach ($File in @("run_app.py", "VERSION", "CHANGELOG.md", "README.md")) {
    Copy-Item (Join-Path $Source $File) $Target -Force
}

$ObsoleteAgent = Join-Path $Target "backend\app\department_agents.py"
if (Test-Path $ObsoleteAgent) {
    Remove-Item $ObsoleteAgent -Force
}

Write-Host "Update applied. Existing business.db, source files and .env were preserved." -ForegroundColor Green
Write-Host ""
Write-Host "Next commands:"
Write-Host "  cd `"$Target`""
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  pip install -r .\backend\requirements.txt"
Write-Host "  python .\run_app.py"
Write-Host ""
Write-Host "Confirm Overview says 'build 3.3.1', then start the manual Clippy overview."
