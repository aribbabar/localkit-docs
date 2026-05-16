param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173,
    [int]$BackendStartupTimeoutSeconds = 45,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$Processes = @()
$EventSubscriptions = @()

function Resolve-CmdCommand {
    param(
        [string]$Name,
        [string]$InstallHint
    )

    foreach ($candidate in @("$Name.cmd", "$Name.bat", "$Name.exe", $Name)) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($command) {
            return $command.Source
        }
    }

    throw "Required command '$Name' was not found. $InstallHint"
}

function Invoke-Checked {
    param(
        [string]$Name,
        [string]$WorkingDirectory,
        [string]$Command
    )

    Write-Host "[$Name] $Command"
    Push-Location $WorkingDirectory
    try {
        cmd.exe /d /s /c $Command
        if ($LASTEXITCODE -ne 0) {
            throw "'$Command' failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
}

function Start-ManagedProcess {
    param(
        [string]$Name,
        [string]$WorkingDirectory,
        [string]$Command,
        [hashtable]$Environment = @{}
    )

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo.FileName = "cmd.exe"
    $process.StartInfo.Arguments = "/d /s /c `"$Command`""
    $process.StartInfo.WorkingDirectory = $WorkingDirectory
    $process.StartInfo.UseShellExecute = $false
    $process.StartInfo.RedirectStandardOutput = $true
    $process.StartInfo.RedirectStandardError = $true
    $process.StartInfo.CreateNoWindow = $true

    foreach ($key in $Environment.Keys) {
        $process.StartInfo.EnvironmentVariables[$key] = [string]$Environment[$key]
    }

    $null = $process.Start()

    $script:EventSubscriptions += Register-ObjectEvent `
        -InputObject $process `
        -EventName OutputDataReceived `
        -MessageData $Name `
        -Action {
            if ($EventArgs.Data) {
                Write-Host "[$($Event.MessageData)] $($EventArgs.Data)"
            }
        }

    $script:EventSubscriptions += Register-ObjectEvent `
        -InputObject $process `
        -EventName ErrorDataReceived `
        -MessageData $Name `
        -Action {
            if ($EventArgs.Data) {
                Write-Host "[$($Event.MessageData)] $($EventArgs.Data)" -ForegroundColor Red
            }
        }

    $process.BeginOutputReadLine()
    $process.BeginErrorReadLine()

    Write-Host "[$Name] started (pid $($process.Id))"
    return $process
}

function Wait-HttpOk {
    param(
        [string]$Name,
        [string]$Url,
        [System.Diagnostics.Process]$Process,
        [int]$TimeoutSeconds
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if ($Process.HasExited) {
            throw "$Name exited before it was ready with code $($Process.ExitCode)."
        }

        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300) {
                Write-Host "[$Name] ready"
                return
            }
        }
        catch {
            Start-Sleep -Milliseconds 500
        }
    }

    throw "$Name did not become ready at $Url within $TimeoutSeconds seconds."
}

function Get-PortOwnerDescription {
    param(
        [string]$HostAddress,
        [int]$Port
    )

    $blockedAddresses = @($HostAddress, "0.0.0.0", "::", "::1")
    $connection = Get-NetTCPConnection `
        -LocalPort $Port `
        -State Listen `
        -ErrorAction SilentlyContinue |
        Where-Object { $blockedAddresses -contains $_.LocalAddress } |
        Select-Object -First 1

    if (-not $connection) {
        return $null
    }

    $process = Get-Process -Id $connection.OwningProcess -ErrorAction SilentlyContinue
    if ($process) {
        return "pid $($process.Id) ($($process.ProcessName))"
    }

    return "pid $($connection.OwningProcess)"
}

function Assert-PortAvailable {
    param(
        [string]$Name,
        [string]$HostAddress,
        [int]$Port
    )

    $owner = Get-PortOwnerDescription $HostAddress $Port
    if ($owner) {
        throw "$Name port $HostAddress`:$Port is already in use by $owner. Stop that process or pass a different -$($Name)Port value."
    }
}

function Stop-ManagedProcesses {
    foreach ($process in $Processes) {
        if ($process -and -not $process.HasExited) {
            Write-Host "Stopping process tree pid $($process.Id)..."
            taskkill.exe /PID $process.Id /T /F | Out-Null
        }
    }

    foreach ($subscription in $EventSubscriptions) {
        Unregister-Event -SubscriptionId $subscription.Id -ErrorAction SilentlyContinue
    }
}

$uvPath = Resolve-CmdCommand "uv" "Install uv from https://docs.astral.sh/uv/getting-started/installation/."
$npmPath = Resolve-CmdCommand "npm" "Install Node.js from https://nodejs.org/."

if (-not $SkipInstall) {
    Invoke-Checked "backend" $BackendDir "`"$uvPath`" sync"
}

if (-not $SkipInstall -and -not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
    Invoke-Checked "frontend" $FrontendDir "`"$npmPath`" install"
}

Assert-PortAvailable "Backend" "127.0.0.1" $BackendPort
Assert-PortAvailable "Frontend" "127.0.0.1" $FrontendPort

$backendCommand = "`"$uvPath`" run fastapi run main.py --host 127.0.0.1 --port $BackendPort"
$frontendCommand = "`"$npmPath`" run dev -- --host 127.0.0.1 --port $FrontendPort --strictPort"

Write-Host "Starting LocalKit Docs..."
Write-Host "Backend:  http://127.0.0.1:$BackendPort"
Write-Host "Frontend: http://127.0.0.1:$FrontendPort"
Write-Host "Press Ctrl+C to stop both processes."

try {
    $backendProcess = Start-ManagedProcess "backend" $BackendDir $backendCommand
    $Processes += $backendProcess
    Wait-HttpOk "backend" "http://127.0.0.1:$BackendPort/health" $backendProcess $BackendStartupTimeoutSeconds

    $Processes += Start-ManagedProcess "frontend" $FrontendDir $frontendCommand @{
        VITE_LOCALKIT_API_URL = "http://127.0.0.1:$BackendPort"
    }

    while ($true) {
        foreach ($process in $Processes) {
            if ($process.HasExited) {
                throw "Process pid $($process.Id) exited with code $($process.ExitCode)."
            }
        }

        Start-Sleep -Milliseconds 500
    }
}
finally {
    Stop-ManagedProcesses
}
