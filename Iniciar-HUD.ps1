$ErrorActionPreference = 'Stop'
$hudPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourcePath = Join-Path $env:LOCALAPPDATA 'OpenJarvis\src'
$uvPath = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links\uv.exe'
$pythonPath = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'
$ollamaPath = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'

if (-not (Test-Path $uvPath)) { throw 'O uv não foi encontrado. Reinstale o OpenJarvis primeiro.' }
if (-not (Test-Path $sourcePath)) { throw 'A pasta do OpenJarvis não foi encontrada.' }
if (-not (Test-Path $pythonPath)) { throw 'O Python necessário para o HUD não foi encontrado.' }
if (-not (Test-Path $ollamaPath)) { throw 'O Ollama necessário para o A.T.L.A.S não foi encontrado.' }

if (-not (Get-NetTCPConnection -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue)) {
  Start-Process -FilePath $ollamaPath -ArgumentList @('serve') -WindowStyle Hidden
  Start-Sleep -Seconds 2
}
if (-not (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)) {
  # Permite exclusivamente a página local do HUD, sem expor a API para a rede.
  $env:OPENJARVIS_CORS_ORIGINS = 'http://127.0.0.1:8787'
  Start-Process -FilePath $uvPath -ArgumentList @('run','jarvis','serve','--host','127.0.0.1','--port','8000','--engine','ollama','--model','qwen3.5:4b','--agent','simple') -WorkingDirectory $sourcePath -WindowStyle Hidden
}
if (-not (Get-NetTCPConnection -LocalPort 8787 -State Listen -ErrorAction SilentlyContinue)) {
  Start-Process -FilePath $pythonPath -ArgumentList @('atlas_server.py') -WorkingDirectory $hudPath -WindowStyle Hidden
}
Start-Sleep -Seconds 3
Start-Process 'http://127.0.0.1:8787'
