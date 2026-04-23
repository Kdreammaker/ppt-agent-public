param(
    [string]$Manifest = "config/public_gate_sync_manifest_fixture.json",
    [string]$Output = "outputs/reports/public_gate_sync_dry_run.json",
    [switch]$ApprovePublicWrite
)

$ErrorActionPreference = "Stop"
$workspace = (Get-Location).Path
$manifestArgument = $Manifest
$manifestPath = if ([System.IO.Path]::IsPathRooted($Manifest)) { $Manifest } else { Join-Path $workspace $Manifest }
$outputPath = if ([System.IO.Path]::IsPathRooted($Output)) { $Output } else { Join-Path $workspace $Output }

if (-not (Test-Path -LiteralPath $manifestPath)) {
    throw "Sync manifest not found: $manifestPath"
}

$manifestData = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable
$serialized = $manifestData | ConvertTo-Json -Depth 40
$forbiddenPatterns = @(
    'workspace_code',
    'xox[baprs]-',
    'sk-[A-Za-z0-9_-]{12,}',
    'AIza[0-9A-Za-z_-]{20,}',
    '[A-Za-z]:\\'
)

$findings = New-Object System.Collections.Generic.List[string]
foreach ($pattern in $forbiddenPatterns) {
    if ($serialized -match $pattern) {
        $findings.Add("forbidden pattern matched: $pattern")
    }
}

foreach ($field in @(
    "private_reference_outputs_included",
    "binary_assets_included",
    "registry_exports_included",
    "local_absolute_paths_included",
    "drive_linkage_included",
    "work_logs_included",
    "workspace_manifests_included"
)) {
    $value = $manifestData["source_boundary"][$field]
    if ($value -ne $false) {
        $findings.Add("source_boundary.$field must be false")
    }
}

$repositoryUrl = $manifestData["public_gate_target"]["repository_url"]
if ($repositoryUrl -ne "https://github.com/Kdreammaker/ai-asset-contribution-gate") {
    $findings.Add("public gate repository URL mismatch")
}

$publicWriteAllowed = $manifestData["operator_approval"]["public_write_allowed"]
if ($publicWriteAllowed -ne $true -and $ApprovePublicWrite.IsPresent) {
    $findings.Add("approval switch was provided but manifest public_write_allowed is not true")
}

$status = if ($findings.Count -eq 0) { "valid" } else { "invalid" }
$report = [ordered]@{
    schema_version = "1.0"
    command = "Prepare-PublicGateSync.ps1"
    status = $status
    mode = "dry_run"
    manifest_path = $manifestArgument
    public_gate = "https://github.com/Kdreammaker/ai-asset-contribution-gate"
    approval_switch_present = [bool]$ApprovePublicWrite.IsPresent
    public_write_performed = $false
    token_access_performed = $false
    candidate_count = @($manifestData["candidate_metadata"]).Count
    findings = @($findings)
    policy_summary = [ordered]@{
        dry_run_first = $true
        public_repo_write_requires_operator_approval = $true
        raw_references_included = $false
        binary_assets_included = $false
        registry_exports_included = $false
        local_absolute_paths_included = $false
        drive_linkage_included = $false
        work_logs_included = $false
        tokens_read_printed_or_committed = $false
    }
}

$outputDir = Split-Path -Parent $outputPath
if ($outputDir) {
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
}
$report | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $outputPath -Encoding UTF8

if ($status -ne "valid") {
    Write-Error "public gate sync dry-run invalid; see $Output"
}

Write-Output "public_gate_sync_dry_run=$status candidates=$($report.candidate_count) public_write_performed=False"
