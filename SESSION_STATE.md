# SESSION STATE

## 현재 작업
- fix132 AutoEver/현대오토에버 정기 ERP 거래처 사업자번호 입력 보정 진행

## 현재 수정중 파일
- manager_server/전표 자동화 프로그램(담당자용)_v6.2.py
- web_v1/backend/erp_runner.py
- web_v1/VERSION
- web_v1/agent/erp_agent.py
- web_v1/deploy/install_operating_server.ps1
- web_v1/backend/UPDATE_NOTES.txt
- PROJECT_STATUS.md
- CODEBASE_WIKI.md
- SESSION_STATE.md

## 방금 수정한 내용
- AutoEver/현대오토에버 vendor special-case 추가: 사업자번호 104-81-53190
- KT에서 검증한 거래처 팝업 키보드 시퀀스를 공용 사업자번호 입력 함수로 바꿈
- 정기 ERP payload에서 AutoEver 계열 vendor_biz_no/supplier_biz_no 자동 보강
- WEB/Agent 버전 1.0.120 bump
- py_compile 통과
- AutoEver regular payload regression 통과

## 다음 작업
- fix132 ZIP 생성/검증 완료: C:\Tmp\accounting_web_v1_autoever_vendor_biz_fix132_20260520_110020.zip
- graphify update 시도 완료: 1297 vs 1383 node 감소로 graphify가 overwrite 거부, 기존 graph 유지
- 관련 파일만 stage/commit/push

## 주의사항
- backup/hotfix/release 폴더 수정 금지
- 현재 워크트리에는 unrelated dirty/delete 파일이 많으므로 관련 파일만 stage
