# Agents GUI Launcher — 설계 문서

**날짜:** 2026-05-12
**상태:** 승인됨

---

## 목표

`agents-init` 터미널 명령을 GUI로 감싸는 Windows 데스크톱 앱.
폴더 선택 → 버튼 클릭 → `.agents-dev/` 구조 생성 + CLAUDE.md 배치 + `.gitignore` 갱신 + Claude Code 세션 자동 시작.

---

## 기술 스택

- Python 3.11+
- Tkinter (표준 라이브러리, 외부 의존성 0)
- threading.Thread (GUI freeze 방지)
- subprocess.Popen (Claude 세션 실행)

---

## 파일 구조

```
AI-app-agent/
├── agents_gui.py     ← 단일 파일 앱
├── README.md         ← 설치/실행/빌드/FAQ
└── build.bat         ← PyInstaller .exe 빌드 스크립트
```

---

## 화면 레이아웃

```
┌──────────────────────────────────────────────┐
│  Agents Init Launcher                        │
├──────────────────────────────────────────────┤
│  [C:\Users\...\my-project          ] [선택]  │
├──────────────────────────────────────────────┤
│    ┌────────────────────────────────────┐    │
│    │  🚀 Agents 초기화 + Claude 실행    │    │
│    └────────────────────────────────────┘    │
│  ┌──────────────────────────────────────┐   │
│  │ 진행 로그 (스크롤 가능)               │   │
│  └──────────────────────────────────────┘   │
├──────────────────────────────────────────────┤
│  상태: 준비됨                                │
└──────────────────────────────────────────────┘
```

---

## 클래스 / 함수 구조

```python
CLAUDE_MD_TEMPLATE: str          # CLAUDE.md 내용 상수

class AgentsGUI(tk.Tk):
    def _build_ui() -> None
    def _select_folder() -> None
    def _run_init() -> None       # threading.Thread 진입점
    def _append_log(msg: str) -> None
    def _set_status(msg: str) -> None

def init_agents_workspace(folder: Path) -> list[str]
    # (a) .agents-dev/log/ 생성
    # (b) CLAUDE.md 생성 (백업 확인 포함)
    # (c) .gitignore 갱신 (중복 방지)
    # (d) ask-gemini.sh / ask-codex.sh 존재 확인

def launch_claude_session(folder: Path) -> bool
    # subprocess.Popen('start cmd /k ...', shell=True)
```

---

## 에러 케이스 매트릭스

| 케이스 | GUI 반응 |
|---|---|
| 폴더 미선택 후 버튼 클릭 | messagebox.showwarning |
| 이미 초기화된 폴더 | messagebox.askyesno 확인창 |
| 권한 부족 | 로그에 "관리자 권한이 필요할 수 있습니다" |
| claude CLI 미설치 | 로그에 설치 URL (https://docs.claude.com/en/docs/claude-code) |
| ask-gemini/codex.sh 없음 | 로그에 경로 안내 메시지 |

---

## agents-init 동작 정의

1. `{folder}/.agents-dev/log/` 폴더 생성
2. `{folder}/CLAUDE.md` 생성 (기존 파일 있으면 `.bak` 백업 후 덮어쓸지 확인)
3. `{folder}/.gitignore` 에 `.agents-dev/log/`, `.claude/settings.local.json` 추가 (중복 방지)
4. `~/.agents-dev/scripts/ask-gemini.sh`, `ask-codex.sh` 존재 확인 → 없으면 경고 로그

---

## Claude 실행 방식

```python
subprocess.Popen(
    f'start cmd /k "cd /d \"{folder}\" && claude"',
    shell=True
)
```
