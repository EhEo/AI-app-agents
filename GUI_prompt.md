# AI-app-agent GUI 빌더 — Agent Team 프롬프트

## 📋 복사용 프롬프트 (아래 코드블록 전체를 Claude Code 또는 새 Claude 세션에 붙여넣으세요)

```
AI-app-agent 프로젝트(C:\Users\MISTOP\Documents\02_AI디지털전환\AI-app-agent)의 터미널 전용 초기화 명령(agents-init)을 GUI로 감싸는 Windows 데스크톱 애플리케이션을 만드는 agent team을 구성해줘.

배경: 현재 프로젝트의 CLAUDE.md에 정의된 3-agent 오케스트레이션(PM+Coder / Gemini Researcher / Codex Reviewer)을 시작하려면 터미널에서 `agents-init` 명령으로 .agents-dev/ 구조, CLAUDE.md, .gitignore를 세팅한 뒤 `claude` 명령으로 Claude Code 세션을 열어야 한다. 이 과정을 모르는 사용자도 (1) 폴더 선택 → (2) 큰 버튼 클릭 → (3) 자동으로 초기화 + Claude 세션 시작이 되도록 만드는 게 목표다.

조교 A (설계 조교): 다음을 결정해서 한 페이지짜리 설계 문서로 정리해줘.
  - 기술 스택: Python 3.11+ / Tkinter 기본 (표준 라이브러리 우선, 외부 의존성 최소화)
  - 화면 구성:
    ① 상단: 폴더 경로 표시 라벨 + [폴더 선택] 버튼
    ② 중앙: [🚀 Agents 초기화 + Claude 실행] 메인 버튼 (크고 눈에 띄게)
    ③ 하단: 진행 로그 영역 (스크롤 가능한 텍스트 박스, 한글 표시 OK)
    ④ 최하단: 상태 표시줄 ("준비됨" / "초기화 중..." / "완료" 등)
  - agents-init이 해야 할 동작 정의:
    (a) 선택한 폴더에 `.agents-dev/log/` 폴더 생성
    (b) CLAUDE.md 템플릿을 폴더 루트에 생성 (이미 있으면 백업 후 덮어쓸지 사용자에게 묻기)
    (c) `.gitignore`에 `.agents-dev/log/`, `.claude/settings.local.json` 추가 (중복 방지)
    (d) `~/.agents-dev/scripts/ask-gemini.sh`, `ask-codex.sh` 존재 확인 후 없으면 안내 메시지
  - Claude 실행 방식: 초기화 성공 후 Windows에서 새 cmd 창을 열어 해당 폴더에서 `claude` 명령 자동 실행
    구현 예: `subprocess.Popen(f'start cmd /k cd /d "{folder}" && claude', shell=True)`
  - 에러 케이스 매트릭스:
    | 케이스 | GUI 반응 |
    |---|---|
    | 폴더 미선택 후 버튼 클릭 | 경고창 "먼저 폴더를 선택해주세요" |
    | 권한 부족 | 로그에 "관리자 권한이 필요할 수 있습니다" |
    | 이미 초기화된 폴더 | "이미 초기화되어 있습니다. 다시 진행하시겠습니까?" 확인창 |
    | claude CLI 미설치 | 로그에 설치 안내 (https://docs.claude.com/en/docs/claude-code) |
    | Python/Tk 미설치 | README에 사전 설치 안내 |
  설계가 끝나면 와이어프레임(ASCII 아트)과 전체 함수 구조(클래스/함수 시그니처)를 구현 조교에게 넘겨줘.

조교 B (구현 조교): 설계 조교의 문서를 받아 단일 파일 Python 스크립트 `agents_gui.py`를 작성해줘.
  - Tkinter 기반 단일 파일 (외부 패키지 0개)
  - 폴더 선택은 `tkinter.filedialog.askdirectory()` 사용
  - agents-init 로직은 `init_agents_workspace(folder_path: Path) -> list[str]` 함수로 분리 (반환값은 진행 로그 라인 리스트)
  - 진행 로그는 GUI 텍스트 박스에 실시간 append, GUI freeze 방지를 위해 `threading.Thread` 사용
  - Claude 실행은 `launch_claude_session(folder_path: Path) -> bool` 함수로 분리
  - CLAUDE.md 템플릿은 스크립트 내부 문자열 상수 `CLAUDE_MD_TEMPLATE`로 보관 (현재 AI-app-agent의 CLAUDE.md 내용을 그대로 사용)
  - 한글 인코딩 안전: 파일 입출력 시 `encoding='utf-8'` 명시
  - 윈도우 종료 시 백그라운드 스레드 안전 정리
  - PEP 8 준수, 한글 주석 OK
  - 파일 상단 docstring에 실행법(`python agents_gui.py`)과 PyInstaller 빌드 명령(`pyinstaller --onefile --windowed --name AgentsInit agents_gui.py`) 명시
  완성된 코드를 검증 조교에게 넘기면서, 직접 테스트한 시나리오 목록을 함께 적어줘.

조교 C (검증 조교): 구현 조교의 코드를 받아 다음을 모두 점검하고 표 형태로 보고해줘.
  - [기능] 빈 폴더 선택 → 초기화 → .agents-dev/log/와 CLAUDE.md가 정상 생성되는가
  - [기능] 이미 초기화된 폴더 재선택 → 확인창이 뜨고, 취소하면 변경 없이 종료되는가
  - [기능] 폴더 미선택 상태에서 버튼 클릭 → 경고 메시지가 표시되는가
  - [기능] claude CLI가 없을 때 → 로그에 설치 안내가 노출되는가
  - [기능] .gitignore에 이미 같은 항목이 있을 때 중복 추가하지 않는가
  - [UX] 초기화 진행 중 GUI가 멈추지 않는가 (threading 작동 확인)
  - [UX] 한글 로그가 깨지지 않고 표시되는가
  - [코드] 단일 파일로 실행 가능한가 (외부 의존성 0)
  - [문서] README.md 작성: 실행법 / PyInstaller 빌드법 / FAQ 3개(설치 안내, claude CLI 연동, 일반 오류 대처)
  문제가 1건이라도 있으면 구현 조교에게 "어떤 입력에서, 어떤 동작이 기대됐는데, 실제로는 어떻게 됐는지" 형식으로 구체적 수정 요청을 보내. 모두 통과하면 최종 패키지를 리드에게 전달해줘.

작업 순서: A → B → C 순으로 진행. C가 수정을 요청하면 B로 돌아가 재구현 후 다시 C에게 보내는 루프를 최대 3회까지 반복. 3회 후에도 잔여 이슈가 있으면 리드에게 보고하고 출시해줘.

협업 지시:
  - A는 B에게 와이어프레임과 함수 시그니처를 넘길 때 "왜 이렇게 설계했는지" 근거를 함께 적어줘.
  - B는 C에게 코드를 넘길 때 자신이 이미 돌려본 시나리오를 명시해서 C가 중복 테스트하지 않도록 해줘.
  - C는 B에게 피드백할 때 재현 가능한 형태(입력 / 기대 / 실제)로 적어줘.

리드 역할: 최종적으로 다음 3개 파일을 사용자에게 전달해줘.
  (1) agents_gui.py — `python agents_gui.py` 또는 더블클릭으로 바로 실행 가능
  (2) README.md — 설치 / 실행 / 빌드 / FAQ 포함
  (3) build.bat — PyInstaller로 .exe 만드는 1줄 스크립트
또한 사용자가 자주 커스터마이즈할 부분(CLAUDE.md 템플릿 내용, Claude 실행 방식, 추가할 초기화 항목)을 README의 "커스터마이즈" 섹션에 표시해줘.
```

