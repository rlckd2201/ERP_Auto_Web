# SESSION STATE

## 현재 작업
- fix115 작업중
- 정기 처리 ERP 관리항목 거래처 입력에서 KT/케이티 중복 검색 시 사업자번호 102-81-42945 행 선택 로직 반영

## 현재 수정중 파일
- manager_server/전표 자동화 프로그램(담당자용)_v6.2.py
- web_v1/VERSION
- web_v1/agent/erp_agent.py
- web_v1/deploy/install_operating_server.ps1
- web_v1/backend/UPDATE_NOTES.txt
- PROJECT_STATUS.md
- CODEBASE_WIKI.md
- SESSION_STATE.md

## 방금 수정한 내용
- KT/케이티 거래처는 payload의 supplier/vendor business number보다 ERP 거래처 사업자번호 102-81-42945를 우선 사용
- ERP 거래처 팝업에서 102-81-42945 행을 찾으면 해당 셀/행을 더블클릭 후 Enter
- 102-81-42945 행이 없거나 팝업이 없으면 첫 번째 케이티 행을 Enter로 잘못 선택하지 않고 PASS
- frontend/setup 필수 파일이 디스크에서 삭제 상태라 배포 ZIP 깨짐 방지를 위해 HEAD 기준으로 복원
- WEB/Agent 버전 1.0.103 bump
- 업데이트 노트 fix115 갱신
- changed-file py_compile, frontend node syntax check, graphify update 완료
- fix115 ZIP 생성 및 내용 검증 완료: C:\Tmp\accounting_web_v1_kt_vendor_bizno_fix115_20260515_144302.zip
- fix115 커밋/푸시 완료: ff1b0c8 Fix KT regular vendor selection

## 다음 작업
- 운영서버 172.17.39.121 배포 명령 제공
- 운영서버 배포 후 담당자 PC Agent 재시작/업데이트 확인

## 주의사항
- active source는 web_v1, active Agent-side ERP GUI source는 manager_server/전표 자동화 프로그램(담당자용)_v6.2.py
- backup / hotfix / release 폴더 수정 금지
- 작업트리에 unrelated dirty 파일이 많으므로 stage/commit은 fix115 관련 파일만
- 로컬 Agent가 켜지면 서버 payload로 개발 폴더를 덮어쓸 수 있으니 운영서버를 1.0.103으로 올린 뒤 Agent 재시작
