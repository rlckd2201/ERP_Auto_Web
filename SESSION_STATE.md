# SESSION STATE

## 현재 작업
- fix113 SMILE EDI 정기 처리 통합 작업중

## 현재 수정중 파일
- tax_crawler/crawler_main.py
- tax_crawler/portal_smileedi.py
- web_v1/backend/invoice_db.py
- web_v1/frontend/index.html
- web_v1/VERSION
- web_v1/agent/erp_agent.py
- web_v1/deploy/install_operating_server.ps1
- web_v1/backend/UPDATE_NOTES.txt
- PROJECT_STATUS.md
- CODEBASE_WIKI.md
- SESSION_STATE.md

## 방금 수정한 내용
- SMILE EDI DtiEmail.do 링크를 메일 링크 추출과 crawler_main handler 목록에 등록
- SMILE EDI는 기본 자동 승인 금지 유지, 미승인 계산서는 자동 저장 실패 처리
- 승인 완료되어 PDF/XML 저장된 SMILE EDI는 정기건으로 저장하고 기본 계정을 지급수수료로 설정
- 정기 처리 출력 세트는 전표와 세금계산서만 요구하므로 현금출금결의서/견적서/품의 흐름에는 연결하지 않음
- 버전 1.0.101 bump
- graphify update .는 1255 < 1318 node 감소 보호로 overwrite 거부됨

## 다음 작업
- 실제 운영 메일에서 SMILE EDI 승인완료/미승인 케이스 각각 E2E 확인
- 운영서버 172.17.39.121에 fix113 ZIP 배포
- 담당자 PC Agent 업데이트 후 정기 원클릭 ERP/전표+세금계산서 출력 확인

## 주의사항
- active source는 web_v1 및 tax_crawler 기준
- backup / hotfix / release 계열 폴더 수정 금지
- SMILE EDI 승인은 되돌릴 수 없으므로 운영 자동수집에서는 승인 버튼을 누르지 않음
