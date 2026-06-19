[CmdletBinding()]
param(
    [string]$ShortcutName = "GVAdictos.lnk"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$LaunchCmd = Join-Path $ProjectRoot "scripts\launch_gvadictos.cmd"
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop $ShortcutName

function Resolve-GVAdictosIcon {
    $repoCandidates = @(
        (Join-Path $ProjectRoot "assets\icons\gvadictos.ico"),
        (Join-Path $ProjectRoot "assets\logo\gvadictos.ico"),
        (Join-Path $ProjectRoot "assets\icons\favicon.ico")
    )

    foreach ($candidate in $repoCandidates) {
        if (Test-Path $candidate) {
            return (Resolve-Path $candidate).Path
        }
    }

    $downloads = Join-Path $env:USERPROFILE "Downloads"
    $downloadRoots = @(
        (Join-Path $downloads "assets"),
        (Join-Path $downloads "logo"),
        (Join-Path $downloads "assets\logo"),
        (Join-Path $downloads "assets\icons")
    )

    foreach ($root in $downloadRoots) {
        if (-not (Test-Path $root)) {
            continue
        }

        $match = Get-ChildItem -Path $root -Recurse -File -Filter "*.ico" -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match "gvadictos|gvadicto|logo|icon|favicon" } |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1

        if ($match) {
            return $match.FullName
        }
    }

    return $null
}

if (-not (Test-Path $LaunchCmd)) {
    throw "No se encontro el launcher: $LaunchCmd"
}

$IconPath = Resolve-GVAdictosIcon

$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $LaunchCmd
$Shortcut.WorkingDirectory = $ProjectRoot
$Shortcut.Description = "Abrir GVAdictos"

if ($IconPath) {
    $Shortcut.IconLocation = "$IconPath,0"
}

$Shortcut.Save()

Write-Host "Acceso directo creado o actualizado:"
Write-Host $ShortcutPath
if ($IconPath) {
    Write-Host "Icono:"
    Write-Host $IconPath
}
else {
    Write-Host "No se encontro icono oficial .ico. El acceso directo usa el icono por defecto."
    Write-Host "Ruta recomendada para anadirlo despues: assets\icons\gvadictos.ico"
}
