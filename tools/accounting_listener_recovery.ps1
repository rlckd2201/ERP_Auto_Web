# Included in the accounting runtime supervisor. No recovery runs on import.
# S-Pinned checks executable, exact command, PID and process creation time.
function S-RecoverStoppedListener {
    $guards = @(S-GuardProcesses)
    if ($guards.Count -eq 0) { return }
    if ($guards.Count -ne 1) { throw 'MULTIPLE_GUARD_PROCESSES' }
    $record = S-ReadRecord
    $current = S-Process $guards[0].ProcessId
    if (!$current -or !(S-Pinned $current $record)) {
        throw 'ORPHAN_RUNTIME_IDENTITY_DIFFERS'
    }
    # A listener that appeared during inspection may belong to a healthy runtime.
    if (@(S-Listeners).Count) { throw 'LISTENER_APPEARED_DURING_RECOVERY' }
    $current = S-Process $record.processId
    if (!$current -or !(S-Pinned $current $record)) {
        throw 'ORPHAN_RUNTIME_IDENTITY_CHANGED'
    }
    S-Log ('recovering pinned runtime without listener ' + $record.processId)
    Stop-Process -Id $record.processId -Force -ErrorAction Stop
    $deadline = [DateTime]::UtcNow.AddSeconds(10)
    while ($remaining = S-Process $record.processId) {
        if (!(S-Pinned $remaining $record)) { throw 'RECOVERY_PROCESS_ID_REUSED' }
        if ([DateTime]::UtcNow -ge $deadline) { throw 'ORPHAN_RUNTIME_STOP_TIMEOUT' }
        Start-Sleep -Milliseconds 100
    }
}
