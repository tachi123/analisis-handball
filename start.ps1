[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$backendEnv = Join-Path $root 'backend\.env.local'
$composeFiles = @('--env-file', $backendEnv, '-f', 'docker-compose.yml', '-f', 'docker-compose.local.yml')
$reportUrl = 'http://localhost:8000/api/v1/public/reports/current'
$alembicHead = '73b208e83d81'
$env:COMPOSE_PROJECT_NAME = 'analisis-handball'

function Get-EnvSetting([string]$Path, [string]$Name) {
    $line = Get-Content -LiteralPath $Path | Where-Object {
        $_ -match "^\s*$([regex]::Escape($Name))\s*="
    } | Select-Object -Last 1
    if (-not $line) { return $null }
    return ($line -replace "^\s*$([regex]::Escape($Name))\s*=\s*", '').Trim().Trim('"').Trim("'")
}

function Require-Setting([string]$Path, [string]$Name, [string]$Expected) {
    if ((Get-EnvSetting $Path $Name) -ne $Expected) {
        throw "$Path must set $Name=$Expected for the safe local launcher."
    }
}

function Start-ViteServer([string]$Directory, [int]$Port, [string]$Name) {
    $escapedRoot = $root.Replace("'", "''")
    $command = "Set-Location -LiteralPath '$escapedRoot'; npm --prefix '$Directory' run dev -- --host 127.0.0.1 --port $Port --strictPort"
    Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoExit', '-Command', $command) | Out-Null
    Write-Host "Started $Name Vite window on http://localhost:$Port"
}

foreach ($command in 'docker', 'npm') {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw "Missing prerequisite: $command. Install it and reopen PowerShell."
    }
}

if (-not (Test-Path -LiteralPath $backendEnv)) {
    throw "Missing local configuration: $backendEnv. Copy backend/.env.local.example and set explicit local credentials."
}
Require-Setting $backendEnv 'APP_ENV' 'development'
Require-Setting $backendEnv 'REPORT_PUBLISHER' 'file'
Require-Setting $backendEnv 'LOCAL_PUBLIC_REPORT_FILE' '/app/data/public-report.json'

& docker compose @composeFiles version | Out-Null
Write-Host "Compose target: project analisis-handball; volume analisis-handball_postgres_data; database sapa_stats; Alembic head $alembicHead."
Write-Host 'Starting Compose with its migration gate. This launcher never removes containers, volumes, or data.'
& docker compose @composeFiles up -d

$deadline = (Get-Date).AddSeconds(120)
$response = $null
do {
    $migrateContainer = & docker compose @composeFiles ps -aq migrate
    if ($migrateContainer) {
        $migrateState = & docker inspect --format '{{.State.Status}}:{{.State.ExitCode}}' $migrateContainer
        if ($migrateState -eq 'exited:0') {
            try {
                $response = Invoke-WebRequest -UseBasicParsing 'http://localhost:8000/health' -TimeoutSec 3
                if ($response.StatusCode -eq 200) { break }
            } catch {
                # The backend gate has passed, but Uvicorn is still becoming healthy.
            }
        } elseif ($migrateState -match '^exited:' -or $migrateState -match '^dead:') {
            & docker compose @composeFiles ps
            throw @"
Migration did not complete successfully. Backend was not started; inspect docker compose logs migrate.

The named preload volume is preserved. Do not reset, delete, or recreate it. Follow docs/operations/local-recovery-runbook.md to create and verify a backup in an isolated clone before investigating the migration failure.
"@
        }
    }
    Start-Sleep -Seconds 2
} while ((Get-Date) -lt $deadline)

if (-not $response -or $response.StatusCode -ne 200) {
    & docker compose @composeFiles ps
    throw 'Backend did not become healthy within 120 seconds. Inspect docker compose logs migrate backend.'
}

$env:VITE_PUBLIC_REPORT_URL = $reportUrl
Start-ViteServer 'frontend' 5173 'operational SPA'
Start-ViteServer 'reports' 5174 'reports'
Write-Host 'Operational SPA: http://localhost:5173'
Write-Host 'Reports: http://localhost:5174'
Write-Host "Public report API: $reportUrl"
