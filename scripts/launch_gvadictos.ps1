[CmdletBinding()]
param(
    [int]$Port = 8501,
    [string]$HostName = "localhost"
)

$ErrorActionPreference = "Stop"

$AppName = "GVAdictos"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$AppPath = Join-Path $ProjectRoot "app.py"
$Url = "http://$HostName`:$Port"

function Test-AppHttp {
    param([string]$TargetUrl)

    try {
        Invoke-WebRequest -Uri $TargetUrl -UseBasicParsing -TimeoutSec 2 | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Resolve-Python {
    $candidates = @(
        (Join-Path $ProjectRoot ".venv\Scripts\python.exe"),
        (Join-Path $ProjectRoot "venv\Scripts\python.exe"),
        "python"
    )

    foreach ($candidate in $candidates) {
        if ($candidate -eq "python") {
            try {
                & python --version *> $null
                if ($LASTEXITCODE -eq 0) {
                    return "python"
                }
            }
            catch {
                continue
            }
        }
        elseif (Test-Path $candidate) {
            return $candidate
        }
    }

    throw "No se encontro Python. Instala Python o crea un entorno virtual en .venv."
}

if (-not (Test-Path $AppPath)) {
    throw "No se encontro app.py en $ProjectRoot"
}

if (Test-AppHttp -TargetUrl $Url) {
    Write-Host "$AppName ya esta respondiendo en $Url"
    Start-Process $Url
    return
}

$Python = Resolve-Python

Write-Host "Abriendo $AppName..."
Write-Host "Proyecto: $ProjectRoot"
Write-Host "URL: $Url"

Set-Location $ProjectRoot
& $Python -m streamlit run $AppPath --server.port $Port --server.address $HostName --browser.gatherUsageStats false
