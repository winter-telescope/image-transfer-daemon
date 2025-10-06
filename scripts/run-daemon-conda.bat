@echo off
REM Run the daemon with the correct conda environment
REM Place this in your Startup folder or run it manually

echo Starting Image Transfer Daemon with conda environment...

REM Activate your conda environment
REM Adjust the path to match your setup
call C:\Users\oir-user\Desktop\GIT\image-transfer-daemon\.conda\Scripts\activate.bat

REM Verify Python
echo Using Python: 
where python

REM Run the daemon
echo Starting daemon...
python -m image_transfer

REM If the daemon crashes, pause to see the error
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Daemon exited with error!
    pause
)