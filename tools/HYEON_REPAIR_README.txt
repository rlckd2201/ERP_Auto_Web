현시훈 PC 회계 프로그램 복구 v2

1. 현시훈 본인 PC에서 ZIP 압축을 모두 풀어 주세요.
2. AccountingWebRepair.exe를 더블클릭해 주세요. 관리자 권한으로 실행하지 않습니다.
3. 완료 또는 오류가 표시될 때까지 창을 닫지 마세요. 패키지 설치에는 몇 분 걸릴 수 있습니다.
4. Agent 실행이 확인되면 포털의 회계 화면에서 '다시 점검'을 눌러 주세요.
5. 성공/실패와 관계없이 본인 바탕화면의 AccountingWeb_Repair_날짜시간.json 파일을 김기창 매니저에게 전달해 주세요.

적용 범위
- 현시훈PC / 현시훈 Windows 계정에서만 복구합니다.
- 실제 Python 경로와 패키지 import, Python에서의 서버 HTTPS 연결을 확인합니다.
- 필수 패키지가 정상인 Python 3.11 x64가 있으면 재사용합니다.
- 필요한 경우 Python 3.11을 사용자 범위에 설치하고 회계 프로그램용 가상환경을 별도로 만듭니다.
- 기존 Python을 삭제하지 않습니다. 원래 실행 스크립트는 변경 전에 .before_repair_날짜시간으로 백업합니다.
- 서버 프로그램, ERP 전표, 프린터 설정, 계정 비밀번호는 이 파일로 변경하지 않습니다.
- Agent 시작은 정상 운영 프로그램의 실행 재개입니다. 이 복구 파일 자체는 전표/출력 작업을 등록하지 않습니다.
- 'Agent 실행 확인'은 프로세스 확인입니다. 서버 연결 및 필수환경 완료 여부는 서버 기록과 포털에서 별도로 확인합니다.
- 결과 파일은 본인 PC에만 저장하며 자동 전송하지 않습니다.

검증 범위
Windows PowerShell 5.1에서 인수 전달, 실제 Python import, 실패 시 중단, 출력의 자격증명 가림, 실행 스크립트 생성 및 대상 제한을 검증했습니다.
현시훈 PC에서 실제 복구 실행과 새 Agent 연결은 아직 확인 전입니다.

v2 변경 이유
16:32 복구 결과에서 Python 3.15의 필수 패키지는 모두 정상으로 확인됐습니다.
첫 복구 파일은 Python HTTPS 검사에서 'Missing Subject Key Identifier' 인증서 오류로 중단됐으며, 실행 스크립트를 변경하거나 Agent를 시작하지 않았습니다.
같은 서버에 Python 3.11의 CA/호스트 검증을 유지한 HTTPS 접속은200으로 확인했습니다. v2는 이 실행환경을 사용합니다. 기존 Python 3.15 및 공유 서버 인증서는 변경하지 않습니다.
이는 확인된 복구 도구의 중단 지점을 수정한 것입니다. 원래 Agent 미실행의 모든 원인이 해결됐다는 의미는 아니며, 실행 후 서버 연결 확인이 필요합니다.
Python SSL 검증 기본값 참고: https://docs.python.org/3.13/library/ssl.html#ssl.create_default_context

WinGet 사용자 범위 설치 옵션 참고: https://learn.microsoft.com/en-us/windows/package-manager/winget/install
