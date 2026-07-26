$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
docker compose -f .\docker-compose.superset.yml down
