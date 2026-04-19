param(
    [string]$Model = "nomic-embed-text",
    [string]$Mode = "",           # code|domain|rfc|rally|customer|mib|wiki|release-notes|theory|community|status
    [string]$Domain = "general",  # nms|occt|spice|kicad|geda|general
    [string]$Collection = "",     # optional override for Chroma collection name
    [string]$RallyProject = "",
    [string]$RallyFilter = "",
    [string]$ConfluenceSpace = "",
    [string]$ConfluenceLabel = "",
    [switch]$MibKeepDeprecated,
    [switch]$DryRun,
    [switch]$Force,
    [switch]$CleanStale,
    [switch]$RecreateCollection,
    [switch]$Verbose,
    [string]$Repo = "",        # Optional: ingest only this sub-folder of the source folder
    [string]$Source = "",      # Optional: source folder or file
    [string]$DBPath = "",      # Optional: VectorDB folder
    [int]$Workers = 2,          # Parallel embedding threads
    [switch]$GitDiff,
    [string]$GitDiffBase = "",
    [string]$ConceptRegistry = ""
)

# Default chat model (query.py / dashboard): gemma3:27b (128K context, fits A6000 48GB at Q4)
# Override: $env:RAG_LLM_MODEL = "qwen2.5-coder:32b"
# Pull: ollama pull gemma3:27b

$ErrorActionPreference = "Stop"
# Prefer Studio-Portable-RAG (build.ps1 default), then Portable_RAG.
$BaseDir = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "Studio-Portable-RAG"))
if (-not (Test-Path (Join-Path $BaseDir "Ollama\ollama.exe"))) {
    $alt = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "Portable_RAG"))
    if (Test-Path (Join-Path $alt "Ollama\ollama.exe")) { $BaseDir = $alt }
}

# Verify the environment has been built (after optional BaseDir auto-detect above)
if (-not (Test-Path (Join-Path $BaseDir "Ollama\ollama.exe"))) {
    Write-Host "[ERROR] Portable RAG not found. Run build.ps1 first." -ForegroundColor Red
    exit 1
}

Write-Host "--------------------------------------------------------" -ForegroundColor Cyan
Write-Host " Universal Domain RAG - Ingestion Runner" -ForegroundColor Cyan
Write-Host " BaseDir         : $BaseDir" -ForegroundColor Gray
Write-Host " Mode            : $(if ($Mode) { $Mode } else { '(legacy / default)' })" -ForegroundColor Cyan
Write-Host " Domain          : $Domain" -ForegroundColor Cyan
Write-Host " Embedding model : $Model" -ForegroundColor Cyan
Write-Host " Embed workers   : $Workers" -ForegroundColor Cyan
Write-Host "--------------------------------------------------------" -ForegroundColor Cyan

# GPU Prerequisite Check (non-fatal -- falls back to CPU if no GPU found)
Write-Host "`n[GPU] Checking for NVIDIA GPU..." -ForegroundColor Cyan
try {
    $gpuInfo = & nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>$null
    if ($gpuInfo) {
        Write-Host " GPU detected: $gpuInfo" -ForegroundColor Green
    } else {
        Write-Host " WARNING: nvidia-smi returned no output. Running on CPU." -ForegroundColor DarkYellow
    }
} catch {
    Write-Host " WARNING: nvidia-smi not found. Running on CPU." -ForegroundColor DarkYellow
}

# 1. Configure GPU environment for Ollama
Write-Host "`n[1/3] Configuring GPU environment..." -ForegroundColor Yellow
$env:OLLAMA_MODELS = Join-Path $BaseDir "Models"
$env:CUDA_VISIBLE_DEVICES = "0"
$env:OLLAMA_NUM_PARALLEL = "$Workers"
$env:EMBED_WORKERS = "$Workers"
$env:OLLAMA_KEEP_ALIVE = "-1"
$env:OLLAMA_GPU_OVERHEAD = "536870912"
$env:EMBEDDING_MODEL = $Model

