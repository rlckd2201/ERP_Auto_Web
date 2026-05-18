# SESSION STATE

## 현재 작업
- fix121 구매 원클릭 ERP payload vendor_biz_no NameError 핫픽스 진행 중

## 현재 수정중 파일
- web_v1/backend/erp_runner.py
- web_v1/VERSION
- web_v1/agent/erp_agent.py
- web_v1/deploy/install_operating_server.ps1
- web_v1/backend/UPDATE_NOTES.txt
- PROJECT_STATUS.md
- CODEBASE_WIKI.md

## 방금 수정한 내용
- build_purchase_erp_payload()에서 vendor_biz_no를 return 전에 정의하도록 수정
- supplier/vendor 사업자번호가 없으면 빈 문자열로 Agent 큐 payload 생성
- WEB/Agent 버전 1.0.109 bump
- 로컬 pythonw Agent가 개발 폴더를 덮어써 패치가 사라지는 현상 확인 후 Agent 중지

## 다음 작업
- graphify update 시도 완료: 1291 < 1377 node 감소로 overwrite 거부됨
- fix121 ZIP 생성/검증 완료
- 관련 파일만 stage/commit/push
- 운영서버 배포 명령어 제공

## 주의사항
- manager_server 수정 금지
- backup / hotfix / release 폴더 참조만 가능
- active source만 수정
- 개발 PC에서 Agent를 다시 켜면 서버 구버전 bundle이 개발 소스를 덮을 수 있으니 운영서버를 1.0.109로 먼저 배포
