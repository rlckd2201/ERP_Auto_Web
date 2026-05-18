# SESSION STATE

## 현재 작업
- fix125 KT/케이티 거래처 사업자번호 팝업 검색 방식 적용 중

## 현재 수정중 파일
- manager_server/전표 자동화 프로그램(담당자용)_v6.2.py
- web_v1/VERSION
- web_v1/agent/erp_agent.py
- web_v1/deploy/install_operating_server.ps1
- web_v1/backend/UPDATE_NOTES.txt
- PROJECT_STATUS.md
- CODEBASE_WIKI.md

## 방금 수정한 내용
- KT 거래처 입력에서 결과 행 좌표/Y추정/UIA 행 활성화 방식 제거
- 빈 거래처 칸 더블클릭으로 거래처 팝업을 열고 검색조건을 사업자번호로 바꾼 뒤 % 102-81-42945 입력 후 Enter 두 번으로 확정하는 흐름 추가
- WEB/Agent 버전 1.0.113 bump

## 다음 작업
- py_compile 검증
- Graphify update
- fix125 ZIP 생성/검증
- 관련 파일만 stage/commit/push
- 운영서버 배포 명령어 제공

## 주의사항
- active source 기준 수정
- backup / hotfix / release 폴더 참조만 가능
- 담당자 PC Agent는 서버 배포 후 자동 업데이트되어야 manager_server 스크립트를 받음
