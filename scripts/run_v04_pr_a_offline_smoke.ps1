[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$DataRoot,
    [string]$Python = "python",
    [string]$OutputDir = "",
    [string]$Config = "configs/v03_offline.yaml"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $repoRoot

$expectedBranch = "docs/v04-five-person-execution-plan-20260820"
$branch = (& git branch --show-current).Trim()
if ($LASTEXITCODE -ne 0 -or $branch -ne $expectedBranch) {
    throw "PR-A offline smoke requires branch $expectedBranch"
}
if ((& git status --porcelain --untracked-files=normal)) {
    throw "PR-A offline smoke requires a clean git working tree"
}
$headSha = (& git rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw "Unable to resolve git HEAD" }
$shortSha = $headSha.Substring(0, 7)

if (-not $OutputDir) {
    $OutputDir = "reports/v04_pr_a_offline_smoke_$shortSha"
}
$outputPath = if ([IO.Path]::IsPathRooted($OutputDir)) {
    [IO.Path]::GetFullPath($OutputDir)
} else {
    [IO.Path]::GetFullPath((Join-Path $repoRoot $OutputDir))
}
if ((Test-Path -LiteralPath $outputPath) -and
    (Get-ChildItem -LiteralPath $outputPath -Force | Select-Object -First 1)) {
    throw "Offline smoke output directory must be fresh: $outputPath"
}

$dataRootPath = (Resolve-Path -LiteralPath $DataRoot).Path
$manifest = Import-Csv -LiteralPath (Join-Path $repoRoot "data/catalog/ipo_prospectus_manifest.csv")
$pilotCases = @("ipo_2020_00368", "ipo_2020_00589", "ipo_2020_00873")
foreach ($caseId in $pilotCases) {
    $row = $manifest | Where-Object { $_.case_id -eq $caseId } | Select-Object -First 1
    if (-not $row) { throw "Manifest row missing for $caseId" }
    $pdf = Join-Path $dataRootPath $row.relative_path
    if (-not (Test-Path -LiteralPath $pdf -PathType Leaf)) {
        throw "Prospectus PDF missing for $caseId"
    }
    if ((Get-Item -LiteralPath $pdf).Length -le 0) {
        throw "Prospectus PDF is empty for $caseId"
    }
}

$offlineEnvironment = @(
    "IPO_RISK_LLM_PROVIDER", "IPO_RISK_LLM_API_KEY",
    "IPO_RISK_LLM_BASE_URL", "IPO_RISK_LLM_MODEL",
    "IPO_RISK_LLM_TIMEOUT_SECONDS", "IPO_RISK_LLM_MAX_RETRIES",
    "OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL",
    "ARK_CODING_API_KEY"
)
foreach ($name in $offlineEnvironment) {
    Remove-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue
}
$env:PYTHONUNBUFFERED = "1"

$logDir = "${outputPath}_logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$caseIds = $pilotCases -join ","
$commonArgs = @(
    "scripts/run_v04_pr_a.py",
    "--config", $Config,
    "--data-root", $dataRootPath,
    "--output-dir", $outputPath,
    "--case-ids", $caseIds
)

$stopwatch = [Diagnostics.Stopwatch]::StartNew()
& $Python @commonArgs 2>&1 | Tee-Object -FilePath (Join-Path $logDir "first_run.log")
$firstExit = $LASTEXITCODE
if ($firstExit -ne 0) { exit $firstExit }

$rerunArgs = $commonArgs + @("--resume", "--verify-determinism")
& $Python @rerunArgs 2>&1 | Tee-Object -FilePath (Join-Path $logDir "determinism_rerun.log")
$rerunExit = $LASTEXITCODE
$stopwatch.Stop()
@{
    branch = $branch
    head = $headSha
    output_dir = $outputPath
    elapsed_seconds = [Math]::Round($stopwatch.Elapsed.TotalSeconds, 3)
    first_exit_code = $firstExit
    rerun_exit_code = $rerunExit
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $logDir "runner_summary.json") -Encoding utf8
exit $rerunExit
