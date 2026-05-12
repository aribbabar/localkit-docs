param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173,
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

$npmPath = Resolve-CmdCommand "npm" "Install Node.js from https://nodejs.org/."
$backendEnvironment = @{}
$backendVenvScripts = Join-Path $BackendDir ".venv\Scripts"

if (Test-Path (Join-Path $backendVenvScripts "fastapi.exe")) {
    $backendEnvironment["Path"] = "$backendVenvScripts;$env:Path"
}
else {
    $null = Resolve-CmdCommand "fastapi" "Install the FastAPI CLI in your backend environment."
}

if (-not $SkipInstall -and -not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
    Invoke-Checked "frontend" $FrontendDir "`"$npmPath`" install"
}

$backendCommand = "fastapi dev main.py --host 127.0.0.1 --port $BackendPort"
$frontendCommand = "`"$npmPath`" run dev -- --host 127.0.0.1 --port $FrontendPort"

Write-Host "Starting LocalKit Docs..."
Write-Host "Backend:  http://127.0.0.1:$BackendPort"
Write-Host "Frontend: http://127.0.0.1:$FrontendPort"
Write-Host "Press Ctrl+C to stop both processes."

try {
    $Processes += Start-ManagedProcess "backend" $BackendDir $backendCommand $backendEnvironment
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
