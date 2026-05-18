Param(
  [string]$AppFile = "app_unloadv1.7.py",
  [int]$StreamlitPort = 8501,
  [string]$StreamlitHost = "0.0.0.0",
  [switch]$SkipRustApi
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

$LogDir = Join-Path $RepoRoot ".data"
$null = New-Item -ItemType Directory -Path $LogDir -Force

$RustApiDir = Join-Path $RepoRoot "rust_api"
$RustApiLog = Join-Path $LogDir "rust_api.log"
$RustApiErrLog = Join-Path $LogDir "rust_api.err.log"
$RustApiPidFile = Join-Path $LogDir "rust_api.pid"
$RustApiPort = if ($env:RUST_API_PORT) { $env:RUST_API_PORT } else { "8787" }
$RustApiStartedByScript = $false
$RustApiProc = $null

function Resolve-CargoPath {
  $cargoCmd = Get-Command cargo -ErrorAction SilentlyContinue
  if ($cargoCmd -and $cargoCmd.Source) {
    return $cargoCmd.Source
  }

  $defaultCargo = Join-Path $HOME ".cargo\bin\cargo.exe"
  if (Test-Path $defaultCargo) {
    return $defaultCargo
  }

  return $null
}

function Test-ProcessAlive {
  Param([int]$Pid)
  try {
    $proc = Get-Process -Id $Pid -ErrorAction Stop
    return $null -ne $proc
  } catch {
    return $false
  }
}

if (-not $SkipRustApi) {
  if ((Test-Path $RustApiPidFile)) {
    $existingPidRaw = Get-Content $RustApiPidFile -ErrorAction SilentlyContinue
    if ($existingPidRaw) {
      $existingPid = [int]$existingPidRaw
      if (Test-ProcessAlive -Pid $existingPid) {
        Write-Host "[INFO] Rust API already running (PID $existingPid)."
      } else {
        Remove-Item $RustApiPidFile -Force -ErrorAction SilentlyContinue
      }
    }
  }

  if (-not (Test-Path $RustApiPidFile)) {
    $cargoPath = Resolve-CargoPath
    if (-not $cargoPath) {
      Write-Warning "cargo was not found. Starting Streamlit only."
    } elseif (-not (Test-Path (Join-Path $RustApiDir "Cargo.toml"))) {
      Write-Warning "rust_api/Cargo.toml not found. Starting Streamlit only."
    } else {
      $env:TRUCKAPP_DATA_DIR = $RepoRoot
      $env:RUST_API_PORT = "$RustApiPort"
      $RustApiProc = Start-Process -FilePath $cargoPath `
        -ArgumentList @("run", "--release") `
        -WorkingDirectory $RustApiDir `
        -RedirectStandardOutput $RustApiLog `
        -RedirectStandardError $RustApiErrLog `
        -PassThru
      Set-Content -Path $RustApiPidFile -Value "$($RustApiProc.Id)"
      $RustApiStartedByScript = $true
      Write-Host "[INFO] Rust API starting (PID $($RustApiProc.Id)) on http://localhost:$RustApiPort"
      Write-Host "[INFO] Rust API log: $RustApiLog"
    }
  }
}

$PythonCandidates = @(
  (Join-Path $RepoRoot ".venv\Scripts\python.exe"),
  (Join-Path $RepoRoot "venv\Scripts\python.exe")
)
$PythonExe = $PythonCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $PythonExe) {
  $pyCmd = Get-Command py -ErrorAction SilentlyContinue
  if ($pyCmd -and $pyCmd.Source) {
    $PythonExe = $pyCmd.Source
  } else {
    throw "No Python executable found. Create .venv or install Python launcher (py)."
  }
}

try {
  Write-Host "[INFO] Starting Streamlit on http://localhost:$StreamlitPort"
  & $PythonExe -m streamlit run $AppFile --server.port $StreamlitPort --server.address $StreamlitHost
} finally {
  if ($RustApiStartedByScript -and $RustApiProc) {
    if (Test-ProcessAlive -Pid $RustApiProc.Id) {
      Stop-Process -Id $RustApiProc.Id -Force -ErrorAction SilentlyContinue
      Remove-Item $RustApiPidFile -Force -ErrorAction SilentlyContinue
      Write-Host "[INFO] Stopped Rust API process $($RustApiProc.Id)."
    }
  }
}
