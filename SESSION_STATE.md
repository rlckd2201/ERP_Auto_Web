# SESSION STATE

## 현재 작업
- fix122 현금출금결의서 정산금액/지불처 누락 핫픽스 진행 중

## 현재 수정중 파일
- web_v1/backend/output_set.py
- web_v1/backend/expense_excel_export.py
- web_v1/VERSION
- web_v1/agent/erp_agent.py
- web_v1/deploy/install_operating_server.ps1
- web_v1/backend/UPDATE_NOTES.txt
- PROJECT_STATUS.md
- CODEBASE_WIKI.md

## 방금 수정한 내용
- 현금출금결의서 payload에 settlement_amount=청구금액, payee=거래처 추가
- Excel export가 I9/N9와 공통양식 후보셀에 정산금액/지불처를 기록하도록 수정
- WEB fallback PDF도 정산금액/지불처 값을 직접 출력하도록 수정
- WEB/Agent 버전 1.0.110 bump
- 로컬 pythonw Agent가 다시 개발 폴더를 덮어써 중지하고 HKCU Run 등록 임시 제거

## 다음 작업
- graphify update 시도 완료: 1291 < 1377 node 감소로 overwrite 거부됨
- fix122 ZIP 생성/검증 완료
- 관련 파일만 stage/commit/push
- 운영서버 배포 명령어 제공

## 주의사항
- manager_server 수정 금지
- backup / hotfix / release 폴더 참조만 가능
- active source만 수정
- 개발 PC에서 Agent를 다시 켜면 운영서버 구버전 bundle이 개발 소스를 덮을 수 있으니 운영서버를 1.0.110으로 먼저 배포
