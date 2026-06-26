# Excel Voucher Web

재정 담당자가 엑셀을 업로드하면 서버가 전표 payload를 만들고, 172.17.30.243 자동 전표처리 PC의 Agent가 작업을 가져가 ERP 전표 처리를 수행하는 신규 웹 기반 시스템이다.

## 실행
```powershell
cd excel_voucher_web
.\run_server.ps1 `
  -Port 8081 `
  -PublicOrigin https://172.17.39.121:8081 `
  -DataServerUrl http://127.0.0.1:18080 `
  -ForwardToDataServer `
  -RequireLogin `
  -GroupwareSyncOnStart `
  -SslCertFile C:\ERP_DB\certs\web_v1.cert.pem `
  -SslKeyFile C:\ERP_DB\certs\web_v1.key.pem
```

브라우저에서 `https://172.17.39.121:8081`을 연다. SSL 인증서를 붙일 때는 `-SslCertFile`, `-SslKeyFile`을 같이 넘긴다.

SSL 없이 내부 테스트만 할 때는 `-SslCertFile`, `-SslKeyFile`을 빼고 `http://172.17.39.121:8081`로 접속한다.

## Agent 실행 예시
```powershell
cd excel_voucher_web
.\run_agent.ps1 -Server https://172.17.39.121:8081 -ClientIp 172.17.30.243
```

운영에서는 `EXCEL_VOUCHER_TARGET_AGENT_IP=172.17.30.243`를 기본으로 사용한다.
Agent는 전표 PDF를 먼저 보관하고, `-PrinterName`이 있으면 Windows 기본 프린터를 변경하지 않고 지정 프린터로 출력한다.
테스트 완료 전 설치 명령에서는 `김제 프린터 (172.17.30.162)`를 지정한다.

지정 프린터 출력 예시:
```powershell
.\run_agent.ps1 `
  -Server https://172.17.39.121:8081 `
  -ClientIp 172.17.30.243 `
  -PrinterName "김제 프린터 (172.17.30.162)" `
  -InsecureSkipTlsVerify
```

운영 전환 시 지정 프린터:
```powershell
.\run_agent.ps1 `
  -Server https://172.17.39.121:8081 `
  -ClientIp 172.17.30.243 `
  -PrinterName "재정 프린터 (172.16.10.173)" `
  -InsecureSkipTlsVerify
```

출력 없이 큐/전표 데이터만 테스트할 때:
```powershell
.\run_agent.ps1 -Server https://172.17.39.121:8081 -ClientIp 172.17.30.243 -PrintMode off
```

self-signed 인증서를 아직 자동 전표처리 PC에 신뢰 등록하지 않은 테스트 환경에서는:
```powershell
.\run_agent.ps1 -Server https://172.17.39.121:8081 -ClientIp 172.17.30.243 -InsecureSkipTlsVerify
```

## 로그인/그룹웨어 DB 연동
- 그룹웨어 DB는 `gw_emp`, `ds_t_emp`에서 계정/부서/메일 정보를 읽기만 한다.
- 외부 MariaDB에는 INSERT/UPDATE/DELETE를 수행하지 않는다.
- 로컬 로그인 계정과 비밀번호 해시는 운영 데이터 폴더의 `excel_voucher.sqlite3`에 저장한다.
- 신규 동기화 계정의 초기 비밀번호는 `wowjd12!@`이며 최초 로그인 시 변경해야 한다.
- 비밀번호 찾기는 임시 비밀번호를 발급하고 메일 발송 후 다음 로그인에서 다시 변경을 강제한다.
- 전산 관리자 계정은 기존 회계업무 WEB DB `C:\ERP_DB\learned_data.db`의 `rlckd9646` 계정과 동기화한다.
- 기존 DB에서 전산 계정을 읽을 수 있으면 서버 시작 시와 로그인 직전에 비밀번호 변경 상태까지 반영한다.

운영 기본값은 `run_server.ps1`에 들어있다.
- 데이터 폴더: `C:\ERP_DB\excel_voucher_web_data`
- 그룹웨어 DB: `172.16.19.33:3306 / ksystem_yundong / dlpadmin2`
- 메일 SMTP: `35.216.76.148:25`

운영 서버 실행 예시:
```powershell
.\run_server.ps1 `
  -Port 8081 `
  -PublicOrigin https://172.17.39.121:8081 `
  -DataServerUrl http://127.0.0.1:18080 `
  -ForwardToDataServer `
  -RequireLogin `
  -GroupwareSyncOnStart `
  -SslCertFile C:\ERP_DB\certs\web_v1.cert.pem `
  -SslKeyFile C:\ERP_DB\certs\web_v1.key.pem
```

기본 그룹웨어 DB 계정은 `dlpadmin2`를 사용한다.
메일 송신은 기존 회계업무 WEB과 같은 내부 SMTP `35.216.76.148:25`, 발신자 `admpdm@dae-seung.co.kr`를 기본값으로 사용한다.
SMTP 서버 연결에 실패하면 메일은 실제 발송되지 않고 `data/mail_outbox`에 JSON으로 보관된다.
그룹웨어 DB 컬럼명은 자동 탐지하되 실제 컬럼명이 다르면 `app/groupware_directory.py`의 후보 목록 보강이 필요하다.

## 접속 확인
서버 PC에서:
```powershell
Get-NetTCPConnection -LocalPort 8081 -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName "Excel Voucher Web 8081" -Direction Inbound -Protocol TCP -LocalPort 8081 -Action Allow
```

자동 전표처리 PC에서:
```powershell
Test-NetConnection 172.17.39.121 -Port 8081
```

## 데이터 서버 전달
- 기본 URL: `http://127.0.0.1:18080`
- 기본 endpoint: `/api/excel-voucher/jobs`
- 자동 전달은 `run_server.ps1`의 `-ForwardToDataServer`로 켠다.
- 수동 재전달 API: `POST /api/jobs/{job_id}/forward`
