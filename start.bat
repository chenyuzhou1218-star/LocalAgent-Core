@echo off
set "PYTHONW=%LocalAppData%\Programs\Python\Python312\pythonw.exe"
if exist "%PYTHONW%" (
    start "" /b "%PYTHONW%" "%~dp0launcher.py"
    exit /b 0
)
set "APP=%~dp0dist\本地 Agent\本地 Agent.exe"
if exist "%APP%" start "" "%APP%"
exit /b 0
