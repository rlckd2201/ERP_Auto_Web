# SESSION STATE

## 현재 작업
- Graphify 기준선 force refresh 완료 및 서버 시작 명령 정정

## 현재 수정중 파일
- graphify-out/GRAPH_REPORT.md
- graphify-out/graph.json
- graphify-out/graph.html
- PROJECT_STATUS.md
- CODEBASE_WIKI.md
- SESSION_STATE.md

## 방금 수정한 내용
- Graphify 내부 API force=True로 graphify-out 갱신
- 새 기준선: 230 files / 1298 nodes / 4074 edges / 41 communities
- install_operating_server.ps1은 설치만 하고 서버 시작은 start_operating_server.ps1 별도 실행 필요함을 확인

## 다음 작업
- Graphify 기준선 문서 커밋/푸시
- 서버 시작 명령 사용자에게 재전달

## 주의사항
- Gemini API 키는 소스/ZIP에 넣지 않음
- worktree에 unrelated dirty/delete가 많으므로 관련 파일만 stage
