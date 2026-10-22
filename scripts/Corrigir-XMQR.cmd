@echo off
setlocal
echo XMQR - criar atalhos e diagnosticar a instalacao existente
echo Execute com o botao direito, Executar como administrador.
echo Cria apenas atalhos de softwares instalados e preserva atalhos existentes.
echo Depois coleta status e metadados, sem exibir senhas ou chaves.
echo Os servicos, configuracoes e permissoes nao sao alterados.
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -File "%~dp0create_installed_windows_shortcuts.ps1"
if errorlevel 1 echo Nao foi possivel concluir os atalhos. Confira a mensagem acima.
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
