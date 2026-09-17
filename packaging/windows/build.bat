@echo off
cd /d "%~dp0..\.."
python -m pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --clean packaging\windows\KodYazar.spec
echo dist\KodYazar\KodYazar.exe
