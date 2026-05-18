# SESSION STATE

## 현재 작업
- fix124 KT/케이티 거래처 팝업 사업자번호 행 선택 핫픽스 진행 중

## 현재 수정중 파일
- manager_server/전표 자동화 프로그램(담당자용)_v6.2.py
- web_v1/VERSION
- web_v1/agent/erp_agent.py
- web_v1/deploy/install_operating_server.ps1
- web_v1/backend/UPDATE_NOTES.txt
- PROJECT_STATUS.md
- CODEBASE_WIKI.md

## 방금 수정한 내용
- KT/케이티 거래처 팝업에서 102-81-42945 완전일치뿐 아니라 행 텍스트 포함/숫자 포함 매칭을 허용
- 매칭된 셀의 y좌표와 팝업 왼쪽 행 영역을 더블클릭해 첫 번째 강조 행 대신 목표 사업자번호 행 선택
- WEB/Agent 버전 1.0.112 bump

## 다음 작업
- Graphify update 시도
- fix124 ZIP 생성/검증
- 관련 파일만 stage/commit/push
- 운영서버 배포 명령어 제공

## 주의사항
- active source 기준 수정
- backup / hotfix / release 폴더 참조만 가능
- 담당자 PC Agent는 서버 배포 후 자동 업데이트되어야 새 manager_server 스크립트를 받음
