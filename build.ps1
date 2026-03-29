$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$BaseDir = [System.IO.Path]::GetFullPath((Join-Path $ScriptDir "Studio-Portable-RAG"))

Write-Host " " -ForegroundColor Cyan
Write-Host " Building Universal Domain RAG (Portable)..." -ForegroundColor Cyan
Write-Host " BaseDir (absolute): $BaseDir" -ForegroundColor Gray
Write-Host " " -ForegroundColor Cyan

# -- Helper: robust zip extraction ----------------------------------------------------
# PowerShell's Expand-Archive fails on some zip variants (zip64, split archives).
# tar.exe (built into Windows 10+) handles them correctly.
function Expand-Zip {
    param(
        [string]$ZipPath,
        [string]$DestPath
    )
    Write-Host "      Extracting $(Split-Path $ZipPath -Leaf)..." -ForegroundColor Gray
    & tar -xf "$ZipPath" -C "$DestPath" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "      tar failed (exit $LASTEXITCODE), falling back to Expand-Archive..." -ForegroundColor DarkYellow
        Expand-Archive -Path $ZipPath -DestinationPath $DestPath -Force
    }
}

# -- Helper: download or use pre-downloaded file --------------------------------------
# If a zip with the expected filename exists next to build.ps1, use it directly.
# Otherwise download from the given URL.
# Returns the path to the zip and whether the caller should delete it afterward.
function Get-ZipFile {
    param(
        [string]$FileName,
        [string]$Url,
        [string]$TempDest
    )
    $local = Join-Path $ScriptDir $FileName
    if (Test-Path $local) {
        Write-Host "      Pre-downloaded file found: $FileName (skipping download)" -ForegroundColor Green
        return @{ Path = $local; Delete = $false }
    }
    Write-Host "      Downloading $FileName..." -ForegroundColor Gray
    Invoke-WebRequest -Uri $Url -OutFile $TempDest
    return @{ Path = $TempDest; Delete = $true }
}

# -- GPU Prerequisite Check (non-fatal) -----------------------------------------------
Write-Host "[GPU] Checking for NVIDIA GPU..." -ForegroundColor Cyan
try {
    $gpuInfo = & nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>$null
    if ($gpuInfo) {
        Write-Host "      GPU detected: $gpuInfo" -ForegroundColor Green
    } else {
        Write-Host "      WARNING: nvidia-smi returned no output. Ingestion will run on CPU." -ForegroundColor DarkYellow
    }
} catch {
    Write-Host "      WARNING: nvidia-smi not found. Ingestion will run on CPU." -ForegroundColor DarkYellow
}

# 1. Create Folder Architecture
New-Item -ItemType Directory -Force -Path "$BaseDir\Ollama" | Out-Null
New-Item -ItemType Directory -Force -Path "$BaseDir\Python" | Out-Null
New-Item -ItemType Directory -Force -Path "$BaseDir\Models" | Out-Null
New-Item -ItemType Directory -Force -Path "$BaseDir\Codebase" | Out-Null
New-Item -ItemType Directory -Force -Path "$BaseDir\VectorDB" | Out-Null
New-Item -ItemType Directory -Force -Path "$BaseDir\DomainDocs" | Out-Null
New-Item -ItemType Directory -Force -Path "$BaseDir\RFCs" | Out-Null
New-Item -ItemType Directory -Force -Path "$BaseDir\MIBs" | Out-Null
New-Item -ItemType Directory -Force -Path "$BaseDir\CommunityData" | Out-Null

# 2. Portable Ollama
Write-Host "[1/9] Setting up Portable Ollama Server..." -ForegroundColor Yellow
$OllamaUrl = "https://github.com/ollama/ollama/releases/latest/download/ollama-windows-amd64.zip"
$OllamaZip = Get-ZipFile -FileName "ollama-windows-amd64.zip" `
                         -Url $OllamaUrl `
                         -TempDest "$BaseDir\ollama.zip"
Expand-Zip -ZipPath $OllamaZip.Path -DestPath "$BaseDir\Ollama"
if ($OllamaZip.Delete) { Remove-Item $OllamaZip.Path }

# 3. Embedded Python 3.11
Write-Host "[2/9] Setting up Embedded Python..." -ForegroundColor Yellow
$PythonUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
$PythonZip = Get-ZipFile -FileName "python-3.11.9-embed-amd64.zip" `
                          -Url $PythonUrl `
                          -TempDest "$BaseDir\python.zip"
Expand-Zip -ZipPath $PythonZip.Path -DestPath "$BaseDir\Python"
if ($PythonZip.Delete) { Remove-Item $PythonZip.Path }

