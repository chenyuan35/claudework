Set-StrictMode -Version Latest

function Set-MemoryBusUtf8 {
    $utf8 = [Text.UTF8Encoding]::new($false)
    [Console]::InputEncoding = $utf8
    [Console]::OutputEncoding = $utf8
    $global:OutputEncoding = $utf8
}

function Get-ClaudeworkWorkspaceRoot {
    if (-not [string]::IsNullOrWhiteSpace($env:CLAUDEWORK_MEMORY_BUS_WORKSPACE)) {
        $configured = [IO.Path]::GetFullPath($env:CLAUDEWORK_MEMORY_BUS_WORKSPACE)
        if (Test-Path -LiteralPath $configured -PathType Container) {
            return $configured
        }
    }
    return [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
}

function Get-MemoryBusExecutable {
    param(
        [Parameter(Mandatory = $true)]
        [string]$WorkspaceRoot
    )

    if (-not [string]::IsNullOrWhiteSpace($env:CLAUDEWORK_MEMORY_BUS_EXE)) {
        $configured = [IO.Path]::GetFullPath($env:CLAUDEWORK_MEMORY_BUS_EXE)
        if (Test-Path -LiteralPath $configured -PathType Leaf) {
            return $configured
        }
    }

    $candidates = @(
        (Join-Path $WorkspaceRoot 'cc-switch\src-tauri\target\release\memory_bus.exe'),
        (Join-Path $WorkspaceRoot 'cc-switch\src-tauri\target\debug\memory_bus.exe'),
        (Join-Path $WorkspaceRoot 'cc-switch\src-tauri\target\release\memory-bus.exe'),
        (Join-Path $WorkspaceRoot 'cc-switch\src-tauri\target\debug\memory-bus.exe')
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return $candidate
        }
    }
    return $null
}

function Test-MemoryBusWorkspacePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$WorkspaceRoot,
        [string]$CurrentDirectory
    )

    if ([string]::IsNullOrWhiteSpace($CurrentDirectory)) {
        return $false
    }
    try {
        $workspace = [IO.Path]::GetFullPath($WorkspaceRoot)
        $current = [IO.Path]::GetFullPath($CurrentDirectory)
        $prefix = $workspace.TrimEnd([char[]]@([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)) + [IO.Path]::DirectorySeparatorChar
        return $current.Equals($workspace, [StringComparison]::OrdinalIgnoreCase) -or
            $current.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)
    }
    catch {
        return $false
    }
}

function Get-MemoryBusContext {
    param(
        [Parameter(Mandatory = $true)]
        [string]$WorkspaceRoot,
        [Parameter(Mandatory = $true)]
        [ValidateSet('claude', 'codex', 'hermes_memory', 'hermes_user')]
        [string]$Consumer,
        [ValidateRange(256, 16000)]
        [int]$MaxChars = 6000
    )

    $memoryBus = Get-MemoryBusExecutable -WorkspaceRoot $WorkspaceRoot
    if ($null -eq $memoryBus) {
        return [pscustomobject]@{
            success = $false
            code = 'memory_bus_missing'
            context = $null
            executable = $null
        }
    }

    # A missing ledger is an expected read-only state before activation. Avoid
    # PowerShell turning the native non-zero exit into a terminating exception
    # (which would otherwise leak provider stderr through a hook host).
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $output = & $memoryBus context --workspace $WorkspaceRoot --consumer $Consumer --max-chars $MaxChars 2>$null
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    if ($LASTEXITCODE -ne 0) {
        return [pscustomobject]@{
            success = $false
            code = 'memory_bus_unavailable'
            context = $null
            executable = $memoryBus
        }
    }
    $context = ($output -join [Environment]::NewLine).Trim()
    if (-not $context.StartsWith('# Memory Bus context', [StringComparison]::Ordinal)) {
        return [pscustomobject]@{
            success = $false
            code = 'memory_bus_invalid_context'
            context = $null
            executable = $memoryBus
        }
    }
    return [pscustomobject]@{
        success = $true
        code = 'ok'
        context = $context
        executable = $memoryBus
    }
}

Export-ModuleMember -Function @(
    'Set-MemoryBusUtf8',
    'Get-ClaudeworkWorkspaceRoot',
    'Get-MemoryBusExecutable',
    'Test-MemoryBusWorkspacePath',
    'Get-MemoryBusContext'
)
