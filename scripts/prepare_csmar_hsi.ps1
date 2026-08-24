param(
    [Parameter(Mandatory = $true)]
    [string]$ArchivePath,

    [Parameter(Mandatory = $true)]
    [string]$OutputDirectory,

    [string]$ExpectedArchiveSha256 = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RequiredHeaders = @(
    "Indexcd",
    "Trddt",
    "Opnidx",
    "Highidx",
    "Lowidx",
    "Clsidx",
    "Vol",
    "Value"
)
$NormalizedHeaders = @(
    "reference_id",
    "trading_date",
    "open",
    "high",
    "low",
    "close",
    "constituent_volume",
    "index_return",
    "source_record_id",
    "source_id",
    "source_version",
    "project_generated_identity"
)

function Get-LowerSha256 {
    param([Parameter(Mandatory = $true)][string]$LiteralPath)
    return (Get-FileHash -LiteralPath $LiteralPath -Algorithm SHA256).Hash.ToLowerInvariant()
}

function ConvertTo-CsvField {
    param([AllowNull()][object]$Value)
    $text = if ($null -eq $Value) { "" } else { [string]$Value }
    return '"' + $text.Replace('"', '""') + '"'
}

function Write-ConflictSafeUtf8 {
    param(
        [Parameter(Mandatory = $true)][string]$LiteralPath,
        [Parameter(Mandatory = $true)][string]$Content
    )
    $encoding = [System.Text.UTF8Encoding]::new($false)
    if (Test-Path -LiteralPath $LiteralPath) {
        $existing = [System.IO.File]::ReadAllText($LiteralPath, $encoding)
        if ($existing -cne $Content) {
            throw "Refusing to overwrite conflicting runtime artifact: $LiteralPath"
        }
        return
    }
    [System.IO.File]::WriteAllText($LiteralPath, $Content, $encoding)
}

$resolvedArchive = (Resolve-Path -LiteralPath $ArchivePath).Path
$archiveItem = Get-Item -LiteralPath $resolvedArchive
if ($archiveItem.Extension.ToLowerInvariant() -ne ".zip") {
    throw "ArchivePath must identify one ZIP archive"
}
$archiveSha256 = Get-LowerSha256 -LiteralPath $resolvedArchive
if ($ExpectedArchiveSha256) {
    $expected = $ExpectedArchiveSha256.Trim().ToLowerInvariant()
    if ($archiveSha256 -cne $expected) {
        throw "Archive SHA-256 mismatch: expected $expected, found $archiveSha256"
    }
}

New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$resolvedOutput = (Resolve-Path -LiteralPath $OutputDirectory).Path

Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($resolvedArchive)
try {
    $sourceEntry = @($zip.Entries | Where-Object { $_.FullName -eq "IDX_Gidxtrd.xls" })
    if ($sourceEntry.Count -ne 1) {
        throw "Expected exactly one IDX_Gidxtrd.xls member"
    }
    $inputStream = $sourceEntry[0].Open()
    try {
        $memoryStream = [System.IO.MemoryStream]::new()
        try {
            $inputStream.CopyTo($memoryStream)
            $sourceBytes = $memoryStream.ToArray()
        }
        finally {
            $memoryStream.Dispose()
        }
    }
    finally {
        $inputStream.Dispose()
    }
}
finally {
    $zip.Dispose()
}

$sha256 = [System.Security.Cryptography.SHA256]::Create()
try {
    $sourceFileSha256 = ([System.BitConverter]::ToString(
        $sha256.ComputeHash($sourceBytes)
    )).Replace("-", "").ToLowerInvariant()
}
finally {
    $sha256.Dispose()
}

$stagedWorkbook = Join-Path $resolvedOutput (
    "IDX_Gidxtrd_" + $sourceFileSha256.Substring(0, 12) + ".xls"
)
if (Test-Path -LiteralPath $stagedWorkbook) {
    if ((Get-LowerSha256 -LiteralPath $stagedWorkbook) -cne $sourceFileSha256) {
        throw "Staged workbook hash conflict: $stagedWorkbook"
    }
}
else {
    [System.IO.File]::WriteAllBytes($stagedWorkbook, $sourceBytes)
}

$excel = $null
$workbook = $null
$rows = New-Object System.Collections.Generic.List[object]
try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $workbook = $excel.Workbooks.Open($stagedWorkbook, 0, $true)
    if ($workbook.Worksheets.Count -ne 1) {
        throw "CSMAR HSI workbook must contain exactly one worksheet"
    }
    $sheet = $workbook.Worksheets.Item(1)
    $used = $sheet.UsedRange
    $values = $used.Value2
    if ($used.Columns.Count -ne $RequiredHeaders.Count) {
        throw "CSMAR HSI workbook column count differs from the delivered schema"
    }
    for ($column = 1; $column -le $RequiredHeaders.Count; $column++) {
        if ([string]$values[1, $column] -cne $RequiredHeaders[$column - 1]) {
            throw "Unexpected CSMAR header at column $column"
        }
    }

    $invariant = [System.Globalization.CultureInfo]::InvariantCulture
    for ($rowNumber = 2; $rowNumber -le $used.Rows.Count; $rowNumber++) {
        $referenceId = ([string]$values[$rowNumber, 1]).Trim()
        if ($referenceId -ne "HSI") {
            continue
        }
        $rawDate = $values[$rowNumber, 2]
        if ($rawDate -is [double]) {
            $tradingDate = [DateTime]::FromOADate($rawDate).ToString("yyyy-MM-dd")
        }
        else {
            $parsedDate = [DateTime]::MinValue
            if (-not [DateTime]::TryParseExact(
                ([string]$rawDate).Trim(),
                "yyyy-MM-dd",
                $invariant,
                [System.Globalization.DateTimeStyles]::None,
                [ref]$parsedDate
            )) {
                throw "Invalid HSI trading date at workbook row $rowNumber"
            }
            $tradingDate = $parsedDate.ToString("yyyy-MM-dd")
        }
        $close = [Convert]::ToDecimal($values[$rowNumber, 6], $invariant)
        if ($close -le 0) {
            throw "HSI close must be positive at workbook row $rowNumber"
        }
        $rows.Add([pscustomobject][ordered]@{
            reference_id = "HSI"
            trading_date = $tradingDate
            open = [Convert]::ToString($values[$rowNumber, 3], $invariant)
            high = [Convert]::ToString($values[$rowNumber, 4], $invariant)
            low = [Convert]::ToString($values[$rowNumber, 5], $invariant)
            close = [Convert]::ToString($values[$rowNumber, 6], $invariant)
            constituent_volume = [Convert]::ToString($values[$rowNumber, 7], $invariant)
            index_return = [Convert]::ToString($values[$rowNumber, 8], $invariant)
        })
    }
}
finally {
    if ($null -ne $workbook) {
        $workbook.Close($false)
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($workbook)
    }
    if ($null -ne $excel) {
        $excel.Quit()
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel)
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}

