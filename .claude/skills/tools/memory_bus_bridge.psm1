Set-StrictMode -Version Latest

function Set-HermesMemoryUtf8 {
    $utf8 = [Text.UTF8Encoding]::new($false)
    [Console]::InputEncoding = $utf8
    [Console]::OutputEncoding = $utf8
    $global:OutputEncoding = $utf8
}

function Get-ClaudeworkWorkspaceRoot {
    if (-not [string]::IsNullOrWhiteSpace($env:CLAUDEWORK_HERMES_MEMORY_WORKSPACE)) {
        $configured = [IO.Path]::GetFullPath($env:CLAUDEWORK_HERMES_MEMORY_WORKSPACE)
        if (Test-Path -LiteralPath $configured -PathType Container) {
            return $configured
        }
    }
    return [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
}

function Get-HermesExternalMemoryPython {
    param(
        [Parameter(Mandatory = $true)]
        [string]$WorkspaceRoot
    )

    $candidates = @()
    if (-not [string]::IsNullOrWhiteSpace($env:CLAUDEWORK_HERMES_MEMORY_PYTHON)) {
        $candidates += [IO.Path]::GetFullPath($env:CLAUDEWORK_HERMES_MEMORY_PYTHON)
    }
    if (-not [string]::IsNullOrWhiteSpace($env:HERMES_AGENT_ROOT)) {
        $candidates += (Join-Path $env:HERMES_AGENT_ROOT 'venv\Scripts\python.exe')
    }
    if (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        $candidates += (Join-Path $env:LOCALAPPDATA 'hermes\hermes-agent\venv\Scripts\python.exe')
    }
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return [IO.Path]::GetFullPath($candidate)
        }
    }
    return $null
}

function Test-ClaudeworkWorkspacePath {
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

function Get-HermesExternalMemoryContext {
    param(
        [Parameter(Mandatory = $true)]
        [string]$WorkspaceRoot,
        [Parameter(Mandatory = $true)]
        [ValidateSet('claude', 'codex', 'hermes_memory', 'hermes_user')]
        [string]$Consumer,
        [ValidateRange(256, 16000)]
        [int]$MaxChars = 6000
    )

    $python = Get-HermesExternalMemoryPython -WorkspaceRoot $WorkspaceRoot
    $bridge = Join-Path $WorkspaceRoot '.claude\skills\tools\hermes_external_memory_bridge.py'
    if ($null -eq $python -or -not (Test-Path -LiteralPath $bridge -PathType Leaf)) {
        return [pscustomobject]@{
            success = $false
            code = 'hermes_external_memory_bridge_missing'
            context = $null
        }
    }

    $processInfo = [Diagnostics.ProcessStartInfo]::new()
    $processInfo.FileName = $python
    $processInfo.WorkingDirectory = $WorkspaceRoot
    $processInfo.UseShellExecute = $false
    $processInfo.CreateNoWindow = $true
    $processInfo.RedirectStandardOutput = $true
    $processInfo.RedirectStandardError = $true
    $arguments = @($bridge, '--workspace', $WorkspaceRoot, '--consumer', $Consumer, '--max-chars', "$MaxChars", '--timeout-seconds', '8')
    if ($null -ne $processInfo.PSObject.Properties['ArgumentList']) {
        foreach ($argument in $arguments) {
            [void]$processInfo.ArgumentList.Add($argument)
        }
    }
    else {
        $processInfo.Arguments = (($arguments | ForEach-Object { '"' + $_.Replace('"', '\"') + '"' }) -join ' ')
    }

    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $processInfo
    try {
        if (-not $process.Start()) {
            throw 'bridge process did not start'
        }
        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(10000)) {
            try { $process.Kill($true) } catch { $process.Kill() }
            $process.WaitForExit()
            return [pscustomobject]@{
                success = $false
                code = 'hermes_external_memory_timeout'
                context = $null
            }
        }
        $stdout = $stdoutTask.GetAwaiter().GetResult().Replace("`r`n", "`n").Trim()
        [void]$stderrTask.GetAwaiter().GetResult()
        if ($process.ExitCode -ne 0) {
            return [pscustomobject]@{
                success = $false
                code = 'hermes_external_memory_unavailable'
                context = $null
            }
        }
        if (-not $stdout.StartsWith('# Hermes external memory context', [StringComparison]::Ordinal)) {
            return [pscustomobject]@{
                success = $false
                code = 'hermes_external_memory_invalid_context'
                context = $null
            }
        }
        return [pscustomobject]@{
            success = $true
            code = 'ok'
            context = $stdout
        }
    }
    catch {
        return [pscustomobject]@{
            success = $false
            code = 'hermes_external_memory_bridge_failed'
            context = $null
        }
    }
    finally {
        $process.Dispose()
    }
}

Export-ModuleMember -Function @(
    'Set-HermesMemoryUtf8',
    'Get-ClaudeworkWorkspaceRoot',
    'Get-HermesExternalMemoryPython',
    'Test-ClaudeworkWorkspacePath',
    'Get-HermesExternalMemoryContext'
)
