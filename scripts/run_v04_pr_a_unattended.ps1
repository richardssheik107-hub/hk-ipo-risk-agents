[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$DataRoot,
    [string]$Python = "python",
    [string]$OutputDir = "",
    [string]$Config = "configs/v03_offline.yaml",
    [int]$RestartDelaySeconds = 30,
    [int]$MaxRestarts = 3
)

$ErrorActionPreference = "Stop"
if ($RestartDelaySeconds -lt 0 -or $MaxRestarts -lt 0) {
    throw "RestartDelaySeconds and MaxRestarts must be non-negative"
}
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $repoRoot
$expectedBranch = "docs/v04-five-person-execution-plan-20260820"
$branch = (& git branch --show-current).Trim()
if ($LASTEXITCODE -ne 0 -or $branch -ne $expectedBranch) {
    throw "PR-A unattended runner requires branch $expectedBranch"
}
if ((& git status --porcelain --untracked-files=normal)) {
    throw "PR-A unattended runner requires a clean git working tree"
}
$headSha = (& git rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw "Unable to resolve git HEAD" }
$shortSha = $headSha.Substring(0, 7)
if (-not $OutputDir) { $OutputDir = "reports/v04_pr_a_$shortSha" }
$outputPath = if ([IO.Path]::IsPathRooted($OutputDir)) {
    [IO.Path]::GetFullPath($OutputDir)
} else {
    [IO.Path]::GetFullPath((Join-Path $repoRoot $OutputDir))
}
$dataRootPath = (Resolve-Path -LiteralPath $DataRoot).Path
Write-Output "Official cohort validation delegated to canonical Python PR-A gate."

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
$lockPath = Join-Path $logDir "runner.lock"
if (Test-Path -LiteralPath $lockPath) {
    throw "Another runner may already own this output directory: $lockPath"
}
Set-Content -LiteralPath $lockPath -Value $PID -Encoding ascii

$arguments = @(
    "scripts/run_v04_pr_a.py",
    "--config", $Config,
    "--data-root", $dataRootPath,
    "--output-dir", $outputPath,
    "--resume"
)
try {
    for ($attempt = 0; $attempt -le $MaxRestarts; $attempt++) {
        $logPath = Join-Path $logDir ("attempt_{0:D2}.log" -f ($attempt + 1))
        Add-Content -LiteralPath $logPath -Value ("started_at=" + (Get-Date).ToString("o"))
        & $Python @arguments 2>&1 | Tee-Object -FilePath $logPath -Append
        $exitCode = $LASTEXITCODE
        Add-Content -LiteralPath $logPath -Value ("exit_code=" + $exitCode)
        if ($exitCode -eq 0) { exit 0 }
        if ($attempt -lt $MaxRestarts) {
            Start-Sleep -Seconds $RestartDelaySeconds
        }
    }
    exit $exitCode
}
finally {
    Remove-Item -LiteralPath $lockPath -ErrorAction SilentlyContinue
}
