param(
    [switch]$Coverage
)

$ErrorActionPreference = "Stop"

$venvPython = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"

if ($Coverage) {
    & $venvPython -m pytest --cov=src --cov-report=term-missing
} else {
    & $venvPython -m pytest
}
