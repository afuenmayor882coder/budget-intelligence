# Start Budget Intelligence App
# Run both frontend and backend concurrently

Write-Host "Starting Budget Intelligence App..." -ForegroundColor Cyan

# Start backend
$backendJob = Start-Job -ScriptBlock {
    Set-Location "c:\Users\afuen\OneDrive\Documents\Budget Analysis\budget-analysis-app\backend"
    .\venv\Scripts\uvicorn.exe main:app --host 0.0.0.0 --port 8000 --reload
}

Start-Sleep -Seconds 2

# Start frontend
$frontendJob = Start-Job -ScriptBlock {
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")
    Set-Location "c:\Users\afuen\OneDrive\Documents\Budget Analysis\budget-analysis-app"
    npm run dev
}

Write-Host ""
Write-Host "Backend:  http://localhost:8000" -ForegroundColor Green
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop both servers" -ForegroundColor Yellow

try {
    Wait-Job $backendJob, $frontendJob
} finally {
    Stop-Job $backendJob, $frontendJob
    Remove-Job $backendJob, $frontendJob
}
