# 운영서버 복붙 명령

운영서버 기준 폴더:

```text
C:\Users\Administrator\Desktop\전표 자동화 프로그램_WEB_Version
```

## 1. ZIP 풀기

`accounting_web_v1_deploy.zip`을 운영서버의 `C:\Users\Administrator\Downloads`에 복사한 뒤 실행:

```powershell
$Root = "C:\Users\Administrator\Desktop\전표 자동화 프로그램_WEB_Version"
New-Item -ItemType Directory -Force -Path $Root | Out-Null
Expand-Archive -Path C:\Users\Administrator\Downloads\accounting_web_v1_deploy.zip -DestinationPath $Root -Force
Test-Path "$Root\web_v1\deploy\install_operating_server.ps1"
```

마지막 결과가 `True`여야 한다.

## 2. 설치

```powershell
$Root = "C:\Users\Administrator\Desktop\전표 자동화 프로그램_WEB_Version"
powershell -ExecutionPolicy Bypass -File "$Root\web_v1\deploy\install_operating_server.ps1"
```

## 3. 실행

```powershell
$Root = "C:\Users\Administrator\Desktop\전표 자동화 프로그램_WEB_Version"
powershell -ExecutionPolicy Bypass -File "$Root\web_v1\deploy\start_operating_server.ps1"
```

브라우저 접속:

```text
https://172.17.39.121:8080
```

## 4. 점검

서버 실행 창을 켜둔 상태에서 새 PowerShell을 열고 실행:

```powershell
$Root = "C:\Users\Administrator\Desktop\전표 자동화 프로그램_WEB_Version"
powershell -ExecutionPolicy Bypass -File "$Root\web_v1\deploy\check_operating_server.ps1"
```

## 5. 인증서 등록

인증서 경고가 뜨면 운영서버 또는 접속 PC에서 실행:

```powershell
$Root = "C:\Users\Administrator\Desktop\전표 자동화 프로그램_WEB_Version"
powershell -ExecutionPolicy Bypass -File "$Root\web_v1\deploy\trust_https_cert_current_user.ps1"
```

실행 후 Chrome/Edge를 완전히 닫고 다시 연다.

## 6. 구매 메일 수집

웹 화면에서 `구매 메일 수집` 버튼을 누르면 운영서버가 Gmail 읽지 않은 메일을 1회 확인하고, 지원되는 세금계산서 링크/첨부를 크롤링해 `C:\ERP_DB\learned_data.db`에 저장한다.
