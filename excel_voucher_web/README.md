# Excel Voucher Web

담당자가 엑셀을 업로드하면 서버가 전표 payload를 만들고, 172.17.30.243 담당자 PC Agent가 작업을 가져가 ERP 전표 처리를 수행하는 신규 웹 기반 시스템이다.

## 실행
```powershell
cd excel_voucher_web
.\run_server.ps1
```

브라우저에서 `http://127.0.0.1:18100`을 연다.

## Agent 실행 예시
```powershell
cd excel_voucher_web
.\run_agent.ps1 -Server http://127.0.0.1:18100
```

운영에서는 `EXCEL_VOUCHER_TARGET_AGENT_IP=172.17.30.243`를 기본으로 사용한다.
