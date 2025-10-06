# Simple management script for the Image Transfer Daemon on Windows
# Usage: .\manage-daemon.ps1 [start|stop|status|logs]

param(
    [Parameter(Position=0)]
    [string]$Command = "status"
)

$TaskName = "ImageTransferDaemon"

switch ($Command.ToLower()) {
    "start" {
        Write-Host "Starting Image Transfer Daemon..." -ForegroundColor Green
        Start-ScheduledTask -TaskName $TaskName
        Start-Sleep -Seconds 2
        $State = (Get-ScheduledTask -TaskName $TaskName).State
        Write-Host "Status: $State"
    }
    
    "stop" {
        Write-Host "Stopping Image Transfer Daemon..." -ForegroundColor Yellow
        Stop-ScheduledTask -TaskName $TaskName
        Write-Host "Stopped"
    }
    
    "restart" {
        Write-Host "Restarting Image Transfer Daemon..." -ForegroundColor Yellow
        Stop-ScheduledTask -TaskName $TaskName
        Start-Sleep -Seconds 2
        Start-ScheduledTask -TaskName $TaskName
        Start-Sleep -Seconds 2
        $State = (Get-ScheduledTask -TaskName $TaskName).State
        Write-Host "Status: $State"
    }
    
    "status" {
        try {
            $Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
            $Info = Get-ScheduledTaskInfo -TaskName $TaskName
            
            Write-Host "`nImage Transfer Daemon Status" -ForegroundColor Cyan
            Write-Host "=============================" -ForegroundColor Cyan
            Write-Host "State: $($Task.State)"
            Write-Host "Last Run: $($Info.LastRunTime)"
            Write-Host "Next Run: $($Info.NextRunTime)"
            Write-Host "Last Result: $($Info.LastTaskResult)"
            
            if ($Task.State -eq "Running") {
                Write-Host "`n✓ Daemon is running" -ForegroundColor Green
            } else {
                Write-Host "`n✗ Daemon is not running" -ForegroundColor Yellow
                Write-Host "  Use '.\manage-daemon.ps1 start' to start it"
            }
        } catch {
            Write-Host "Daemon is not installed" -ForegroundColor Red
            Write-Host "Install with: image-transfer-service --install"
        }
    }
    
    "logs" {
        $LogFile = "$env:USERPROFILE\logs\image_transfer.log"
        if (Test-Path $LogFile) {
            Write-Host "Showing last 30 lines of log:" -ForegroundColor Cyan
            Get-Content $LogFile -Tail 30
            Write-Host "`nTo follow logs in real-time, use:" -ForegroundColor Yellow
            Write-Host "  Get-Content $LogFile -Wait"
        } else {
            Write-Host "No log file found at $LogFile" -ForegroundColor Red
        }
    }
    
    default {
        Write-Host "Usage: .\manage-daemon.ps1 [start|stop|restart|status|logs]" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Commands:"
        Write-Host "  start    - Start the daemon"
        Write-Host "  stop     - Stop the daemon"
        Write-Host "  restart  - Restart the daemon"
        Write-Host "  status   - Show daemon status"
        Write-Host "  logs     - Show recent log entries"
    }
}