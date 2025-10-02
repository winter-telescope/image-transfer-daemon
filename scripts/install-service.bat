@echo off
REM Windows batch file to install the service

echo Installing Image Transfer Daemon Service...
python "%~dp0install-service.py" --install %*

if %ERRORLEVEL% == 0 (
    echo.
    echo Service installed successfully!
    echo.
    echo Use these commands to manage the service:
    echo   Start:   net start ImageTransferDaemon
    echo   Stop:    net stop ImageTransferDaemon
    echo   Status:  sc query ImageTransferDaemon
) else (
    echo.
    echo Failed to install service. Make sure you're running as Administrator.
)