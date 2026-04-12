$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot

$DbPath = ""
$Model = ""
$NoOllama = $false
$OllamaTimeout = 30
$QueryArgs = New-Object System.Collections.ArrayList
$raw = @($args)
$i = 0
while ($i -lt $raw.Count) {
    $a = $raw[$i]
    if ($a -eq "--db-path") {
        $i++
        if ($i -ge $raw.Count) { throw "--db-path requires a value" }
        $DbPath = $raw[$i]
        $i++
        continue
    }
    if ($a -eq "--model") {
        $i++
        if ($i -ge $raw.Count) { throw "--model requires a value" }
        $Model = $raw[$i]
        $i++
        continue
    }
    if ($a -eq "--no-ollama") {
        $NoOllama = $true
        $i++
        continue
    }
    if ($a -eq "--ollama-timeout") {
        $i++
        if ($i -ge $raw.Count) { throw "--ollama-timeout requires a value" }
        $OllamaTimeout = [int]$raw[$i]
        $i++
        continue
    }
    if ($a -eq "-h" -or $a -eq "--help") {
        Write-Host @"
Usage: .\query.ps1 [query.ps1 options] [query.py options ...]

query.ps1 options:
  --db-path PATH       VectorDB directory (DB_PATH)
  --model NAME         Embedding model (EMBEDDING_MODEL)
  --no-ollama          Do not start Ollama; expect server on :11434
  --ollama-timeout N   Seconds to wait for Ollama (default: 30)
  -h, --help           This help

All other arguments are passed to query.py.
"@
        exit 0
    }
    [void]$QueryArgs.Add($a)
    $i++
}

$BaseDir = [System.IO.Path]::GetFullPath((Join-Path $ScriptDir "Studio-Portable-RAG"))
if (-not (Test-Path (Join-Path $BaseDir "Ollama\ollama.exe"))) {
    $alt = [System.IO.Path]::GetFullPath((Join-Path $ScriptDir "Portable_RAG"))
    if (Test-Path (Join-Path $alt "Ollama\ollama.exe")) { $BaseDir = $alt }
}

if (-not (Test-Path (Join-Path $BaseDir "Ollama\ollama.exe"))) {
    Write-Host "[ERROR] Portable RAG not found. Run .\build.ps1 first." -ForegroundColor Red
    exit 1
}

Write-Host "--------------------------------------------------------" -ForegroundColor Cyan
Write-Host " Universal Domain RAG - Query Runner" -ForegroundColor Cyan
Write-Host " BaseDir         : $BaseDir" -ForegroundColor Gray
Write-Host "--------------------------------------------------------" -ForegroundColor Cyan

$env:OLLAMA_MODELS = Join-Path $BaseDir "Models"
if (-not $env:CUDA_VISIBLE_DEVICES) { $env:CUDA_VISIBLE_DEVICES = "0" }
if (-not $env:OLLAMA_KEEP_ALIVE) { $env:OLLAMA_KEEP_ALIVE = "-1" }
if (-not $env:OLLAMA_GPU_OVERHEAD) { $env:OLLAMA_GPU_OVERHEAD = "536870912" }

if ($Model) {
    $env:EMBEDDING_MODEL = $Model
    Write-Host " Embedding model : $Model (from --model)" -ForegroundColor Gray
}

if ($DbPath) {
    New-Item -ItemType Directory -Force -Path $DbPath | Out-Null
    $env:DB_PATH = [System.IO.Path]::GetFullPath($DbPath)
    Write-Host " VectorDB path   : $($env:DB_PATH)" -ForegroundColor Gray
} else {
    $env:DB_PATH = [System.IO.Path]::GetFullPath((Join-Path $BaseDir "VectorDB"))
    Write-Host " VectorDB path   : $($env:DB_PATH)" -ForegroundColor Gray
}

$ollamaBin = Join-Path $BaseDir "Ollama\ollama.exe"
$ollamaProc = $null
$ollamaAlready = $false

if (-not $NoOllama) {
    Write-Host "`n[1/2] Starting / reusing local Ollama..." -ForegroundColor Yellow
    $ready = $false
    try {
        Invoke-RestMethod -Uri "http://127.0.0.1:11434/" -TimeoutSec 2 -ErrorAction Stop | Out-Null
        $ready = $true
        $ollamaAlready = $true
        Write-Host "            Existing Ollama on :11434 — reusing." -ForegroundColor Gray
    } catch {
        $ollamaProc = Start-Process -FilePath $ollamaBin -ArgumentList "serve" -WindowStyle Hidden -PassThru
        Write-Host "            Waiting for http://127.0.0.1:11434 (max ${OllamaTimeout}s)..." -ForegroundColor Gray
        for ($t = 0; $t -lt $OllamaTimeout; $t++) {
            try {
                Invoke-RestMethod -Uri "http://127.0.0.1:11434/" -TimeoutSec 2 -ErrorAction Stop | Out-Null
                $ready = $true
                break
            } catch { Start-Sleep -Seconds 1 }
        }
        if (-not $ready) {
            if ($ollamaProc) { Stop-Process -Id $ollamaProc.Id -Force -ErrorAction SilentlyContinue }
            Write-Host "[ERROR] Ollama did not become ready within ${OllamaTimeout}s." -ForegroundColor Red
            exit 1
        }
        Write-Host "            Ollama is ready." -ForegroundColor Gray
    }
    $emb = if ($env:EMBEDDING_MODEL) { $env:EMBEDDING_MODEL } else { "nomic-embed-text" }
    Write-Host "            Warmup embed: $emb" -ForegroundColor Gray
    try {
        $body = @{ model = $emb; input = "warmup" } | ConvertTo-Json
        Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/embed" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 30 | Out-Null
    } catch {
        Write-Host "    (warmup skipped — run: ollama pull $emb)" -ForegroundColor DarkYellow
    }
} else {
    Write-Host "`n[1/2] Skipping Ollama start (--no-ollama)." -ForegroundColor Yellow
}

Write-Host "`n[2/2] Running query.py..." -ForegroundColor Yellow
Copy-Item -Path (Join-Path $ScriptDir "query.py") -Destination (Join-Path $BaseDir "query.py") -Force
if (Test-Path (Join-Path $ScriptDir "hybrid_search.py")) {
    Copy-Item -Path (Join-Path $ScriptDir "hybrid_search.py") -Destination (Join-Path $BaseDir "hybrid_search.py") -Force
}

$pythonExe = Join-Path $BaseDir "Python\python.exe"
if (-not (Test-Path -LiteralPath $pythonExe)) {
    $altPy = Join-Path $BaseDir "PyEnv\python.exe"
    if (Test-Path -LiteralPath $altPy) { $pythonExe = $altPy }
}

if (-not (Test-Path -LiteralPath $pythonExe)) {
    Write-Host "[ERROR] Python not found under $BaseDir\Python" -ForegroundColor Red
    exit 1
}

$queryScript = Join-Path $BaseDir "query.py"
$code = 0
try {
    & $pythonExe $queryScript @QueryArgs
    $code = $LASTEXITCODE
} finally {
    if (-not $NoOllama) {
        if ($ollamaAlready) {
            Write-Host "Ollama left running (was already active)." -ForegroundColor Gray
        } elseif ($ollamaProc) {
            Write-Host "Shutting down Ollama server..." -ForegroundColor Gray
            Stop-Process -Id $ollamaProc.Id -Force -ErrorAction SilentlyContinue
        }
    }
}

if ($code -ne 0) {
    Write-Host "[ERROR] query.py exited with code $code." -ForegroundColor Red
}
exit $code
