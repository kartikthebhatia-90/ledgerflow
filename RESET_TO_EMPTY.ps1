$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$listener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    Write-Host "Stop LedgerFlow with Ctrl+C before resetting, then run this script again." -ForegroundColor Yellow
    exit 1
}

$preserve = @("NEW_DATA_README.md", ".empty_company_data")
Get-ChildItem ".\data" -Force | Where-Object { $preserve -notcontains $_.Name } | Remove-Item -Recurse -Force
New-Item -ItemType Directory -Force ".\data\source_files\permanent", ".\data\source_files\recurring", ".\data\database", ".\data\context", ".\data\memory", ".\data\audit" | Out-Null
Set-Content ".\data\.empty_company_data" "Company data intentionally cleared. Demo seed disabled."
Set-Content ".\data\source_files\.use_as_folder_intake" "Files placed below this folder are scanned by LedgerFlow."
Set-Content ".\data\source_files\README.md" "Drop permanent and recurring source files through the Data management visual or into the matching folders."

if (Test-Path ".\file_drop") {
    Get-ChildItem ".\file_drop" -Force | Remove-Item -Recurse -Force
}
New-Item -ItemType Directory -Force ".\file_drop\permanent", ".\file_drop\recurring", ".\file_drop\archive" | Out-Null

Write-Host "PASS: LedgerFlow business data is empty. .env and application code were preserved." -ForegroundColor Green