# -Source / -DBPath: resolve to absolute paths NOW, before Push-Location
if ($Source -ne "") {
    if (-not (Test-Path -LiteralPath $Source)) {
        Write-Host "[ERROR] Source path not found: $Source" -ForegroundColor Red
        exit 1
    }
    $env:SOURCE_FOLDER = (Resolve-Path -LiteralPath $Source).Path
    Write-Host " Source path     : $env:SOURCE_FOLDER" -ForegroundColor Gray
} else {
    $env:SOURCE_FOLDER = ""
}

# Default source for modes that need a folder on disk (mode-specific layout under portable base)
$modeDefaultSources = @{
    "code"          = "Codebase"
    "domain"        = "DomainDocs"
    "rfc"           = "RFCs"
    "mib"           = "MIBs"
    "community"     = "CommunityData"
    "release-notes" = "Codebase"
    "theory"        = "DomainDocs"
    "customer"      = "CommunityData"
}
if ($Mode -ne "status" -and $Mode -ne "rally" -and $Mode -ne "wiki" -and $env:SOURCE_FOLDER -eq "") {
    $defaultFolder = $modeDefaultSources[$Mode]
    if (-not $defaultFolder) { $defaultFolder = "Codebase" }
    $defaultSrc = Join-Path $BaseDir $defaultFolder
    if (Test-Path -LiteralPath $defaultSrc) {
        $env:SOURCE_FOLDER = (Resolve-Path -LiteralPath $defaultSrc).Path
        Write-Host " Default source  : $env:SOURCE_FOLDER (mode=$Mode -> $defaultFolder)" -ForegroundColor Gray
    }
}

if ($DBPath -ne "") {
    if (-not (Test-Path -LiteralPath $DBPath)) {
        New-Item -ItemType Directory -Force -Path $DBPath | Out-Null
    }
    $env:DB_PATH = (Resolve-Path -LiteralPath $DBPath).Path
    Write-Host " VectorDB path   : $env:DB_PATH" -ForegroundColor Gray
} else {
    $env:DB_PATH = [System.IO.Path]::GetFullPath((Join-Path $BaseDir "VectorDB"))
    Write-Host " VectorDB path   : $env:DB_PATH" -ForegroundColor Gray
}

# Decide whether -Repo is a sub-folder filter (multi-repo) or a name override (single-repo mode).
$env:INGEST_REPO = ""
$env:REPO_NAME = ""
if ($Repo -ne "") {
    $codebaseDefault = Join-Path $BaseDir "Codebase"
    $effectiveSource = if ($env:SOURCE_FOLDER -ne "") { $env:SOURCE_FOLDER } else { $codebaseDefault }
    $sourceFolderName = Split-Path $effectiveSource -Leaf
    if ($Repo -eq $sourceFolderName) {
        $env:REPO_NAME = $Repo
        Write-Host "            Repo name      : $Repo (single-repo mode)" -ForegroundColor Gray
    } elseif (Test-Path -LiteralPath (Join-Path $effectiveSource $Repo)) {
        $env:INGEST_REPO = $Repo
        Write-Host "            Repo filter    : $Repo (sub-folder of source)" -ForegroundColor Gray
    } else {
        $env:REPO_NAME = $Repo
        Write-Host "            Repo name      : $Repo (single-repo mode - alias for '$sourceFolderName')" -ForegroundColor Gray
    }
}

# 2. Start Ollama and wait until it is actually ready
Write-Host "[2/3] Starting local Ollama server (GPU-accelerated)..." -ForegroundColor Yellow

$ollamaProc = $null
$OllamaAlreadyRunning = $false
try {
    Invoke-RestMethod -Uri "http://localhost:11434" -ErrorAction Stop | Out-Null
    $OllamaAlreadyRunning = $true
    Write-Host "            Existing Ollama instance detected on :11434. Reusing it." -ForegroundColor Gray
} catch {
    $ollamaProc = Start-Process `
        -FilePath (Join-Path $BaseDir "Ollama\ollama.exe") `
        -ArgumentList "serve" `
        -NoNewWindow `
        -PassThru
}

