@echo off
set "PYTHON_ROOT=D:\git\Portable Python-3.10.5 x64\App\Python"
set "PYTHON_EXE=%PYTHON_ROOT%\python.exe"
set "SCRIPTS_DIR=%PYTHON_ROOT%\Scripts"

if not exist "%PYTHON_EXE%" (
  echo Portable Python not found: %PYTHON_EXE%
  exit /b 1
)

set "PATH=%PYTHON_ROOT%;%SCRIPTS_DIR%;%PATH%"
set "PYTHONUTF8=1"

echo Portable Python environment loaded.
echo python: %PYTHON_EXE%
echo scripts: %SCRIPTS_DIR%
