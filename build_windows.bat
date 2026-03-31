@echo off
cd /d %~dp0
py -3 -m pip install -r launcher\requirements.txt
py -3 launcher\scripts\generate_icons.py
py -3 -m PyInstaller --noconfirm --clean --windowed --icon launcher\assets\noobtrade.ico --name NoobTrade launcher\app.py
echo.
echo Windows build complete.
echo Open: dist\NoobTrade\NoobTrade.exe
