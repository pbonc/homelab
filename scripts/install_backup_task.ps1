[CmdletBinding()]
param(
    [string]$TaskName = "Homelab Daily Backup",
    [string]$Distribution = "Ubuntu",
    [string]$Schedule = "03:00"
)

$ErrorActionPreference = "Stop"

try {
    $runAt = [datetime]::ParseExact(
        $Schedule,
        "HH:mm",
        [Globalization.CultureInfo]::InvariantCulture
    )
}
catch {
    throw "Schedule must use 24-hour HH:mm format, for example 03:00."
}

$linuxCommand = @(
    "cd /mnt/c/dev/homelab"
    "mkdir -p ~/.local/state/homelab-backup"
    "make backup-run >> ~/.local/state/homelab-backup/backup.log 2>&1"
) -join " && "

$action = New-ScheduledTaskAction `
    -Execute "$env:SystemRoot\System32\wsl.exe" `
    -Argument "-d $Distribution -- bash -lc `"$linuxCommand`""
$trigger = New-ScheduledTaskTrigger -Daily -At $runAt
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal `
    -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Create and verify the encrypted off-host homelab backup." `
    -Force | Out-Null

Write-Host "[PASS] Registered '$TaskName' daily at $Schedule."
Write-Host "The Windows user must be signed in; missed runs start when available."
