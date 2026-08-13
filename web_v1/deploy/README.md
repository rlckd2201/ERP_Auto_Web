# WEB v1.0 Operating Server Deploy

## 배포 전 필수 자산 점검

설치 전에 아래 검사를 실행합니다. 하나라도 누락되면 설치를 진행하지 말고
배포 ZIP을 다시 생성해야 합니다. 이 통합 브랜치의 커밋된 `VERSION`은
`1.0.164`입니다. 다른 버전을 배포하려면 해당 버전의 전체 소스와 Agent 변경이
같은 릴리스에 포함됐는지 먼저 확인합니다.

```powershell
$Root = "C:\Users\Administrator\Desktop\전표 자동화 프로그램_WEB_Version"
$Required = @(
  "$Root\web_v1\frontend\index.html",
  "$Root\web_v1\frontend\app.js",
  "$Root\web_v1\frontend\styles.css",
  "$Root\web_v1\frontend\admin_db.html",
  "$Root\web_v1\frontend\admin_db.js",
  "$Root\web_v1\frontend\admin_db.css",
  "$Root\web_v1\frontend\sw.js",
  "$Root\web_v1\backend\tools\AccountingWebRequiredSetup.exe",
  "$Root\web_v1\backend\zoom_billing.py",
  "$Root\web_v1\VERSION"
)
$Missing = $Required | Where-Object { -not (Test-Path -LiteralPath $_) }
if ($Missing) { throw "배포 필수 자산 누락: $($Missing -join ', ')" }
$Version = (Get-Content -LiteralPath "$Root\web_v1\VERSION" -Raw).Trim()
if (-not $Version) { throw "VERSION 값이 비어 있습니다." }
Write-Host "배포 필수 자산 점검 통과: WEB $Version"
```

운영서버에서는 아래 폴더를 WEB v1.0 작업 루트로 사용한다.

```text
C:\Users\Administrator\Desktop\전표 자동화 프로그램_WEB_Version
```

## 0. 프로젝트 ZIP 풀기

운영서버에 `accounting_web_v1_deploy.zip`을 복사한 뒤 아래 명령으로 푼다.

```powershell
$Root = "C:\Users\Administrator\Desktop\전표 자동화 프로그램_WEB_Version"
New-Item -ItemType Directory -Force -Path $Root | Out-Null
Expand-Archive -Path C:\Users\Administrator\Downloads\accounting_web_v1_deploy.zip -DestinationPath $Root -Force
```

압축을 풀면 아래 파일이 존재해야 한다.

```powershell
Test-Path "C:\Users\Administrator\Desktop\전표 자동화 프로그램_WEB_Version\web_v1\deploy\install_operating_server.ps1"
```

결과가 `True`여야 한다.

## 1. 설치

운영서버에서 실행:

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\Administrator\Desktop\전표 자동화 프로그램_WEB_Version\web_v1\deploy\install_operating_server.ps1"
```

설치 스크립트는 다음을 수행한다.

- `C:\ERP_DB`, `C:\ERP_DB\downloads`, `C:\ERP_DB\chrome_profile` 생성
- WEB v1.0 백엔드 Python 패키지 설치
- Playwright Chromium 설치
- `web_v1\backend\.env` 생성

## 2. 실행

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\Administrator\Desktop\전표 자동화 프로그램_WEB_Version\web_v1\deploy\start_operating_server.ps1"
```

## 3. 점검

서버 실행 후 다른 PowerShell에서:

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\Administrator\Desktop\전표 자동화 프로그램_WEB_Version\web_v1\deploy\check_operating_server.ps1"
```

브라우저에서는 아래 주소로 접속한다.

```text
https://172.17.39.121:8080
```

서버가 다른 PC에서 접속될 예정이면 운영서버 IP로 접속한다.

```text
https://운영서버IP:8080
```

## 참고

- 실제 운영 접속 주소가 정해지면 `.env`의 `WEB_PUBLIC_ORIGIN`을 HTTPS 주소로 바꾼다.
- 브라우저 완료 알림은 사용자 브라우저에서 최초 1회 알림 허용이 필요하다.
- 설치 스크립트가 `https://172.17.39.121:8080`용 자체서명 인증서를 만들고 현재 Windows 사용자 신뢰 저장소에 등록한다.
- 다른 사용자 PC에서 접속할 때는 `C:\ERP_DB\certs\web_v1.cert.pem` 인증서를 해당 PC의 현재 사용자 신뢰 저장소에 등록해야 한다.