---

## 📌 2~3줄 요약

세 명의 조교(설계 / 구현 / 검증)가 순차 협업하여, AI-app-agent의 `agents-init` 터미널 명령을 Tkinter GUI로 감싸는 Python 단일 파일 앱과 .exe 빌드 스크립트를 만듭니다. 사용자는 폴더를 선택하고 큰 버튼 하나만 누르면 `.agents-dev/` 구조 생성 → CLAUDE.md 배치 → `.gitignore` 갱신 → Claude Code 세션 자동 시작까지 한 번에 처리됩니다.

---

## 🛠 커스터마이즈 가이드

| 바꾸고 싶은 부분 | 수정할 위치 |
|---|---|
| 다른 프로젝트용으로 쓰기 | 프롬프트 첫 줄의 경로(`C:\Users\MISTOP\...AI-app-agent`)를 새 경로로 변경 |
| CLAUDE.md 템플릿 내용 | "CLAUDE_MD_TEMPLATE 문자열 상수" 언급 부분 — 다른 템플릿 사용 시 명시 |
| Mac/Linux 지원 추가 | 조교 A의 "Claude 실행 방식" 블록에 `os.name == 'nt'` 분기 요청 추가 |
| Tkinter 대신 PyQt 사용 | 조교 B 첫 줄 "Tkinter 기반"을 "PyQt6 기반"으로 변경 + 의존성 허용 |
| 조교를 추가 (예: 디자이너) | "조교 D (디자이너 조교): ..." 블록을 같은 형식으로 추가 |
| Gemini/Codex 자동 설치까지 포함 | agents-init 동작 정의 (d)번 항목을 "없으면 안내" → "없으면 자동 다운로드"로 변경 |
