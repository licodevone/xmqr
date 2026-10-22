@echo off
setlocal
echo XMQR - diagnostico da instalacao
echo Execute este arquivo com o botao direito, Executar como administrador.
echo Este procedimento apenas le status, permissoes e existencia de arquivos.
echo Senhas e chaves privadas nao sao exibidas. Servicos nao sao alterados.
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -File "%~dp0collect_windows_installed_diagnostics.ps1"
set "XMQR_DIAG_EXIT=%ERRORLEVEL%"
echo.
if "%XMQR_DIAG_EXIT%"=="0" (
    echo Relatorio: %~dp0..\target\p244-diagnostic\installed-diagnostics.json
) else (
    echo Diagnostico nao concluido. Confira a mensagem acima.
)
pause
exit /b %XMQR_DIAG_EXIT%
