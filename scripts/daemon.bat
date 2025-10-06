@echo off
REM Simple daemon management for Windows
REM Usage: daemon.bat [start|stop|status|logs|install|uninstall]

if "%1"=="" goto status
if "%1"=="start" goto start
if "%1"=="stop" goto stop
if "%1"=="status" goto status
if "%1"=="logs" goto logs
if "%1"=="install" goto install
if "%1"=="uninstall" goto uninstall
goto help

:start
echo Starting Image Transfer Daemon...
schtasks /run /tn ImageTransferDaemon
goto end

:stop
echo Stopping Image Transfer Daemon...
schtasks /end /tn ImageTransferDaemon
goto end

:status
echo Image Transfer Daemon Status:
schtasks /query /tn ImageTransferDaemon 2>NUL
if errorlevel 1 (
    echo Daemon is NOT installed
    echo Run: daemon.bat install
)
goto end

:logs
echo Recent log entries:
powershell -Command "Get-Content $env:USERPROFILE\logs\image_transfer.log -Tail 30"
goto end

:install
echo Installing daemon (no admin needed)...
image-transfer-service --install
goto end

:uninstall
echo Uninstalling daemon...
image-transfer-service --uninstall
goto end

:help
echo Usage: daemon.bat [command]
echo.
echo Commands:
echo   start     - Start the daemon
echo   stop      - Stop the daemon  
echo   status    - Check if daemon is running
echo   logs      - Show recent log entries
echo   install   - Install the daemon (no admin needed)
echo   uninstall - Remove the daemon
echo.
echo If no command given, shows status

:end