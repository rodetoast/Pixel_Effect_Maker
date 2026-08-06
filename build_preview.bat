@echo off
setlocal
cd /d "%~dp0"

where pyinstaller >nul 2>nul
if errorlevel 1 (
    echo [ERROR] PyInstaller was not found in the active build environment.
    echo Install requirements.txt and requirements-build.txt in a dedicated build environment.
    exit /b 1
)

pyinstaller --noconfirm --clean Pixel_Effect_Maker.spec
if errorlevel 1 exit /b 1

set "PREVIEW_DIST=dist\Pixel_Effect_Maker_v0.0.04_Early_Preview_20260806"
if not exist "%PREVIEW_DIST%\projects" mkdir "%PREVIEW_DIST%\projects"
if not exist "%PREVIEW_DIST%\exports" mkdir "%PREVIEW_DIST%\exports"
copy /y README_PREVIEW.txt "%PREVIEW_DIST%\README_PREVIEW.txt" >nul

echo [OK] %PREVIEW_DIST%
endlocal