# 4. Unlock pip for the embedded runtime
Write-Host "[3/9] Unlocking Python Package Manager..." -ForegroundColor Yellow
$pthFile = "$BaseDir\Python\python311._pth"
(Get-Content $pthFile) -replace '#import site', 'import site' | Set-Content $pthFile

Write-Host "[4/9] Installing PIP..." -ForegroundColor Yellow
$GetPipUrl = "https://bootstrap.pypa.io/get-pip.py"
Invoke-WebRequest -Uri $GetPipUrl -OutFile "$BaseDir\Python\get-pip.py"
& "$BaseDir\Python\python.exe" "$BaseDir\Python\get-pip.py"

# 5. Install RAG dependencies
# langchain-core    -- explicit: required for langchain_core.documents (Document class used by all chunkers)
# langchain         -- LangChain core chains/agents
# langchain-community -- OllamaEmbeddings, Chroma vectorstore
# langchain-text-splitters -- RecursiveCharacterTextSplitter, Language enum
# chromadb          -- local vector database
# tqdm              -- progress bar
# tree-sitter-*     -- C/C++/Java from PyPI; Scheme has no PyPI wheel (pip install from GitHub below; needs git).
Write-Host "[5/9] Installing AI libraries..." -ForegroundColor Yellow
& "$BaseDir\Python\Scripts\pip.exe" install `
    langchain-core `
    langchain `
    langchain-community `
    langchain-text-splitters `
    langchain-ollama `
    langchain-chroma `
    chromadb `
    tqdm `
    "mcp[cli]" `
    tree-sitter `
    tree-sitter-c `
    tree-sitter-cpp `
    tree-sitter-java `
    requests `
    beautifulsoup4
# Pin commit for reproducible builds (ingest uses import tree_sitter_scheme + .language()).
$gitAvailable = $false
try {
    & git --version 2>$null | Out-Null
    $gitAvailable = ($LASTEXITCODE -eq 0)
} catch {}
if ($gitAvailable) {
    & "$BaseDir\Python\Scripts\pip.exe" install "git+https://github.com/6cdh/tree-sitter-scheme.git@c6cb7c7d7a04b3f5d999c28e2e9c0c31b2d50ece"
} else {
    Write-Host "      git not found — skipping tree-sitter-scheme (Scheme chunking will use regex fallback)" -ForegroundColor DarkYellow
}

# 6. Download Embedding Models
Write-Host "[6/9] Downloading Embedding Models..." -ForegroundColor Yellow
$env:OLLAMA_MODELS = "$BaseDir\Models"
$env:CUDA_VISIBLE_DEVICES = "0"
$env:OLLAMA_KEEP_ALIVE = "-1"

$ollamaProc = Start-Process -FilePath "$BaseDir\Ollama\ollama.exe" `
    -ArgumentList "serve" -WindowStyle Hidden -PassThru
Write-Host "    Waiting for Ollama to be ready..." -ForegroundColor Gray
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        Invoke-RestMethod -Uri "http://localhost:11434" -ErrorAction Stop | Out-Null
        $ready = $true; break
    } catch { Start-Sleep -Seconds 1 }
}
if (-not $ready) {
    Stop-Process -Id $ollamaProc.Id -Force -ErrorAction SilentlyContinue
    throw "Ollama did not start within 30 seconds."
}

Write-Host "    Pulling nomic-embed-text (274 MB, fast / long-context)..." -ForegroundColor Gray
& "$BaseDir\Ollama\ollama.exe" pull nomic-embed-text

Write-Host "    Pulling mxbai-embed-large (670 MB, higher accuracy)..." -ForegroundColor Gray
& "$BaseDir\Ollama\ollama.exe" pull mxbai-embed-large

Stop-Process -Id $ollamaProc.Id -Force -ErrorAction SilentlyContinue

# 7. Copy Python scripts + support files
Write-Host "[7/9] Copying scripts and domain RAG support files..." -ForegroundColor Yellow
Copy-Item -Path "$ScriptDir\ingest.py" -Destination "$BaseDir\ingest.py" -Force
Copy-Item -Path "$ScriptDir\mcp_server.py" -Destination "$BaseDir\mcp_server.py" -Force
Copy-Item -Path "$ScriptDir\domain_feeder.py" -Destination "$BaseDir\domain_feeder.py" -Force
Copy-Item -Path "$ScriptDir\sanitizer.py" -Destination "$BaseDir\sanitizer.py" -Force -ErrorAction SilentlyContinue
Copy-Item -Path "$ScriptDir\concept_registry.json" -Destination "$BaseDir\concept_registry.json" -Force -ErrorAction SilentlyContinue

