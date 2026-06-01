# Agents Init Launcher

`agents-init` 터미널 명령을 GUI로 감싼 Windows 데스크톱 앱.

폴더 선택 → 버튼 클릭 한 번으로:

1. `.agents-dev/log/` 폴더 생성
2. `CLAUDE.md` (3-agent 오케스트레이션 템플릿) 배치
3. `.gitignore` 자동 갱신
4. Claude Code 세션 GUI 내 터미널에서 자동 시작 (PTY 내장)

---

## 터미널 단독 실행 (agents-init)

GUI 없이 Git Bash 에서 바로 3-에이전트 tmux 세션을 띄울 수 있습니다.

```bash
agents-init            # 현재 폴더 초기화 + tmux 3분할 (Claude · Gemini · Codex)
agents-init ~/proj     # 특정 폴더 지정
agents-init . --bypass # claude --dangerously-skip-permissions 로 시작
agents-init . --no-attach   # 세션만 만들고 attach 안 함
```

- `agents-init` / `agent-init` 와 `install-tmux.sh` 는 **GUI 최초 실행 시 `~/bin/` 에 자동 설치**됩니다
  (번들 `agents_scripts/bin/` → `install_bundled_scripts()`). `~/bin` 은 Git Bash 의
  `/etc/profile.d/env.sh` 가 PATH 에 자동 추가하므로 새 터미널에서 바로 `agents-init` 이 잡힙니다.
- **tmux** 가 없으면 한 번만: `bash ~/bin/install-tmux.sh`
  (MSYS2 공식 패키지에서 tmux + libevent 를 받아 `~/bin` 에 설치, 관리자 권한 불필요.
  `msys-2.0.dll` 은 Git Bash 것을 공유 — cygheap 충돌 방지).
- 새 폴더에는 `~/.agents-dev/CLAUDE.md.template` 의 오케스트레이션 정책이 `CLAUDE.md` 로 복사됩니다.

---

## 실행법

### 방법 1: Python 직접 실행 (개발·테스트용)

**사전 요구사항:**

- Python 3.11+
- `claude` CLI ([설치 안내](https://docs.claude.com/en/docs/claude-code))
- `pywinpty` (GUI 내 PTY 터미널에 필요, 없으면 별도 cmd 창으로 자동 폴백)

  ```bash
  pip install pywinpty
  ```

- `~/.agents-dev/scripts/ask-gemini.sh`, `ask-codex.sh` (AI-app-agent 세팅 후 자동 생성)

```bash
python agents_gui.py
```

### 방법 2: .exe 더블클릭 (배포용)

`dist/AgentsInit.exe` 를 더블클릭. Python 불필요.

빌드 방법은 아래 "빌드" 섹션 참조.

---

## 단위 테스트

```bash
pip install pytest
pytest tests/test_core.py -v
```

9개 테스트가 모두 PASS 해야 합니다.

---

## .exe 빌드법

**1. 의존성 설치:**

```bash
pip install pyinstaller pywinpty
```

**2. 빌드 실행:**

```bash
build.bat
```

빌드 결과물: `dist/AgentsInit.exe`

> **주의:** `build.bat` 은 `--collect-all winpty` 옵션으로 pywinpty 내부 DLL/EXE 바이너리를 자동 수집합니다.
> Windows Defender 등 백신 소프트웨어가 `--onefile` 빌드를 오탐할 수 있습니다.
> 문제가 있으면 `--onedir` 방식으로 전환하거나 코드 서명을 고려하세요.

---

## FAQ

**Q1. "claude CLI 를 찾을 수 없습니다" 메시지가 뜹니다.**

Claude Code CLI 가 설치되어 있지 않거나 PATH 에 등록되지 않은 상태입니다.

설치: [https://docs.claude.com/en/docs/claude-code](https://docs.claude.com/en/docs/claude-code)

설치 후 새 터미널에서 `claude --version` 으로 확인하세요.

**Q2. pywinpty 미설치 메시지가 뜨고 별도 창이 열립니다.**

`pip install pywinpty` 로 설치하면 Claude 세션이 GUI 하단에 직접 표시됩니다.
설치 없이도 기존처럼 별도 cmd 창으로 동작합니다.

**Q3. Gemini / Codex 연동이 안 된다는 경고가 뜹니다.**

`~/.agents-dev/scripts/ask-gemini.sh` 와 `ask-codex.sh` 가 필요합니다.
로그 창에 표시된 경로에 파일이 있는지 확인하고, AI-app-agent 프로젝트 세팅을 먼저 진행해주세요.

**Q4. 초기화 중 "관리자 권한이 필요할 수 있습니다" 메시지가 뜹니다.**

대상 폴더가 쓰기 제한 경로(예: `C:\Program Files\`)에 있습니다.
`C:\Users\...\Documents\` 처럼 일반 사용자 폴더를 선택하세요.

---

## 커스터마이즈

| 바꾸고 싶은 부분 | 수정 위치 |
| --- | --- |
| CLAUDE.md 템플릿 내용 | `agents_gui.py` 의 `CLAUDE_MD_TEMPLATE` 문자열 상수 |
| PTY 터미널 크기 | `_start_pty_session()` 내 `dimensions=(rows, cols)` |
| 추가 초기화 항목 | `init_agents_workspace()` 함수 내 로직 추가 |
| .gitignore 추가 항목 | `_GITIGNORE_ENTRIES` 리스트 |
| Gemini/Codex 스크립트 경로 | `_SCRIPTS_DIR` 상수 |
| 폴백 실행 방식 (VS Code 등) | `launch_claude_session()` 함수 내 `subprocess.Popen` 인자 |
