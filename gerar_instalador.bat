@echo off
setlocal
cd /d "%~dp0"
title Criando o instalador do Baixador de Videos

echo ============================================================
echo   Criando o instalador do Baixador de Videos
echo   (leva alguns minutos; precisa de internet)
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 goto :sempython

echo [1/5] Instalando as bibliotecas...
python -m pip install -U -r requirements.txt
if errorlevel 1 goto :erro

echo.
echo [2/5] Criando o icone e as imagens do instalador...
python arte.py
if errorlevel 1 goto :erro

echo.
echo [3/5] Gerando o programa (pasta dist)...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
python -m PyInstaller --noconfirm --clean --noconsole --onedir --name BaixadorDeVideos --collect-all yt_dlp --collect-all yt_dlp_ejs --collect-all customtkinter --collect-all imageio_ffmpeg --collect-all pystray --icon icone.ico app.py
if errorlevel 1 goto :erro

echo.
echo [4/5] Incluindo o Deno no instalador (exigido pelo YouTube)...
if exist "componentes\deno.exe" goto :copiadeno
if not exist componentes mkdir componentes
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip' -OutFile 'componentes\deno.zip'; Expand-Archive -Path 'componentes\deno.zip' -DestinationPath 'componentes' -Force; Remove-Item 'componentes\deno.zip' } catch { Write-Host 'Nao foi possivel baixar o Deno agora. Sem problema: o programa baixa sozinho no primeiro uso.' }"
:copiadeno
if exist "componentes\deno.exe" copy /y "componentes\deno.exe" "dist\BaixadorDeVideos\" >nul

echo.
echo [5/5] Montando o instalador (Inno Setup)...
call :acharinno
if defined ISCC goto :compilar
echo Inno Setup nao encontrado. Tentando instalar pelo winget...
winget install --id JRSoftware.InnoSetup -e --silent --accept-package-agreements --accept-source-agreements
call :acharinno
if defined ISCC goto :compilar
echo.
echo Nao consegui instalar o Inno Setup automaticamente.
echo Baixe e instale em https://jrsoftware.org/isdl.php e rode este arquivo de novo.
goto :fim

:compilar
"%ISCC%" installer.iss
if errorlevel 1 goto :erro
echo.
echo ============================================================
echo   PRONTO! O instalador esta em:
echo   %~dp0installer_output\BaixadorDeVideos_Setup.exe
echo   Copie esse unico arquivo para qualquer computador com Windows.
echo ============================================================
explorer "%~dp0installer_output"
goto :fim

:acharinno
set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
exit /b 0

:sempython
echo Python nao encontrado. Instale em python.org (marque "Add Python to PATH") e rode de novo.
goto :fim

:erro
echo.
echo Ocorreu um erro. Veja a mensagem acima.

:fim
echo.
pause
endlocal
