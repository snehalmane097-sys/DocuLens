# Run from any directory; explicitly load this checkout's exported FastAPI app.
param([ValidateRange(1, 65535)][int]$Port = 8000)
$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw "Backend Python is missing: $python"
}
Push-Location $PSScriptRoot
try {
    & $python -c "import app.main; routes=[r for r in app.main.app.routes if r.path == '/api/documents/analyze' and 'POST' in r.methods]; print('Loading:', app.main.__file__); assert len(routes) == 1, 'Expected exactly one POST /api/documents/analyze'; print('PDF analysis route registered')"
    if ($LASTEXITCODE -ne 0) { throw 'Backend app import or route registration check failed.' }
    $uvicornArgs = @('-m', 'uvicorn', 'app.main:app', '--app-dir', $PSScriptRoot,
        '--host', '127.0.0.1', '--port', "$Port", '--reload',
        '--reload-dir', (Join-Path $PSScriptRoot 'app'))
    $envFile = Join-Path $PSScriptRoot '.env'
    if (Test-Path -LiteralPath $envFile) { $uvicornArgs += @('--env-file', $envFile) }
    & $python @uvicornArgs
    if ($LASTEXITCODE -ne 0) { throw "Uvicorn exited with code $LASTEXITCODE." }
}
finally { Pop-Location }
