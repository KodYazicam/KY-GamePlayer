@echo off
rem Optional one-file EXE (roadmap 1.1): dist\KodYazar-onefile.exe.
rem Single file, no _internal folder. Slower start than build.bat's onedir.
setlocal
cd /d "%~dp0..\.."
python -m PyInstaller packaging\windows\KodYazar-onefile.spec --noconfirm --clean
if errorlevel 1 (
  echo build failed & exit /b 1
)
echo.
echo built: dist\KodYazar-onefile.exe
endlocal
