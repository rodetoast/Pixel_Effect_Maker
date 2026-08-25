@echo off
setlocal
cd /d "%~dp0"

if defined PIXEL_EFFECT_PYTHON (
    "%PIXEL_EFFECT_PYTHON%" --version >nul 2>&1 && goto run_override
)

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" --version >nul 2>&1 && goto run_venv
)

where py >nul 2>&1 && py -3 --version >nul 2>&1 && goto run_py
where python >nul 2>&1 && python --version >nul 2>&1 && goto run_python

echo [ERROR] No usable Python interpreter was found.
echo Repair .venv, install Python with the py launcher, or set PIXEL_EFFECT_PYTHON.
exit /b 1

:run_override
"%PIXEL_EFFECT_PYTHON%" -m app.main %*
goto result

:run_venv
".venv\Scripts\python.exe" -m app.main %*
goto result

:run_py
py -3 -m app.main %*
goto result

:run_python
python -m app.main %*

:result
set "APP_EXIT=%ERRORLEVEL%"
if not "%APP_EXIT%"=="0" (
    echo.
    echo [ERROR] Pixel Effect Maker exited with code %APP_EXIT%.
)
exit /b %APP_EXIT%
