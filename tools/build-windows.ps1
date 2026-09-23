param(
    [string]$AdbDirectory
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$distRoot = Join-Path $repo 'dist'
$release = Join-Path $distRoot 'OpenCameraRemote'

if (-not $AdbDirectory) {
    $adbCommand = Get-Command adb -ErrorAction Stop
    $AdbDirectory = Split-Path -Parent $adbCommand.Source
}
$AdbDirectory = (Resolve-Path -LiteralPath $AdbDirectory).Path
$needed = @('adb.exe', 'AdbWinApi.dll', 'AdbWinUsbApi.dll', 'NOTICE.txt', 'source.properties')
foreach ($name in $needed) {
    if (-not (Test-Path -LiteralPath (Join-Path $AdbDirectory $name) -PathType Leaf)) {
        throw "Official Android Platform Tools file is missing: $name"
    }
}
$adbVersion = & (Join-Path $AdbDirectory 'adb.exe') version
if ($LASTEXITCODE -ne 0 -or ($adbVersion -join "`n") -notmatch 'Android Debug Bridge version') {
    throw 'ADB version check failed'
}

if (Test-Path -LiteralPath $release) {
    $resolvedRelease = (Resolve-Path -LiteralPath $release).Path
    $expectedPrefix = (Join-Path $repo 'dist') + [IO.Path]::DirectorySeparatorChar
    if (-not $resolvedRelease.StartsWith($expectedPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Release directory is outside this repository dist folder'
    }
    Remove-Item -LiteralPath $resolvedRelease -Recurse -Force
}

Push-Location $repo
try {
    uv run pyinstaller --noconfirm --clean --onedir --contents-directory . `
        --name OpenCameraRemote --paths src `
        --add-data "$(Join-Path $repo 'src/oc_remote/web');oc_remote/web" `
        --distpath $distRoot --workpath (Join-Path $repo 'build') `
        --specpath (Join-Path $repo 'build') src/oc_remote/main.py
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed' }
} finally {
    Pop-Location
}

$bundleAdb = Join-Path $release 'adb'
New-Item -ItemType Directory -Path $bundleAdb -Force | Out-Null
foreach ($name in $needed) {
    Copy-Item -LiteralPath (Join-Path $AdbDirectory $name) -Destination (Join-Path $bundleAdb $name)
}
Copy-Item -LiteralPath (Join-Path $repo 'LICENSE') -Destination (Join-Path $release 'LICENSE.txt')

$licenseRoot = Join-Path $release 'licenses'
New-Item -ItemType Directory -Path $licenseRoot -Force | Out-Null
$pythonBase = ((& uv run python -c 'import sys; print(sys.base_prefix)') | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or -not $pythonBase) { throw 'Could not locate the Python runtime license' }
Copy-Item -LiteralPath (Join-Path $pythonBase 'LICENSE.txt') `
    -Destination (Join-Path $licenseRoot 'PYTHON_LICENSE.txt')
$sitePackages = ((& uv run python -c "import sysconfig; print(sysconfig.get_path('purelib'))") | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or -not $sitePackages) { throw 'Could not locate third-party license metadata' }
foreach ($metadata in Get-ChildItem -LiteralPath $sitePackages -Directory -Filter '*.dist-info') {
    $notices = Get-ChildItem -LiteralPath $metadata.FullName -Recurse -File | Where-Object {
        $_.Name -match '^(LICENSE|COPYING|NOTICE)'
    }
    foreach ($notice in $notices) {
        $relative = $notice.FullName.Substring($metadata.FullName.Length + 1)
        $target = Join-Path (Join-Path $licenseRoot $metadata.Name) $relative
        New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
        Copy-Item -LiteralPath $notice.FullName -Destination $target
    }
}
Write-Output "Windows release directory: $release"
Write-Output ($adbVersion -join "`n")
