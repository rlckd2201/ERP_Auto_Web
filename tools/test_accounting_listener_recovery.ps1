$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'accounting_listener_recovery.ps1')

function Reset-Fixture {
    $script:record = [pscustomobject]@{ processId = 123; createdAtUtc = 'pinned' }
    $script:guards = @([pscustomobject]@{ ProcessId = 123 })
    $script:ports = @()
    $script:pinned = $true
    $script:stopped = @()
    $script:lookups = 0
    $script:changeOnSecondLookup = $false
    $script:recordMissing = $false
}
function S-GuardProcesses { return $script:guards }
function S-ReadRecord { if ($script:recordMissing) { throw 'MISSING_RECORD' }; return $script:record }
function S-Listeners { return $script:ports }
function S-Process($ProcessId) {
    $script:lookups++
    if ($script:stopped -contains $ProcessId) { return $null }
    if ($script:changeOnSecondLookup -and $script:lookups -ge 2) { $script:pinned = $false }
    return [pscustomobject]@{ ProcessId = $ProcessId }
}
function S-Pinned($Process, $Record) { return $script:pinned -and $Process.ProcessId -eq $Record.processId }
function S-Log([string]$Text) {}
function Stop-Process { param($Id, [switch]$Force, $ErrorAction); $script:stopped += $Id }
function Assert-Rejected([string]$Expected) {
    $message = ''
    try { S-RecoverStoppedListener } catch { $message = $_.Exception.Message }
    if ($message -ne $Expected) { throw "Expected $Expected, got $message" }
    if ($script:stopped.Count) { throw 'An unverified process was stopped' }
}

Reset-Fixture
S-RecoverStoppedListener
if ($script:stopped.Count -ne 1 -or $script:stopped[0] -ne 123) { throw 'Pinned orphan was not recovered' }
Reset-Fixture
$script:guards = @()
S-RecoverStoppedListener
if ($script:stopped.Count) { throw 'Empty runtime stopped a process' }
Reset-Fixture
$script:guards += [pscustomobject]@{ ProcessId = 456 }
Assert-Rejected 'MULTIPLE_GUARD_PROCESSES'
Reset-Fixture
$script:pinned = $false
Assert-Rejected 'ORPHAN_RUNTIME_IDENTITY_DIFFERS'
Reset-Fixture
$script:record.processId = 456
Assert-Rejected 'ORPHAN_RUNTIME_IDENTITY_DIFFERS'
Reset-Fixture
$script:recordMissing = $true
Assert-Rejected 'MISSING_RECORD'
Reset-Fixture
$script:ports = @([pscustomobject]@{ OwningProcess = 123 })
Assert-Rejected 'LISTENER_APPEARED_DURING_RECOVERY'
Reset-Fixture
$script:changeOnSecondLookup = $true
Assert-Rejected 'ORPHAN_RUNTIME_IDENTITY_CHANGED'
Write-Output 'PASS: 8 recovery checks; no real process was stopped.'
