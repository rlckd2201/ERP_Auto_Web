# Excel Voucher Web

담당자가 엑셀을 업로드하면 서버가 전표 payload를 만들고, 172.17.30.243 담당자 PC Agent가 작업을 가져가 ERP 전표 처리를 수행하는 신규 웹 기반 시스템이다.

## 실행
```powershell
cd excel_voucher_web
.\run_server.ps1 `
  -Port 8081 `
  -PublicOrigin https://172.17.39.121:8081 `
  -DataServerUrl http://127.0.0.1:18080 `
  -ForwardToDataServer `
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

## 데이터 서버 전달
- 기본 URL: `http://127.0.0.1:18080`
- 기본 endpoint: `/api/excel-voucher/jobs`
- 자동 전달은 `run_server.ps1`의 `-ForwardToDataServer`로 켠다.
- 수동 재전달 API: `POST /api/jobs/{job_id}/forward`