if (-not $OllamaAlreadyRunning) {
    Write-Host "        Waiting http://localhost:11434 for readiness..." -ForegroundColor Gray
    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        try {
            Invoke-RestMethod -Uri "http://localhost:11434" -ErrorAction Stop | Out-Null
            $ready = $true
            break
        } catch {
            Start-Sleep -Seconds 1
        }
    }

    if (-not $ready) {
        if ($ollamaProc -and -not $ollamaProc.HasExited) {
            taskkill /PID $ollamaProc.Id /F /T 2>$null | Out-Null
        }
        throw "Ollama did not become ready within 30 seconds."
    }

    Write-Host "        Ollama is ready." -ForegroundColor Gray
}

# GPU Verification -- confirm the chosen model is loaded on GPU, not CPU
Write-Host "    Verifying GPU usage for '$Model'..." -ForegroundColor Gray
try {
    Invoke-RestMethod -Uri "http://localhost:11434/api/embed" `
        -Method Post `
        -ContentType "application/json" `
        -Body ('{"model": "' + $Model + '", "input": "warmup"}') `
        -ErrorAction Stop | Out-Null

    $ps = Invoke-RestMethod -Uri "http://localhost:11434/api/ps" -ErrorAction Stop
    $modelEntry = $ps.models | Where-Object { $_.name -like "*$Model*" }
    if ($modelEntry) {
        $details = $modelEntry | ConvertTo-Json -Compress
        Write-Host "    Model loaded: $details" -ForegroundColor Green
    } else {
        Write-Host "    Model not yet listed in /api/ps (may load on first request)." -ForegroundColor Gray
    }
} catch {
    Write-Host "    GPU verification skipped: $($_.Exception.Message)" -ForegroundColor DarkYellow
}

# 3. Run the ingestion pipeline
Write-Host "[3/3] Running ingestion pipeline..." -ForegroundColor Yellow
Copy-Item -Path (Join-Path $PSScriptRoot "ingest.py") -Destination (Join-Path $BaseDir "ingest.py") -Force
Copy-Item -Path (Join-Path $PSScriptRoot "mcp_server.py") -Destination (Join-Path $BaseDir "mcp_server.py") -Force -ErrorAction SilentlyContinue
Copy-Item -Path (Join-Path $PSScriptRoot "domain_feeder.py") -Destination (Join-Path $BaseDir "domain_feeder.py") -Force -ErrorAction SilentlyContinue
Copy-Item -Path (Join-Path $PSScriptRoot "hybrid_search.py") -Destination (Join-Path $BaseDir "hybrid_search.py") -Force -ErrorAction SilentlyContinue
Copy-Item -Path (Join-Path $PSScriptRoot "sanitizer.py") -Destination (Join-Path $BaseDir "sanitizer.py") -Force -ErrorAction SilentlyContinue
Copy-Item -Path (Join-Path $PSScriptRoot "concept_registry.json") -Destination (Join-Path $BaseDir "concept_registry.json") -Force -ErrorAction SilentlyContinue

$pythonExe = Join-Path $BaseDir "Python\python.exe"
if (-not (Test-Path -LiteralPath $pythonExe)) {
    $alt = Join-Path $BaseDir "PyEnv\python.exe"
    if (Test-Path -LiteralPath $alt) {
        $pythonExe = $alt
    }
}