$orderedRows = @($rows | Sort-Object trading_date)
if ($orderedRows.Count -eq 0) {
    throw "No HSI rows found in the delivered CSMAR workbook"
}
$dates = @($orderedRows | ForEach-Object { $_.trading_date })
$duplicateCount = $dates.Count - @($dates | Sort-Object -Unique).Count
if ($duplicateCount -ne 0) {
    throw "Duplicate HSI trading dates found: $duplicateCount"
}
$sourceVersion = (
    "csmar_hsi_daily_close_v1:" +
    $archiveSha256.Substring(0, 12) + ":" +
    $sourceFileSha256.Substring(0, 12)
)

$csvLines = New-Object System.Collections.Generic.List[string]
$csvLines.Add(($NormalizedHeaders | ForEach-Object { ConvertTo-CsvField $_ }) -join ",")
foreach ($row in $orderedRows) {
    $sourceRecordId = "project:CSMAR:IDX_Gidxtrd.xls:HSI:" + $row.trading_date
    $valuesForCsv = @(
        $row.reference_id,
        $row.trading_date,
        $row.open,
        $row.high,
        $row.low,
        $row.close,
        $row.constituent_volume,
        $row.index_return,
        $sourceRecordId,
        "CSMAR",
        $sourceVersion,
        "true"
    )
    $csvLines.Add(($valuesForCsv | ForEach-Object { ConvertTo-CsvField $_ }) -join ",")
}
$normalizedCsv = Join-Path $resolvedOutput "csmar_hsi_daily.csv"
$csvContent = ($csvLines -join "`n") + "`n"
Write-ConflictSafeUtf8 -LiteralPath $normalizedCsv -Content $csvContent
$normalizedFileSha256 = Get-LowerSha256 -LiteralPath $normalizedCsv

$manifest = [ordered]@{
    manifest_version = "csmar_hsi_source_manifest_v1"
    source_name = "CSMAR"
    dataset_name = "国际指数日行情文件"
    reference_id = "HSI"
    series_name = "恒生指数"
    frequency = "daily"
    series_type = "unspecified_by_delivered_metadata"
    series_type_status = "SERIES_TYPE_REQUIRES_METADATA_CONFIRMATION"
    source_file_name = "IDX_Gidxtrd.xls"
    source_archive_name = $archiveItem.Name
    source_archive_sha256 = $archiveSha256
    source_file_sha256 = $sourceFileSha256
    normalized_schema_version = "csmar_hsi_daily_close_v1"
    normalized_file_sha256 = $normalizedFileSha256
    row_count = $orderedRows.Count
    coverage_start = $orderedRows[0].trading_date
    coverage_end = $orderedRows[-1].trading_date
    duplicate_count = 0
    null_close_count = 0
    invalid_close_count = 0
    parse_error_count = 0
    retrieval_metadata = [ordered]@{
        delivered_to_project_date = "2026-08-23"
        original_download_timestamp = "not_supplied"
        delivery_method = "user_supplied_csmar_export"
        workbook_open_mode = "read_only"
    }
    license_notice = "仅供西安交通大学使用；原始与normalized数据不得提交公开仓库"
    project_generated_identity = $true
}
$manifestJson = ($manifest | ConvertTo-Json -Depth 8) + "`n"
$runtimeManifest = Join-Path $resolvedOutput "csmar_hsi_source_manifest.runtime.json"
Write-ConflictSafeUtf8 -LiteralPath $runtimeManifest -Content $manifestJson

$verifiedManifestText = [System.IO.File]::ReadAllText(
    $runtimeManifest,
    [System.Text.UTF8Encoding]::new($false)
)
if ($verifiedManifestText -notmatch '[\p{IsCJKUnifiedIdeographs}]') {
    throw "UTF-8 manifest verification failed: Chinese text was not preserved"
}

Write-Output ("NORMALIZED_CSV=" + $normalizedCsv)
Write-Output ("RUNTIME_MANIFEST=" + $runtimeManifest)
Write-Output ("ARCHIVE_SHA256=" + $archiveSha256)
Write-Output ("SOURCE_FILE_SHA256=" + $sourceFileSha256)
Write-Output ("NORMALIZED_FILE_SHA256=" + $normalizedFileSha256)
Write-Output ("HSI_ROW_COUNT=" + $orderedRows.Count)
Write-Output ("HSI_COVERAGE_START=" + $orderedRows[0].trading_date)
Write-Output ("HSI_COVERAGE_END=" + $orderedRows[-1].trading_date)
Write-Output "HSI_SOURCE_ACCEPTED=YES"
