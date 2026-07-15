$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$CoreRoot = Join-Path $Root "vendor\wenyi"
$BuildDir = Join-Path $Root "build"
$DistDir = Join-Path $Root "dist"
$CoreDist = Join-Path $BuildDir "core-dist"
$ReleaseDir = Join-Path $DistDir "文译"
$IconPath = Join-Path $BuildDir "wenyi.png"
$CoreProject = Join-Path $CoreRoot "pyproject.toml"
$CoreConfig = Join-Path $CoreRoot "config.yaml"

if (-not (Test-Path -LiteralPath $CoreProject)) {
    throw "Wenyi core not found. Clone https://github.com/BigDawnGhost/wenyi into vendor\wenyi."
}
if (-not (Test-Path -LiteralPath $CoreConfig)) {
    throw "Wenyi core config not found: $CoreConfig"
}

if (Get-Command uv -ErrorAction SilentlyContinue) {
    $Uv = "uv"
} else {
    throw "uv not found. Install it from https://docs.astral.sh/uv/"
}

Remove-Item -Recurse -Force $BuildDir, $DistDir -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $BuildDir, $CoreDist | Out-Null

& $Uv run --project $Root python `
    (Join-Path $Root "gui\build_icon.py") $IconPath
if ($LASTEXITCODE -ne 0) { throw "Failed to generate the application icon." }

Write-Host "[1/3] Building Wenyi core..."
& $Uv run --project $CoreRoot --with pyinstaller pyinstaller `
    --noconfirm --clean --onefile --console `
    --name trans-novel `
    --paths $CoreRoot `
    --distpath $CoreDist `
    --workpath (Join-Path $BuildDir "core") `
    --specpath $BuildDir `
    (Join-Path $Root "gui\wrapper.py")
if ($LASTEXITCODE -ne 0) { throw "Failed to build Wenyi core." }

Write-Host "[2/3] Building GUI..."
& $Uv run --project $Root pyinstaller `
    --noconfirm --clean --onedir --windowed `
    --name "文译" `
    --icon $IconPath `
    --add-data "$CoreConfig;." `
    --distpath $DistDir `
    --workpath (Join-Path $BuildDir "gui") `
    --specpath $BuildDir `
    (Join-Path $Root "main.py")
if ($LASTEXITCODE -ne 0) { throw "Failed to build the GUI." }

Write-Host "[3/3] Assembling release directory..."
Copy-Item (Join-Path $CoreDist "trans-novel.exe") (Join-Path $ReleaseDir "trans-novel.exe") -Force
New-Item -ItemType Directory -Force -Path (Join-Path $ReleaseDir "licenses") | Out-Null
Copy-Item (Join-Path $CoreRoot "LICENSE") (Join-Path $ReleaseDir "licenses\WENYI-LICENSE.txt") -Force
Copy-Item (Join-Path $Root "LICENSE") (Join-Path $ReleaseDir "LICENSE.txt") -Force

Write-Host "Build complete: $ReleaseDir"
Write-Host "Distribute the complete release directory, not only the GUI executable."
