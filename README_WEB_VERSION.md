# 회계업무 자동화 WEB v1.0

> **현재 기준: 2026-08-12 / WEB `1.0.228`**
>
> 이 저장소의 운영 구조는 **운영서버 + 담당자 PC Agent**입니다. 운영서버가
> 메일 수집, 세금계산서/구매 문서 분석, SQLite 상태 관리 및 작업 큐를 담당하고,
> 담당자 PC Agent가 K-System GUI, Excel, 프린터와 같은 Windows 로컬 작업을
> 수행한 뒤 결과 PDF를 서버에 다시 전달합니다. `tax_crawler`는 포털별
> 세금계산서 수집에 사용됩니다.

## 현재 운영 구조

```text
브라우저 → FastAPI 운영서버 → SQLite / 작업 큐 → 담당자 PC Agent
                                         └→ K-System · Excel · 프린터 · PDF 결과 업로드
```

- 서버 진입점: `web_v1/backend/__main__.py`
- 서버 API/작업 조정: `web_v1/backend/app.py`
- 담당자 PC 실행 Agent: `web_v1/agent/erp_agent.py`
- 포털별 세금계산서 수집: `tax_crawler/`
- 기존 K-System 자동화 연계: `manager_server/`

정리일: 2026-08-12

## 현재 개발 기준

- 활성 개발 대상: 회계업무 자동화 WEB v1.0
- 활성 작업 루트: `web_v1`
- 기존 데스크톱 UI는 과거 구조이지만 `manager_server`의 ERP 자동화 모듈은 Agent가 현재도 재사용한다.

## 폴더 구성

- web_v1: WEB v1.0 신규 개발 루트
- manager_server: 담당자용 v6.2 ERP GUI 자동화 소스. `erp_runner.py`가 동적으로 불러오는 현재 런타임 의존성
- manager_server/dist: 기존 담당자용 v6.2 실행파일 참고자료
- tax_crawler: WEB v1.0 메일 수집기가 현재 사용하는 포털별 세금계산서 크롤러
- tax_crawler/docs: 크롤러 문서
- docs: 작업 메모 및 md 문서 모음
- support: 설정, ERP 핸들러, 공통 양식, 핫픽스 파일

## WEB v1.0 방향

- 사용자는 웹 담당자 화면에서 필요한 기능을 선택한다.
- 운영서버는 메일 수집, 크롤링, 분석, DB, 작업 큐와 문서 세트를 조정한다.
- ERP GUI 입력, Excel 결의서 생성, 로컬 프린터 출력은 담당자 PC Agent가 수행한다.
- 웹 화면에는 작업 진행률과 로그를 표시한다.
- 작업 완료/실패 시 Chrome/Edge 브라우저 알림을 띄운다.
- ERP/Excel/프린터 작업은 대상 Agent가 JSON 작업 큐에서 순차 처리한다.

## 제외한 것

- backup_* 파일/폴더
- build, __pycache__, 테스트 출력 폴더
- 과거 버전 exe/spec/py
