@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ============================================================
:: build_exe.bat — Shared Paste Dashboard 打包腳本
:: 所有路徑皆由 config.py 的 BUILD_ROOT 推算，或自動 fallback
:: ============================================================

set "PYTHON_EXE=py.exe"
set "PYTHON_VERSION=-3.13"
set "SRC_DIR=%~dp0..\"
set "APP_NAME=SharedPasteDashboard"

:: 取得 config.py 中的 BUILD_ROOT（讓 Python 計算）
for /f "delims=" %%I in ('%PYTHON_EXE% %PYTHON_VERSION% -c "import sys; sys.path.insert(0, r'%~dp0..'); from config import BUILD_ROOT; print(BUILD_ROOT)" 2^>nul') do set "BUILD_ROOT=%%I"
if not defined BUILD_ROOT (
    echo [WARN] 無法從 config.py 取得 BUILD_ROOT，fallback 至 SRC_DIR
    set "BUILD_ROOT=%SRC_DIR%"
)

set "PKG_SRC=%BUILD_ROOT%\_pkg_src"
set "OUT_DIR=%BUILD_ROOT%\dist"
set "BUILD_DIR=%BUILD_ROOT%\build"
set "SPEC_DIR=%BUILD_ROOT%\spec"
set "FINAL_DIR=%BUILD_ROOT%\%APP_NAME%"

echo.
echo ============================================================
echo  Shared Paste Dashboard Build Script
echo  SRC     : %SRC_DIR%
echo  OUTPUT  : %FINAL_DIR%
echo ============================================================
echo.

:: --- 取得 TCL 路徑 ---
for /f "delims=" %%I in ('%PYTHON_EXE% %PYTHON_VERSION% -c "import sys; from pathlib import Path; print(Path(sys.base_prefix) / 'tcl')"') do set "TCL_ROOT=%%I"

:: --- 終止舊執行檔 ---
echo === Kill old exe if running ===
taskkill /f /im %APP_NAME%.exe >nul 2>nul

:: --- 清除舊建置 ---
echo === Clean folders ===
if exist "%PKG_SRC%"  rmdir /s /q "%PKG_SRC%"
if exist "%OUT_DIR%"  rmdir /s /q "%OUT_DIR%"
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
if exist "%SPEC_DIR%"  rmdir /s /q "%SPEC_DIR%"
if exist "%FINAL_DIR%" rmdir /s /q "%FINAL_DIR%"

mkdir "%PKG_SRC%"
mkdir "%OUT_DIR%"
mkdir "%BUILD_DIR%"
mkdir "%SPEC_DIR%"

:: --- 複製源碼 ---
echo === Copy source files ===
copy "%SRC_DIR%main.py"         "%PKG_SRC%\main.py"         /Y
copy "%SRC_DIR%config.py"       "%PKG_SRC%\config.py"       /Y
copy "%SRC_DIR%sync_service.py" "%PKG_SRC%\sync_service.py" /Y
copy "%SRC_DIR%ui_dashboard.py" "%PKG_SRC%\ui_dashboard.py" /Y

cd /d "%PKG_SRC%"

:: --- 環境確認 ---
echo === Python Version ===
%PYTHON_EXE% %PYTHON_VERSION% --version

echo === Tkinter Test ===
%PYTHON_EXE% %PYTHON_VERSION% -c "import tkinter; print('tkinter ok')"
if errorlevel 1 (
    echo [ERROR] Tkinter test failed.
    pause
    exit /b 1
)

:: --- 安裝 PyInstaller ---
echo === Install / Check PyInstaller ===
%PYTHON_EXE% %PYTHON_VERSION% -m pip install --upgrade pyinstaller

:: --- 打包 ---
echo === Build EXE (onedir) ===
%PYTHON_EXE% %PYTHON_VERSION% -m PyInstaller ^
  --onedir ^
  --noconsole ^
  --clean ^
  --name %APP_NAME% ^
  --hidden-import tkinter ^
  --hidden-import _tkinter ^
  --add-data "%TCL_ROOT%\tcl8.6;tcl\tcl8.6" ^
  --add-data "%TCL_ROOT%\tk8.6;tcl\tk8.6" ^
  --distpath "%OUT_DIR%" ^
  --workpath "%BUILD_DIR%" ^
  --specpath "%SPEC_DIR%" ^
  main.py

if errorlevel 1 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

:: --- 複製至最終目錄 ---
echo === Copy to final folder ===
xcopy "%OUT_DIR%\%APP_NAME%" "%FINAL_DIR%\" /E /I /Y

echo.
echo ============================================================
echo  Build complete!
echo  Final folder : %FINAL_DIR%
echo  Executable   : %FINAL_DIR%\%APP_NAME%.exe
echo ============================================================
echo.
pause
