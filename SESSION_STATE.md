# SESSION STATE

## 현재 작업
- fix126 KT/케이티 거래처 키보드 시퀀스 방식 적용

## 현재 수정중 파일
- manager_server/전표 자동화 프로그램(담당자용)_v6.2.py
- web_v1/VERSION
- web_v1/agent/erp_agent.py
- web_v1/deploy/install_operating_server.ps1
- web_v1/backend/UPDATE_NOTES.txt
- PROJECT_STATUS.md
- CODEBASE_WIKI.md

## 방금 수정한 내용
- 로컬 Agent가 개발 폴더를 덮어써서 pythonw.exe Agent 중지 및 Run 등록 제거
- KT 거래처 팝업에서 검색조건/UIA/검색어칸 추정을 버리고 확인된 키보드 순서로 교체
- 순서: 거래처 칸 더블클릭 후 102-81-42945 입력, Tab 4, ↓ 5, ↑ 1, Tab 3, Enter
- WEB/Agent 버전 1.0.114 bump

## 다음 작업
- py_compile 검증
- Graphify update
- fix126 ZIP 생성/검증
- 관련 파일만 stage/commit/push
- 운영서버 배포 명령어 제공

## 주의사항
- 결과 행 좌표 선택 금지
- 검색조건/UIA/검색어칸 추정 금지
- active source만 수정
