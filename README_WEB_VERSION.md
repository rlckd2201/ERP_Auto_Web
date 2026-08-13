# 회계업무 자동화 웹 시스템

> 현재 통합 기준: 2026-08-13
>
> 이 저장소에는 배포와 데이터 경계가 다른 두 웹 제품이 공존합니다. 현재 통합
> 브랜치의 `web_v1/VERSION`은 `1.0.164`입니다. 별도 원본 작업 폴더의
> 미커밋 1.0.228 변경은 이 브랜치에 포함되지 않았습니다.

## 제품 구분

| 제품 | 역할 | 기본 포트 | 상태/저장소 |
|---|---|---:|---|
| `web_v1` | 메일 수집, 세금계산서·구매/정기 처리, 작업 큐와 문서 세트 | 8080 계열 기존 배포 설정 | `C:\ERP_DB` 기반 기존 WEB/Agent 데이터 |
| `excel_voucher_web` | 수시결제 엑셀 업로드를 단일 ERP 전표로 처리 | 8081 | 별도 SQLite·업로드·Agent 큐 |

두 제품은 `manager_server`의 K-System GUI 자동화 계보를 공유하지만 서버
프로세스, 큐, 데이터 디렉터리, 포트와 릴리스 버전은 합치지 않습니다.

## 구조

```text
web_v1 브라우저 -> web_v1 FastAPI/SQLite -> manager-PC Agent
                                             -> K-System/Excel/프린터

Excel 전표 브라우저 -> excel_voucher_web FastAPI/SQLite -> 172.17.30.243 Agent
                                                        -> K-System/프린터/PDF
```

- `web_v1/backend/app.py`: 기존 회계업무 API와 조정 서버
- `web_v1/agent/erp_agent.py`: 기존 담당자 PC Agent
- `tax_crawler/`: 포털별 세금계산서 수집
- `excel_voucher_web/app/main.py`: 엑셀 전표 웹 서버
- `excel_voucher_web/agent/agent_worker.py`: 엑셀 전표 전용 Agent
- `manager_server/전표 자동화 프로그램(담당자용)_v6.2.py`: 공유 ERP GUI 구현

## 현재 통합 주의사항

- 원격 `main`의 Excel 전표 라인은 2026-07-27에 210행 입력, 저장, 출력까지
  완주했으며 `stable-2026-07-27-full-success` 태그가 기준선입니다.
- `web_v1/backend/zoom_billing.py`는 존재하지만 이 브랜치의
  `mail_collector.py`에는 연결되지 않았습니다. Zoom 자동수집을 이 통합
  브랜치의 활성 기능으로 간주하지 마십시오.
- ERP API/DB RFP는 향후 공식 연동 목표이며 현재 구현은 Windows GUI Agent
  방식입니다.
- 운영 검증은 두 제품을 각각 수행해야 합니다. 한 제품의 성공을 다른 제품의
  E2E 증거로 사용하지 않습니다.

현재 인수인계는 루트 `SESSION.md`, `TODO.md`, `DECISIONS.md`,
`DEBUG.md`를 먼저 읽고, Excel 전표의 상세 실행 이력은
`excel_voucher_web/` 아래 문서를 확인합니다.
