$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$BaseDir = [System.IO.Path]::GetFullPath((Join-Path $ScriptDir "Studio-Portable-RAG"))
if (-not (Test-Path (Join-Path $BaseDir "Ollama\ollama.exe"))) {
    $alt = [System.IO.Path]::GetFullPath((Join-Path $ScriptDir "Portable_RAG"))
    if (Test-Path (Join-Path $alt "Ollama\ollama.exe")) { $BaseDir = $alt }
}
$Port = if ($env:RAG_GUI_PORT) { $env:RAG_GUI_PORT } else { "8501" }

if (-not (Test-Path (Join-Path $BaseDir "Ollama\ollama.exe"))) {
    Write-Host "[ERROR] Portable RAG not found. Run .\build.ps1 first (expect Studio-Portable-RAG\Ollama\ollama.exe)." -ForegroundColor Red
    exit 1
}

function Sync-GuiAssets {
    Copy-Item -Path (Join-Path $ScriptDir "gui_backend.py") -Destination (Join-Path $BaseDir "gui_backend.py") -Force
    Copy-Item -Path (Join-Path $ScriptDir "agent_tools.py") -Destination (Join-Path $BaseDir "agent_tools.py") -Force
    Copy-Item -Path (Join-Path $ScriptDir "query.py") -Destination (Join-Path $BaseDir "query.py") -Force
    Copy-Item -Path (Join-Path $ScriptDir "hybrid_search.py") -Destination (Join-Path $BaseDir "hybrid_search.py") -Force
    Copy-Item -Path (Join-Path $ScriptDir "ingest.py") -Destination (Join-Path $BaseDir "ingest.py") -Force
    if (Test-Path -LiteralPath (Join-Path $ScriptDir "index.html")) {
        Copy-Item -Path (Join-Path $ScriptDir "index.html") -Destination (Join-Path $BaseDir "index.html") -Force
    }
    if (Test-Path -LiteralPath (Join-Path $ScriptDir "static")) {
        Copy-Item -Path (Join-Path $ScriptDir "static") -Destination (Join-Path $BaseDir "static") -Recurse -Force
    }
    if (Test-Path -LiteralPath (Join-Path $ScriptDir "util")) {
        Copy-Item -Path (Join-Path $ScriptDir "util") -Destination (Join-Path $BaseDir "util") -Recurse -Force
    }
}

Sync-GuiAssets

$pythonExe = Join-Path $BaseDir "Python\python.exe"
if (-not (Test-Path -LiteralPath $pythonExe)) {
    Write-Host "[ERROR] Python not found at $pythonExe" -ForegroundColor Red
    exit 1
}

$env:OLLAMA_MODELS = if ($env:OLLAMA_MODELS) { $env:OLLAMA_MODELS } else { Join-Path $BaseDir "Models" }
if (-not $env:CUDA_VISIBLE_DEVICES) { $env:CUDA_VISIBLE_DEVICES = "0" }
if (-not $env:OLLAMA_KEEP_ALIVE) { $env:OLLAMA_KEEP_ALIVE = "-1" }
if (-not $env:EMBEDDING_MODEL) { $env:EMBEDDING_MODEL = "mxbai-embed-large" }

$embedModel = $env:EMBEDDING_MODEL
$ollamaBin = Join-Path $BaseDir "Ollama\ollama.exe"
$ollamaProc = $null
$ollamaAlready = $false

Write-Host "[GUI] Starting / reusing Ollama (needed for ingest embeddings & chat)..." -ForegroundColor Cyan
try {
    Invoke-RestMethod -Uri "http://127.0.0.1:11434/" -TimeoutSec 2 -ErrorAction Stop | Out-Null
    $ollamaAlready = $true
    Write-Host "            Existing Ollama on :11434 — reusing." -ForegroundColor Gray
} catch {
    $ollamaProc = Start-Process -FilePath $ollamaBin -ArgumentList "serve" -WindowStyle Hidden -PassThru
    Write-Host "            Waiting for http://127.0.0.1:11434 (max 30s)..." -ForegroundColor Gray
    $ready = $false
    for ($t = 0; $t -lt 30; $t++) {
        try {
            Invoke-RestMethod -Uri "http://127.0.0.1:11434/" -TimeoutSec 2 -ErrorAction Stop | Out-Null
            $ready = $true
            break
        } catch { Start-Sleep -Seconds 1 }
    }
    if (-not $ready) {
        if ($ollamaProc) { Stop-Process -Id $ollamaProc.Id -Force -ErrorAction SilentlyContinue }
        Write-Host "[ERROR] Ollama did not become ready within 30 seconds." -ForegroundColor Red
        exit 1
    }
    Write-Host "            Ollama is ready." -ForegroundColor Gray
}

Write-Host "            Embed warmup: $embedModel" -ForegroundColor Gray
try {
    $body = @{ model = $embedModel; input = "warmup" } | ConvertTo-Json
    Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/embed" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 30 | Out-Null
} catch {
    Write-Host "            (warmup skipped — run: ollama pull $embedModel)" -ForegroundColor DarkYellow
}

Write-Host "Dashboard: http://127.0.0.1:${Port}/" -ForegroundColor Cyan
Write-Host "Working dir: $BaseDir (close window or Ctrl+C; Ollama stops if gui.ps1 started it)" -ForegroundColor Gray
Set-Location -LiteralPath $BaseDir

try {
    & $pythonExe -m uvicorn gui_backend:app --host 127.0.0.1 --port $Port
} finally {
    if ($ollamaAlready) {
        Write-Host "Ollama left running (was already active before the dashboard started)." -ForegroundColor Gray
    } elseif ($ollamaProc) {
        Write-Host "Shutting down Ollama server (started by gui.ps1)..." -ForegroundColor Gray
        Stop-Process -Id $ollamaProc.Id -Force -ErrorAction SilentlyContinue
    }
}
