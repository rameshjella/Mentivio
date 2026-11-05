$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..
& "$PSScriptRoot\..\.venv\Scripts\python.exe" -m streamlit run app\mentivio_app.py --server.headless true --server.port 8501

