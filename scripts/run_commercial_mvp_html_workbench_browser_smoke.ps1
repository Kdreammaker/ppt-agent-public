param(
  [string]$Suffix = "pre_full_beta_last_check",
  [int]$Port = 4189,
  [string]$Report,
  [string]$ScreenshotRoot
)

$ErrorActionPreference = "Stop"

function Resolve-RepoRoot {
  return (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
}

function Resolve-Node {
  $bundledNode = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
  if (Test-Path -LiteralPath $bundledNode) {
    return $bundledNode
  }
  $nodeCommand = Get-Command node -ErrorAction Stop
  return $nodeCommand.Source
}

function Resolve-Python {
  $bundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
  if (Test-Path -LiteralPath $bundledPython) {
    return $bundledPython
  }
  $pythonCommand = Get-Command python -ErrorAction Stop
  return $pythonCommand.Source
}

function Wait-LocalServer {
  param([int]$ServerPort)
  $deadline = (Get-Date).AddSeconds(20)
  while ((Get-Date) -lt $deadline) {
    try {
      $client = [System.Net.Sockets.TcpClient]::new()
      $async = $client.BeginConnect("127.0.0.1", $ServerPort, $null, $null)
      if ($async.AsyncWaitHandle.WaitOne(500)) {
        $client.EndConnect($async)
        $client.Close()
        return
      }
      $client.Close()
    } catch {
      Start-Sleep -Milliseconds 250
    }
  }
  throw "Local smoke server did not start on 127.0.0.1:$ServerPort"
}

$repoRoot = Resolve-RepoRoot
if (-not $Report) {
  $Report = "outputs\reports\commercial_mvp_html_workbench_browser_smoke_$Suffix.json"
}
if (-not $ScreenshotRoot) {
  $ScreenshotRoot = "outputs\playwright\commercial-mvp-html-workbench-$($Suffix -replace '_','-')"
}

$nodePathCandidates = @(
  (Join-Path $repoRoot ".playwright-cli\node_modules"),
  (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules")
) | Where-Object { Test-Path -LiteralPath $_ }

if (-not $nodePathCandidates) {
  throw "Playwright Node modules were not found. Expected .playwright-cli\node_modules or bundled Codex node_modules."
}

$node = Resolve-Node
$python = Resolve-Python
$server = $null
$oldNodePath = $env:NODE_PATH
$oldBaseUrl = $env:COMMERCIAL_MVP_BASE_URL
$oldReport = $env:COMMERCIAL_MVP_BROWSER_REPORT
$oldScreenshotRoot = $env:COMMERCIAL_MVP_SCREENSHOT_ROOT

try {
  $env:NODE_PATH = ($nodePathCandidates -join [IO.Path]::PathSeparator)
  $env:COMMERCIAL_MVP_BASE_URL = "http://127.0.0.1:$Port"
  $env:COMMERCIAL_MVP_BROWSER_REPORT = $Report
  $env:COMMERCIAL_MVP_SCREENSHOT_ROOT = $ScreenshotRoot

  $server = Start-Process -FilePath $python `
    -ArgumentList @("-m", "http.server", [string]$Port, "--bind", "127.0.0.1") `
    -WorkingDirectory $repoRoot `
    -PassThru `
    -WindowStyle Hidden

  Wait-LocalServer -ServerPort $Port

  & $node (Join-Path $repoRoot "scripts\validate_commercial_mvp_html_workbench_browser_smoke.js")
  if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
  }
} finally {
  if ($server -and -not $server.HasExited) {
    Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
    $server.WaitForExit(5000) | Out-Null
  }
  $env:NODE_PATH = $oldNodePath
  $env:COMMERCIAL_MVP_BASE_URL = $oldBaseUrl
  $env:COMMERCIAL_MVP_BROWSER_REPORT = $oldReport
  $env:COMMERCIAL_MVP_SCREENSHOT_ROOT = $oldScreenshotRoot
}
