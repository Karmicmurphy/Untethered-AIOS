$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests -v
