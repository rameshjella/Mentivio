$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..
& "$PSScriptRoot\..\.venv\Scripts\python.exe" -m app.mentivio_app
