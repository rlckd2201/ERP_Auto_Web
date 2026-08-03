@echo off
REM Excel Voucher Web Server 실행 런처.
REM 시작프로그램(shell:startup)에는 이 파일의 바로가기를 넣는다.
REM .ps1 파일이나 그 바로가기를 넣으면 윈도우가 실행하지 않고 메모장으로 열어
REM 서버가 뜨지 않는다.
setlocal
cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_server.ps1" ^
  -Port 8081 ^
  -PublicOrigin https://172.17.39.121:8081 ^
  -DataServerUrl http://127.0.0.1:18080 ^
  -ForwardToDataServer ^
  -RequireLogin ^
  -GroupwareSyncOnStart ^
  -SslCertFile C:\ERP_DB\certs\web_v1.cert.pem ^
  -SslKeyFile C:\ERP_DB\certs\web_v1.key.pem

REM 서버가 멈추면 창이 바로 닫히지 않도록 오류 코드를 남긴다.
if errorlevel 1 (
  echo.
  echo [!] 서버가 종료되었습니다. 위 메시지를 확인하세요. 종료코드=%errorlevel%
  pause
)
endlocal
