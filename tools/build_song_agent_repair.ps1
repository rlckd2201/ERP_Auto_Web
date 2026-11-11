param(
    [Parameter(Mandatory=$true)][string]$CertificatePath,
    [Parameter(Mandatory=$true)][string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
$cert = [IO.Path]::GetFullPath($CertificatePath)
if ((Get-FileHash -LiteralPath $cert -Algorithm SHA256).Hash -ine '2978977502684f6822d9d046f194f7f9e978357457d3a87385d33cc66e1fb8fd') {
    throw 'Use the exact server105 public certificate verified for this recovery.'
}
$output = [IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $output -Force | Out-Null
$resources = Join-Path $output 'resources'
New-Item -ItemType Directory -Path $resources -Force | Out-Null
$utf8Bom = New-Object Text.UTF8Encoding($true)
[IO.File]::WriteAllText((Join-Path $resources 'repair.ps1'),[IO.File]::ReadAllText((Join-Path $PSScriptRoot 'song_agent_repair.ps1')),$utf8Bom)
[IO.File]::WriteAllText((Join-Path $resources 'repair-common.ps1'),[IO.File]::ReadAllText((Join-Path $PSScriptRoot 'hyeon_agent_repair.ps1')),$utf8Bom)
$resourceCert = Join-Path $resources 'server105-trust.pem'
if ($cert -ine $resourceCert) { Copy-Item -LiteralPath $cert -Destination $resourceCert -Force }
$compiler = Join-Path $env:SystemRoot 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$exe = Join-Path $output 'AccountingWebSongRepair.exe'
& $compiler /nologo /target:exe ("/out:$exe") ("/resource:" + (Join-Path $resources 'repair.ps1') + ',repair.ps1') ("/resource:" + (Join-Path $resources 'repair-common.ps1') + ',repair-common.ps1') ("/resource:$resourceCert,server105-trust.pem") (Join-Path $PSScriptRoot 'AccountingWebSongRepair.cs')
if ($LASTEXITCODE -ne 0) { throw 'Recovery executable compilation failed.' }
& $exe --self-test
if ($LASTEXITCODE -ne 0) { throw 'Recovery executable resource check failed.' }
Get-FileHash -LiteralPath $exe -Algorithm SHA256
