# SPDX-License-Identifier: MIT
# Process-local environment only. Does not select EIM, install tools or flash.
param(
    [Parameter(Mandatory=$true)][string]$PrivateDirectory,
    [string]$IdfPath = 'C:/esp/v5.5.5/esp-idf',
    [string]$IdfPythonEnvironment = 'C:/Users/licod/.espressif/python_env/idf5.5_py3.13_env',
    [string]$IdfToolsPath = 'C:/Espressif/tools'
)
$ErrorActionPreference = 'Stop'
$privateRoot = (Resolve-Path -LiteralPath $PrivateDirectory).Path
$fixtureRoot = $PSScriptRoot
$repositoryRoot = (Resolve-Path -LiteralPath (Join-Path $fixtureRoot '../..')).Path
if ($privateRoot.StartsWith($repositoryRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Build directory must be outside Git'
}
$pythonExecutable = Join-Path $IdfPythonEnvironment 'Scripts/python.exe'
& $pythonExecutable -c 'import serial, esptool, idf_component_manager'
if ($LASTEXITCODE -ne 0) { throw 'Existing ESP-IDF Python environment unavailable' }
if (-not (Test-Path -LiteralPath (Join-Path $privateRoot 'firmware-config.json'))) {
    throw 'Private firmware configuration required'
}
$env:XMQR_E01_PRIVATE_DIR = $privateRoot
$env:CARGO_TARGET_DIR = Join-Path $privateRoot 'target'
$env:CARGO_WORKSPACE_DIR = $fixtureRoot
$env:IDF_PATH = $IdfPath
$env:IDF_TOOLS_PATH = $IdfToolsPath
$env:IDF_PYTHON_ENV_PATH = $IdfPythonEnvironment
$env:ESP_IDF_VERSION = 'v5.5.5'
$env:ESP_IDF_TOOLS_INSTALL_DIR = 'fromenv'
$env:ESP_IDF_PATH_ISSUES = 'warn'
$env:ESP_ROM_ELF_DIR = Join-Path $IdfToolsPath 'esp-rom-elfs/20241011'
$env:LIBCLANG_PATH = Join-Path $env:USERPROFILE '.rustup/toolchains/esp/xtensa-esp32-elf-clang/esp-clang/bin'
$toolDirectories = @(
    $env:LIBCLANG_PATH,
    (Join-Path $IdfPath 'tools'),
    (Join-Path $IdfToolsPath 'idf-exe/1.0.3'),
    (Join-Path $IdfPythonEnvironment 'Scripts'),
    (Join-Path $IdfToolsPath 'cmake/3.30.2/bin'),
    (Join-Path $IdfToolsPath 'ninja/1.12.1'),
    (Join-Path $IdfToolsPath 'xtensa-esp-elf/esp-14.2.0_20260121/xtensa-esp-elf/bin'),
    (Join-Path $env:USERPROFILE '.cargo/bin')
)
$env:PATH = ($toolDirectories -join ';') + ';' + $env:PATH
Push-Location -LiteralPath $fixtureRoot
try {
    & cargo +esp build --locked --release
    if ($LASTEXITCODE -ne 0) { throw 'E01 firmware build failed; board not flashed' }
} finally { Pop-Location }
