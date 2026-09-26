$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Starting VerdictLens local model engine on http://127.0.0.1:8000"
$Backend = Start-Process python -ArgumentList "-m", "uvicorn", "api:app", "--host", "127.0.0.1", "--port", "8000", "--reload" -WorkingDirectory (Join-Path $Root "backend") -PassThru -WindowStyle Hidden

try {
    Write-Host "Starting the website on http://localhost:3000"
    Set-Location $Root
    npm run dev
}
finally {
    if (-not $Backend.HasExited) { Stop-Process -Id $Backend.Id }
}
