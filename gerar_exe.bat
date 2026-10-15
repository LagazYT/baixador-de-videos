@echo off
cd /d "%~dp0"
python -m pip install -U -r requirements.txt
python arte.py
python -m PyInstaller --noconsole --onefile --name BaixadorDeVideos --collect-all yt_dlp --collect-all yt_dlp_ejs --collect-all customtkinter --collect-all imageio_ffmpeg --collect-all pystray --hidden-import mpv --collect-all py7zr --icon icone.ico app.py
echo.
echo Pronto! O programa esta em: dist\BaixadorDeVideos.exe
pause
