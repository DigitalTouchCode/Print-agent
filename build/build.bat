@echo off
REM Run this from the project root: build\build.bat
REM Produces dist\DT Print Agent.exe

cd /d "%~dp0\.."

if not exist venv (
    py -3 -m venv venv
)
call venv\Scripts\activate.bat

pip install --upgrade pip
pip install -r requirements.txt

pyinstaller --noconfirm --clean build\dt_print_agent.spec

echo.
echo Build finished: dist\DT Print Agent.exe
echo Next: run build\installer.iss with Inno Setup to produce a proper Setup.exe
pause
