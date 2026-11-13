param([string]$PythonExe = 'python')
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'Windows distribution must be built on Windows.' }
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectRoot
try {
    # Never publish an archive left over from an earlier successful build.
    Remove-Item release/SmartHome-Windows.zip, release/windows-check.json -ErrorAction SilentlyContinue
    & $PythonExe -m pytest backend/tests -q
    if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed.' }
    Push-Location frontend
    try {
        npm ci
        if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
        npm run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
    } finally { Pop-Location }
    & $PythonExe -m PyInstaller --noconfirm --clean --distpath release --workpath build packaging/SmartHome.spec
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }
    Copy-Item docs/USER_README.txt release/SmartHome-Release/README.txt
    & $PythonExe scripts/check_release.py release/SmartHome-Release/SmartHome.exe --report release/windows-check.json
    if ($LASTEXITCODE -ne 0) { throw 'Packaged application smoke checks failed.' }
    Compress-Archive -Path release/SmartHome-Release -DestinationPath release/SmartHome-Windows.zip -Force
} finally { Pop-Location }
