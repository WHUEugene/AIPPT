param(
    [string]$CondaEnvName = "aippt-win"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$configPath = Join-Path $backendDir "data\config.json"
$checks = New-Object System.Collections.Generic.List[string]
$failures = New-Object System.Collections.Generic.List[string]

function Add-CheckResult {
    param(
        [string]$Message,
        [bool]$Passed
    )

    if ($Passed) {
        $checks.Add("PASS: $Message") | Out-Null
    } else {
        $failures.Add("FAIL: $Message") | Out-Null
    }
}

function Test-CondaEnvironment {
    param([string]$Name)

    try {
        $json = conda env list --json | ConvertFrom-Json
        return [bool]($json.envs | Where-Object { (Split-Path $_ -Leaf) -eq $Name })
    } catch {
        return $false
    }
}

Add-CheckResult -Message "backend config file exists at $configPath" -Passed (Test-Path $configPath)

$imageDirExists = Test-Path (Join-Path $backendDir "generated\images")
$pptxDirExists = Test-Path (Join-Path $backendDir "generated\pptx")
Add-CheckResult -Message "backend generated images directory exists" -Passed $imageDirExists
Add-CheckResult -Message "backend generated pptx directory exists" -Passed $pptxDirExists

$venvCfgPaths = @(
    Join-Path $backendDir "venv\pyvenv.cfg"),
    (Join-Path $backendDir ".venv\pyvenv.cfg")

foreach ($venvCfg in $venvCfgPaths) {
    if (Test-Path $venvCfg) {
        $content = Get-Content $venvCfg -Raw
        $looksMac = $content -match "/Users/" -or $content -match "darwin"
        Add-CheckResult -Message "imported platform-specific venv removed or rebuilt for $venvCfg" -Passed (-not $looksMac)
    } else {
        $checks.Add("PASS: no stale imported venv config at $venvCfg") | Out-Null
    }
}

$viteShim = Join-Path $frontendDir "node_modules\.bin\vite.cmd"
$tscShim = Join-Path $frontendDir "node_modules\.bin\tsc.cmd"
Add-CheckResult -Message "frontend vite Windows shim exists" -Passed (Test-Path $viteShim)
Add-CheckResult -Message "frontend tsc Windows shim exists" -Passed (Test-Path $tscShim)

$esbuildWin = Join-Path $frontendDir "node_modules\@esbuild\win32-x64"
$esbuildMac = Join-Path $frontendDir "node_modules\@esbuild\darwin-arm64"
if (Test-Path $esbuildMac) {
    Add-CheckResult -Message "frontend does not rely on macOS esbuild binaries" -Passed (Test-Path $esbuildWin)
} else {
    $checks.Add("PASS: no imported macOS-only esbuild binary detected") | Out-Null
}

Add-CheckResult -Message "conda environment '$CondaEnvName' exists" -Passed (Test-CondaEnvironment -Name $CondaEnvName)

foreach ($line in $checks) {
    Write-Host $line -ForegroundColor Green
}

foreach ($line in $failures) {
    Write-Host $line -ForegroundColor Red
}

if ($failures.Count -gt 0) {
    Write-Host ""
    Write-Host ("Local runtime verification failed with {0} issue(s)." -f $failures.Count) -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Local runtime verification passed." -ForegroundColor Green