# 8. Post-install validation (imports + optional tree-sitter)
Write-Host "[8/9] Post-install validation smoke test..." -ForegroundColor Yellow
$py = "$BaseDir\Python\python.exe"
& $py -c "import langchain_chroma, chromadb, tqdm; print('core deps: OK')"
& $py -c "import tree_sitter; print('tree-sitter: OK')" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "      tree-sitter optional import failed (C/C++/Java AST will fall back)." -ForegroundColor DarkYellow }
& $py -c "import tree_sitter_scheme; print('tree-sitter-scheme: OK')" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "      tree-sitter-scheme import failed (Scheme chunking will use regex fallback)." -ForegroundColor DarkYellow }

# 9. Merge .cursor/mcp.json (do not wipe other MCP servers)
Write-Host "[9/9] Merging .cursor\mcp.json for Cursor MCP integration..." -ForegroundColor Yellow

$codebaseRagEntry = @{
    command = Join-Path $BaseDir "Python\python.exe"
    args    = @( (Join-Path $BaseDir "mcp_server.py") )
    env     = @{
        OLLAMA_MODELS        = Join-Path $BaseDir "Models"
        OLLAMA_EXE           = Join-Path $BaseDir "Ollama\ollama.exe"
        DB_PATH              = Join-Path $BaseDir "VectorDB"
        MCP_LOG              = Join-Path $BaseDir "mcp_server.log"
        CUDA_VISIBLE_DEVICES = "0"
        OLLAMA_KEEP_ALIVE    = "-1"
    }
}

$cursorDir = Join-Path $Env:USERPROFILE ".cursor"
New-Item -ItemType Directory -Force -Path $cursorDir | Out-Null
$mcpPath = Join-Path $cursorDir "mcp.json"

$serverMap = @{}
if (Test-Path -LiteralPath $mcpPath) {
    try {
        $old = Get-Content -LiteralPath $mcpPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($old.mcpServers) {
            foreach ($p in $old.mcpServers.PSObject.Properties) {
                if ($p.Name -eq "codebase-rag") { continue }
                $serverMap[$p.Name] = $p.Value
            }
        }
    }
    catch {
        Write-Host "      WARNING: existing mcp.json malformed; backing up to mcp.json.bak" -ForegroundColor DarkYellow
        Copy-Item -LiteralPath $mcpPath -Destination ($mcpPath + ".bak") -Force
    }
}
$serverMap["codebase-rag"] = $codebaseRagEntry
$mcpRoot = @{ mcpServers = $serverMap }
$outJson = $mcpRoot | ConvertTo-Json -Depth 12
[System.IO.File]::WriteAllText($mcpPath, $outJson, [System.Text.UTF8Encoding]::new($false))
Write-Host "         Written: $mcpPath" -ForegroundColor Green

Write-Host "****************************************************************" -ForegroundColor Green
Write-Host "* Build complete. Portable RAG is ready.                       *" -ForegroundColor Green
Write-Host "****************************************************************" -ForegroundColor Green
Write-Host "* Multi-repo layout (recommended):                             *" -ForegroundColor Cyan
Write-Host "*   Portable RAG\Codebase\<repo-name>\   <- one folder per repo *" -ForegroundColor Cyan
Write-Host "*   e.g. Codebase\auth-service\                                *" -ForegroundColor Cyan
Write-Host "*        Codebase\payment-gateway\                             *" -ForegroundColor Cyan
Write-Host "****************************************************************" -ForegroundColor Green
Write-Host "* Code ingest:             .\run.ps1 -Mode code                *" -ForegroundColor Green
Write-Host "* Domain docs:             .\run.ps1 -Mode domain -Domain nms *" -ForegroundColor Green
Write-Host "* Status:                  .\run.ps1 -Mode status             *" -ForegroundColor Green
Write-Host "* GPU model:               .\run.ps1 -Model mxbai-embed-large  *" -ForegroundColor Green
Write-Host "****************************************************************" -ForegroundColor Green
Write-Host "* Query interactively:     .\query.ps1                         *" -ForegroundColor Green
Write-Host "* Filter by repo:          .\query.ps1 -Repo auth-service       *" -ForegroundColor Green
Write-Host "* Build super prompt:      .\prompt.ps1 -Query 'Auth Flow'     *" -ForegroundColor Green
Write-Host "****************************************************************" -ForegroundColor Green
Write-Host "* MCP live search (Cursor AI):                                 *" -ForegroundColor Cyan
Write-Host "*   .cursor\mcp.json has been written with your local paths    *" -ForegroundColor Cyan
Write-Host "*   In Cursor: Settings -> MCP -> you should see 'codebase-search' *" -ForegroundColor Cyan
Write-Host "*   Then ask Cursor AI: 'Find all JWT validation code'         *" -ForegroundColor Cyan
Write-Host "****************************************************************" -ForegroundColor Green
