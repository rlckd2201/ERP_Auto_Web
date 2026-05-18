# SESSION STATE

## 현재 작업
- fix123 문서세트 선택 개별출력/개별 PDF 저장 핫픽스 진행 중

## 현재 수정중 파일
- web_v1/frontend/app.js
- web_v1/frontend/styles.css
- web_v1/backend/models.py
- web_v1/backend/app.py
- web_v1/backend/worker.py
- web_v1/backend/output_set.py
- web_v1/VERSION
- web_v1/agent/erp_agent.py
- web_v1/deploy/install_operating_server.ps1
- web_v1/backend/UPDATE_NOTES.txt
- PROJECT_STATUS.md
- CODEBASE_WIKI.md

## 방금 수정한 내용
- 문서세트 카드에 선택 체크박스 추가
- 문서 하나 이상 선택 시에만 개별 PDF 저장/개별 출력 버튼 활성화
- 프론트에서 selected_doc_keys를 output-set job payload로 전송
- 백엔드/worker/output_set이 selected_doc_keys를 받아 선택 문서만 복사/저장/출력 큐에 포함
- WEB/Agent 버전 1.0.111 bump

## 다음 작업
- Graphify update 시도
- fix123 ZIP 생성/검증
- 관련 파일만 stage/commit/push
- 운영서버 배포 명령어 제공

## 주의사항
- manager_server 수정 금지
- backup / hotfix / release 폴더 참조만 가능
- active source만 수정
- 기존 문서 출력/통합본 PDF 저장은 전체 문서세트 동작 유지
- 개별 PDF 저장/개별 출력만 선택 문서 제한 적용
