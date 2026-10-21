@echo off
setlocal
echo XMQR - instalacao dos componentes deste pacote
echo Extraia o ZIP inteiro antes de continuar.
echo Os assistentes pedirao permissao administrativa.
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -File "%~dp0install-windows.ps1"
set "XMQR_INSTALL_EXIT=%ERRORLEVEL%"
if not "%XMQR_INSTALL_EXIT%"=="0" (
    echo.
    echo A instalacao nao terminou com sucesso. Confira a mensagem acima.
    echo Se a politica local impedir scripts, abra os MSIs individualmente:
    echo primeiro XMQR Manager e depois os componentes desejados.
)
echo.
pause
exit /b %XMQR_INSTALL_EXIT%
