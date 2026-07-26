$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path ".env.superset")) {
  Copy-Item ".env.superset.example" ".env.superset"
  Write-Host "Created .env.superset. Change its secrets before production use." -ForegroundColor Yellow
}
docker compose -f .\docker-compose.superset.yml up -d --build
Write-Host "Superset is starting at http://127.0.0.1:8088" -ForegroundColor Green
Write-Host "Run LedgerFlow and open Data management to inspect department dashboard nodes."
