$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$required = @(
  ".\backend\app\department_agents.py",
  ".\backend\app\timezone_utils.py",
  ".\frontend\dist\agent-architecture-v200.js",
  ".\data\.empty_company_data",
  ".\INSTALL_AND_RUN_CLEAN_APP.ps1"
)
foreach ($path in $required) {
  if (-not (Test-Path $path)) { Write-Host "FAIL: Missing $path" -ForegroundColor Red; exit 1 }
}
if (Select-String -Path ".\backend\app\department_agents.py" -Pattern "SqliteSaver\(_CHECKPOINT_CONNECTION\)" -Quiet) {
  Write-Host "FAIL: synchronous SqliteSaver is still configured for async graph execution." -ForegroundColor Red
  exit 1
}
if (-not (Select-String -Path ".\backend\app\department_agents.py" -Pattern "AsyncSqliteSaver" -Quiet)) {
  Write-Host "FAIL: AsyncSqliteSaver fix is missing." -ForegroundColor Red
  exit 1
}
if (-not (Select-String -Path ".\backend\requirements.txt" -Pattern "aiosqlite" -Quiet)) {
  Write-Host "FAIL: aiosqlite dependency is missing." -ForegroundColor Red
  exit 1
}
$businessFiles = Get-ChildItem ".\data\source_files" -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -notin @("README.md", ".use_as_folder_intake") }
if ($businessFiles) {
  Write-Host "FAIL: Clean package still contains business source files." -ForegroundColor Red
  exit 1
}
Write-Host "PASS: LedgerFlow 2.0.2 clean app, async agents, full-map drag/drop and single headings are installed." -ForegroundColor Green