Push-Location -LiteralPath $BaseDir
try {
    $ingestScript = Join-Path $BaseDir "ingest.py"
    $ingestArgs = New-Object System.Collections.ArrayList
    [void]$ingestArgs.Add($ingestScript)
    if ($Mode -ne "") {
        [void]$ingestArgs.Add("--mode"); [void]$ingestArgs.Add($Mode)
    }
    if ($Domain -ne "") {
        [void]$ingestArgs.Add("--domain"); [void]$ingestArgs.Add($Domain)
    }
    if ($Collection -ne "") {
        [void]$ingestArgs.Add("--collection"); [void]$ingestArgs.Add($Collection)
    }
    if ($env:DB_PATH -ne "") {
        [void]$ingestArgs.Add("--db-path"); [void]$ingestArgs.Add($env:DB_PATH)
    }
    if ($Mode -ne "status" -and $env:SOURCE_FOLDER -ne "") {
        [void]$ingestArgs.Add("--source"); [void]$ingestArgs.Add($env:SOURCE_FOLDER)
    }
    if ($RallyProject -ne "") {
        [void]$ingestArgs.Add("--rally-project"); [void]$ingestArgs.Add($RallyProject)
    }
    if ($RallyFilter -ne "") {
        [void]$ingestArgs.Add("--rally-filter"); [void]$ingestArgs.Add($RallyFilter)
    }
    if ($ConfluenceSpace -ne "") {
        [void]$ingestArgs.Add("--confluence-space"); [void]$ingestArgs.Add($ConfluenceSpace)
    }
    if ($ConfluenceLabel -ne "") {
        [void]$ingestArgs.Add("--confluence-label"); [void]$ingestArgs.Add($ConfluenceLabel)
    }
    if ($MibKeepDeprecated) { [void]$ingestArgs.Add("--mib-keep-deprecated") }
    if ($DryRun) { [void]$ingestArgs.Add("--dry-run") }
    if ($Force) { [void]$ingestArgs.Add("--force") }
    if ($CleanStale) { [void]$ingestArgs.Add("--clean-stale") }
    if ($RecreateCollection) { [void]$ingestArgs.Add("--recreate-collection") }
    if ($Verbose) { [void]$ingestArgs.Add("--verbose") }
    if ($GitDiff) { [void]$ingestArgs.Add("--git-diff") }
    if ($GitDiffBase -ne "") {
        [void]$ingestArgs.Add("--git-diff-base"); [void]$ingestArgs.Add($GitDiffBase)
    }
    if ($ConceptRegistry -ne "") {
        [void]$ingestArgs.Add("--concept-registry"); [void]$ingestArgs.Add($ConceptRegistry)
    }

    $ingestProc = Start-Process -FilePath $pythonExe `
        -ArgumentList ($ingestArgs.ToArray()) `
        -WorkingDirectory $BaseDir `
        -Wait -PassThru -NoNewWindow
    if ($ingestProc.ExitCode -ne 0) {
        Write-Host "[ERROR] ingest.py failed with exit code $($ingestProc.ExitCode)." -ForegroundColor Red
        exit $ingestProc.ExitCode
    }
} finally {
    Pop-Location
    if ($OllamaAlreadyRunning) {
        Write-Host "Ollama left running (was already active before this script started)." -ForegroundColor Gray
    } elseif ($ollamaProc) {
        Write-Host "Shutting down Ollama server (killing process tree)..." -ForegroundColor Gray
        taskkill /PID $ollamaProc.Id /F /T 2>$null | Out-Null
        Start-Sleep -Milliseconds 500
        $remaining = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
        if ($remaining) {
            $remaining | Stop-Process -Force -ErrorAction SilentlyContinue
            Write-Host "       Cleaned up $($remaining.Count) stray Ollama process(es)." -ForegroundColor Gray
        } else {
            Write-Host "       Ollama fully stopped." -ForegroundColor Gray
        }
    }
}

$resolvedDB = $env:DB_PATH
Write-Host ""
Write-Host " Run finished. VectorDB: $resolvedDB" -ForegroundColor Green
Write-Host " Examples:" -ForegroundColor Cyan
Write-Host "   .\run.ps1 -Mode code -Model mxbai-embed-large" -ForegroundColor Gray
Write-Host "   .\run.ps1 -Mode domain -Domain nms -Source `"$BaseDir\DomainDocs`"" -ForegroundColor Gray
Write-Host "   .\run.ps1 -Mode status" -ForegroundColor Gray
Write-Host "   .\run.ps1 -Mode mib -Domain nms -Source `"$BaseDir\MIBs`"" -ForegroundColor Gray
Write-Host ""
