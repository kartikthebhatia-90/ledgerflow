$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$required = @(
  ".\backend\app\department_agents.py",
  ".\backend\app\agent_context.py",
  ".\agent\BUSINESS_ANALYST_METHOD.md",
  ".\agent\ASSISTANT_PERSONAS.json",
  ".\frontend\dist\ledgerflow-v203-runtime.js",
  ".\frontend\dist\ledgerflow-v203-runtime.css",
  ".\frontend\dist\agent-architecture-v203.html",
  ".\frontend\dist\agent-architecture-v203.js",
  ".\frontend\dist\agent-architecture-v203.css"
)
foreach ($path in $required) {
  if (-not (Test-Path $path)) {
    Write-Host "FAIL: Missing $path" -ForegroundColor Red
    exit 1
  }
}

$checks = @(
  @{ Path = ".\backend\app\department_agents.py"; Pattern = "Frame.*route.*parallel"; Label = "business analyst graph" },
  @{ Path = ".\backend\app\department_agents.py"; Pattern = "_challenge_findings"; Label = "challenge reviewer" },
  @{ Path = ".\backend\app\department_agents.py"; Pattern = "AsyncSqliteSaver"; Label = "async checkpoints" },
  @{ Path = ".\frontend\dist\ledgerflow-v203-runtime.js"; Pattern = "interimResults = true"; Label = "interim voice recognition" },
  @{ Path = ".\frontend\dist\ledgerflow-v203-runtime.js"; Pattern = "speechSynthesis.cancel"; Label = "voice interruption" },
  @{ Path = ".\frontend\dist\agent-architecture-v203.html"; Pattern = "Permanent files"; Label = "permanent file dropdown" },
  @{ Path = ".\frontend\dist\agent-architecture-v203.html"; Pattern = "Temporary / recurring files"; Label = "temporary file dropdown" }
)
foreach ($check in $checks) {
  if (-not (Select-String -Path $check.Path -Pattern $check.Pattern -Quiet)) {
    Write-Host "FAIL: Missing $($check.Label)." -ForegroundColor Red
    exit 1
  }
}

if ((Get-Content ".\VERSION" -Raw).Trim() -ne "2.0.3") {
  Write-Host "FAIL: VERSION is not 2.0.3." -ForegroundColor Red
  exit 1
}

Write-Host "PASS: LedgerFlow 2.0.3 business-analyst orchestration, personality, voice interruption and hidden file registers are installed." -ForegroundColor Green
