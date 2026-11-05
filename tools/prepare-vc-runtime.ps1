# Collect a personally installed official Microsoft VC++ x64 runtime for import
# into the local iPhone Wine guest. Never publish the output to GitHub.
[CmdletBinding()]
param(
    [string]$Destination = (Join-Path ([Environment]::GetFolderPath('Desktop')) 'vc-runtime-x64')
)
$ErrorActionPreference = 'Stop'
$source = Join-Path $env:WINDIR 'System32'
$required = @('vcruntime140.dll', 'msvcp140.dll')
$optional = @('vcruntime140_1.dll', 'msvcp140_1.dll', 'msvcp140_2.dll',
              'concrt140.dll', 'vcomp140.dll')
function Test-X64PE([string]$path) {
    $stream = [IO.File]::OpenRead($path)
    try {
        $reader = [IO.BinaryReader]::new($stream)
        if ($stream.Length -lt 0x40 -or $reader.ReadUInt16() -ne 0x5a4d) { return $false }
        $stream.Position = 0x3c
        $offset = $reader.ReadInt32()
        if ($offset -lt 0x40 -or $offset -gt $stream.Length - 6) { return $false }
        $stream.Position = $offset
        return ($reader.ReadUInt32() -eq 0x4550 -and $reader.ReadUInt16() -eq 0x8664)
    } finally {
        $stream.Dispose()
    }
}
foreach ($name in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $source $name))) {
        throw "Missing $name. Install the official x64 redistributable from https://aka.ms/vc14/vc_redist.x64.exe and retry."
    }
}
[IO.Directory]::CreateDirectory($Destination) | Out-Null
foreach ($name in ($required + $optional)) {
    $path = Join-Path $source $name
    if (-not (Test-Path -LiteralPath $path)) { continue }
    if (-not (Test-X64PE $path)) { throw "$name is not a 64-bit x64 PE binary" }
    $sig = Get-AuthenticodeSignature -LiteralPath $path
    if ($sig.Status -ne 'Valid' -or
        -not $sig.SignerCertificate -or
        $sig.SignerCertificate.Subject -notmatch 'Microsoft') {
        throw "$name did not pass Microsoft publisher signature verification"
    }
    Copy-Item -LiteralPath $path -Destination (Join-Path $Destination $name) -Force
    Write-Host "Validated and staged $name"
}
Write-Host "Personal runtime folder: $Destination"
Write-Host "Copy this directory into the app's Files/Documents location on the iPhone."
