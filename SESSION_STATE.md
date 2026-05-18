# SESSION STATE

## 현재 작업
- fix120 비밀번호 찾기/초기 비밀번호 변경 기능 적용 중

## 현재 수정중 파일
- web_v1/backend/app.py
- web_v1/backend/setup_state.py
- web_v1/backend/config.py
- web_v1/frontend/index.html
- web_v1/frontend/app.js
- web_v1/frontend/styles.css
- web_v1/VERSION
- web_v1/agent/erp_agent.py
- web_v1/deploy/install_operating_server.ps1
- web_v1/backend/UPDATE_NOTES.txt
- PROJECT_STATUS.md
- CODEBASE_WIKI.md

## 방금 수정한 내용
- 모든 기존 WEB 계정을 배포 후 1회 eotmd12!@로 초기화하는 auth_meta marker 추가
- 초기 비밀번호 로그인 시 새 비밀번호 변경 모달 표시
- 비밀번호 찾기: 사내 메일 인증코드 발송 후 새 비밀번호 설정 흐름 추가
- SMTP 설정은 mail_test.py 기준 35.216.76.148:25 구조를 사용
- SMTP ID/PW는 소스 하드코딩 대신 배포 시 PASSWORD_RESET_SMTP_USER/PW 환경변수로 받아 .env에 저장하도록 install_operating_server.ps1 수정
- 운영 배포 시 PASSWORD_RESET_SMTP_USER=admpdm, PASSWORD_RESET_SMTP_PW=admpdm, PASSWORD_RESET_FROM=admpdm@dae-seung.co.kr 지정 필요
- WEB/Agent 버전 1.0.108 bump

## 다음 작업
- graphify update 재실행
- ZIP 재생성/검증
- 관련 파일만 stage/commit/push
- 운영서버 배포 명령어 제공

## 주의사항
- local Agent가 개발 폴더를 덮어써 frontend가 삭제되는 현상이 있어 pythonw Agent를 중지한 뒤 작업함
- manager_server 수정 금지
- backup / hotfix / release 폴더 참조만 가능
- active source만 수정
