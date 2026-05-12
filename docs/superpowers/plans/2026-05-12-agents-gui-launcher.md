# Agents GUI Launcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `agents_gui.py` 단일 파일 Tkinter 앱으로 agents-init 터미널 흐름을 GUI로 감싸고, README.md + build.bat 를 함께 제공한다.

**Architecture:** 순수 로직 함수(`init_agents_workspace`, `launch_claude_session`)를 GUI 클래스와 완전히 분리. threading.Thread + queue.Queue 패턴으로 GUI freeze 방지. CLAUDE_MD_TEMPLATE 상수를 스크립트 내부에 보관.

**Tech Stack:** Python 3.11+, tkinter, pathlib, threading, queue, subprocess, shutil (모두 표준 라이브러리)

---

## 파일 맵

| 파일 | 역할 |
|---|---|
| `agents_gui.py` | 단일 파일 앱 (GUI + 로직 + 템플릿 상수) |
| `README.md` | 설치 / 실행 / 빌드 / FAQ / 커스터마이즈 |
| `build.bat` | PyInstaller .exe 빌드 1줄 스크립트 |
| `tests/test_core.py` | 순수 로직 함수 단위 테스트 |

---

### Task 1: Gemini 리서치 — Tkinter + threading + subprocess Windows 베스트 프랙티스

**Files:** (로그 파일만)

- [ ] **Step 1: Gemini에 Tkinter threading 패턴 질문**

```bash
~/.agents-dev/scripts/ask-gemini.sh "Python Tkinter GUI app on Windows: best practices for (1) threading with queue.Queue to update text widget without freeze, (2) subprocess.Popen to open new cmd window and run a command, (3) pyinstaller --onefile --windowed packaging. List any known pitfalls on Windows 11."
```

- [ ] **Step 2: Gemini 응답 요약 후 계속 진행**

---

### Task 2: 테스트 파일 스캐폴딩

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_core.py`

- [ ] **Step 1: tests 폴더 및 빈 __init__.py 생성**

```bash
mkdir tests && touch tests/__init__.py
```

- [ ] **Step 2: 실패하는 테스트 작성**

`tests/test_core.py`:

```python
# agents_gui 핵심 로직 함수에 대한 단위 테스트
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from pathlib import Path
import tempfile
import shutil


# ── init_agents_workspace 테스트 ──────────────────────────────


def test_creates_agents_dev_log_dir(tmp_path):
    """빈 폴더에서 초기화하면 .agents-dev/log/ 가 생성된다."""
    from agents_gui import init_agents_workspace
    init_agents_workspace(tmp_path)
    assert (tmp_path / ".agents-dev" / "log").is_dir()


def test_creates_claude_md(tmp_path):
    """CLAUDE.md 파일이 생성된다."""
    from agents_gui import init_agents_workspace
    init_agents_workspace(tmp_path)
    assert (tmp_path / "CLAUDE.md").exists()


def test_claude_md_not_empty(tmp_path):
    """생성된 CLAUDE.md 는 비어 있지 않다."""
    from agents_gui import init_agents_workspace
    init_agents_workspace(tmp_path)
    content = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert len(content) > 100


def test_gitignore_entries_added(tmp_path):
    """.gitignore 에 두 항목이 추가된다."""
    from agents_gui import init_agents_workspace
    init_agents_workspace(tmp_path)
    text = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert ".agents-dev/log/" in text
    assert ".claude/settings.local.json" in text


def test_gitignore_no_duplicate(tmp_path):
    """같은 항목이 이미 있으면 중복 추가하지 않는다."""
    from agents_gui import init_agents_workspace
    existing = ".agents-dev/log/\n.claude/settings.local.json\n"
    (tmp_path / ".gitignore").write_text(existing, encoding="utf-8")
    init_agents_workspace(tmp_path)
    text = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert text.count(".agents-dev/log/") == 1
    assert text.count(".claude/settings.local.json") == 1


def test_returns_log_lines(tmp_path):
    """반환값은 비어 있지 않은 문자열 리스트다."""
    from agents_gui import init_agents_workspace
    logs = init_agents_workspace(tmp_path)
    assert isinstance(logs, list)
    assert len(logs) > 0
    assert all(isinstance(line, str) for line in logs)


def test_already_initialized_returns_warning(tmp_path):
    """이미 초기화된 폴더에서 호출하면 로그에 경고 문자열이 포함된다."""
    from agents_gui import init_agents_workspace
    init_agents_workspace(tmp_path)
    # 두 번째 호출 — GUI에서 사용자가 확인창에서 '예'를 눌렀다고 가정
    logs = init_agents_workspace(tmp_path)
    combined = " ".join(logs).lower()
    assert "백업" in combined or "backup" in combined or "이미" in combined or "already" in combined


# ── launch_claude_session 테스트 ─────────────────────────────


def test_launch_returns_false_for_missing_claude(tmp_path, monkeypatch):
    """claude CLI 가 없을 때 False 를 반환한다."""
    from agents_gui import launch_claude_session
    # PATH 에서 claude 를 찾을 수 없도록 monkeypatch
    monkeypatch.setenv("PATH", "")
    result = launch_claude_session(tmp_path, dry_run=True)
    assert result is False
```

- [ ] **Step 3: 테스트가 실패하는지 확인**

```bash
cd "c:/Users/MISTOP/Documents/02_AI디지털전환/AI-app-agent" && python -m pytest tests/test_core.py -v 2>&1 | head -30
```

Expected: `ImportError` 또는 `ModuleNotFoundError` — agents_gui.py 가 아직 없으므로 정상.

---

### Task 3: 핵심 로직 구현 — `agents_gui.py` (로직 함수 + 상수)

**Files:**
- Create: `agents_gui.py`

- [ ] **Step 1: 파일 스캐폴딩 — CLAUDE_MD_TEMPLATE 상수 + 로직 두 함수**

`agents_gui.py` 전체 내용 (GUI 클래스 제외, 상수 + 로직만):

```python
# agents-init 터미널 명령을 GUI로 감싸는 Windows 데스크톱 앱
"""
실행법:
    python agents_gui.py

PyInstaller 빌드:
    pyinstaller --onefile --windowed --name AgentsInit agents_gui.py
"""

from __future__ import annotations

import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext


# ── CLAUDE.md 템플릿 (3-agent 오케스트레이션 정책) ──────────────────
CLAUDE_MD_TEMPLATE = """\
# CLAUDE.md — orchestration policy

You are the **PM + Coder** in a mandatory 3-agent team. Every non-trivial task follows the loop below — no shortcuts.

| Role | Invocation |
|---|---|
| **PM + Coder** (you) | this session |
| **Researcher** (Gemini) | `~/.agents-dev/scripts/ask-gemini.sh "question"` |
| **Reviewer** (Codex) | `~/.agents-dev/scripts/ask-codex.sh "focus"` |

## Standard workflow — always follow this order

```text
1. PLAN      — break the task into steps; identify what is uncertain
2. RESEARCH  — call Gemini for anything involving external knowledge
3. CODE      — implement based on the research result
4. REVIEW    — call Codex after every logical unit of work
5. FIX       — address blockers/major findings; re-review if significant
6. REPORT    — tell the user: verdict + key findings + log paths
```

This is not optional. Do not skip steps 2 or 4.

---

## Step 2 — Research with Gemini (always before coding)

Call Gemini **before writing code** whenever the task involves:

- Any library, framework, or API — even ones you think you know
- Recent changes, deprecations, or version constraints
- Design trade-offs between multiple approaches
- Spec, RFC, or protocol details

```bash
~/.agents-dev/scripts/ask-gemini.sh "your question"

# with context piped in
echo "$RELEVANT_CODE" | ~/.agents-dev/scripts/ask-gemini.sh "question about this code"
```

Skip Gemini **only** when the answer is fully verifiable by reading repo files or running `grep`. If there is any doubt, ask.

---

## Step 4 — Review with Codex (always after completing work)

Call Codex after **every** logical unit of completed work:

- After implementing a feature or bug fix
- After any refactor touching more than one file
- Before committing

```bash
# full working-tree review (default)
~/.agents-dev/scripts/ask-codex.sh

# scoped review
~/.agents-dev/scripts/ask-codex.sh "focus on the auth module"

# with Gemini research attached
~/.agents-dev/scripts/ask-codex.sh --with-research .agents-dev/log/research-<ts>.md "focus"
```

Skip Codex **only** for: single-line typo fixes, doc-only changes (no code), or WIP stubs mid-feature that are not yet runnable.

---

## Handling Codex's `NEED RESEARCH`

If Codex output contains a `## NEED RESEARCH` block:

1. Run `ask-gemini.sh` for each question; capture the answers.
2. Save combined answers to `.agents-dev/log/research-<ts>.md`.
3. Re-invoke: `ask-codex.sh --with-research <file> "<original focus>"`.
4. Surface blockers / major findings to the user before continuing.

---

## Routing rules

- You are the **central router** — Codex and Gemini never communicate directly.
- When Codex raises NEED RESEARCH, relay it to Gemini and bring the answer back.
- Never act on a NEEDS-FIX verdict without showing the user first.

---

## Reporting to the user

- After research: summarize Gemini's key points in 2–4 lines + cite the log path.
- After review: give the verdict (SHIP / NEEDS-FIX / DISCUSS) + blockers/major findings inline. Link the full log; do not dump the entire output.
- Logs live in `.agents-dev/log/` (gitignored).

---

## Don't

- Don't skip Gemini because "you already know" — always verify externally before coding.
- Don't skip Codex because the change "looks fine" — always get a second opinion.
- Don't call Gemini / Codex from inside an `Agent` subagent — keep orchestration in the main session so the user sees the routing.
- Don't act on `NEEDS-FIX` findings without showing the user first.
- Don't paste secrets / credentials into prompts (both CLIs send to external providers).
"""

# ask-gemini.sh / ask-codex.sh 예상 위치
_SCRIPTS_DIR = Path.home() / ".agents-dev" / "scripts"
_REQUIRED_SCRIPTS = ["ask-gemini.sh", "ask-codex.sh"]

# .gitignore 에 추가할 항목
_GITIGNORE_ENTRIES = [
    ".agents-dev/log/",
    ".claude/settings.local.json",
]


def init_agents_workspace(folder: Path) -> list[str]:
    """
    선택한 폴더에 agents-dev 워크스페이스를 초기화한다.

    동작:
      (a) .agents-dev/log/ 폴더 생성
      (b) CLAUDE.md 생성 (기존 파일 있으면 .bak 백업 후 덮어씀)
      (c) .gitignore 에 누락된 항목 추가 (중복 방지)
      (d) ask-gemini.sh / ask-codex.sh 존재 확인

    Returns:
        진행 로그 라인 리스트
    """
    logs: list[str] = []

    # (a) .agents-dev/log/ 생성
    log_dir = folder / ".agents-dev" / "log"
    log_dir.mkdir(parents=True, exist_ok=True)
    logs.append(f"[✓] .agents-dev/log/ 생성: {log_dir}")

    # (b) CLAUDE.md 생성
    claude_md = folder / "CLAUDE.md"
    if claude_md.exists():
        bak = folder / "CLAUDE.md.bak"
        shutil.copy2(claude_md, bak)
        logs.append(f"[i] 기존 CLAUDE.md 백업: {bak}")
    claude_md.write_text(CLAUDE_MD_TEMPLATE, encoding="utf-8")
    logs.append(f"[✓] CLAUDE.md 생성 완료")

    # (c) .gitignore 갱신
    gitignore = folder / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    added: list[str] = []
    for entry in _GITIGNORE_ENTRIES:
        if entry not in existing:
            existing += f"\n{entry}"
            added.append(entry)
    if added:
        gitignore.write_text(existing.lstrip("\n"), encoding="utf-8")
        logs.append(f"[✓] .gitignore 갱신: {', '.join(added)}")
    else:
        logs.append("[i] .gitignore — 이미 모든 항목 존재, 변경 없음")

    # (d) 스크립트 존재 확인
    for script in _REQUIRED_SCRIPTS:
        path = _SCRIPTS_DIR / script
        if path.exists():
            logs.append(f"[✓] {script} 확인됨")
        else:
            logs.append(
                f"[⚠] {script} 없음 — 설치 필요: ~/.agents-dev/scripts/{script}"
            )

    return logs


def launch_claude_session(folder: Path, *, dry_run: bool = False) -> bool:
    """
    선택한 폴더에서 새 cmd 창으로 claude 세션을 실행한다.

    Args:
        folder: 작업 폴더 경로
        dry_run: True 이면 실제 프로세스를 생성하지 않음 (테스트용)

    Returns:
        성공 여부 (bool)
    """
    if shutil.which("claude") is None:
        return False
    if dry_run:
        return False  # 테스트용 — claude 없는 환경에서 False 반환
    try:
        subprocess.Popen(
            f'start cmd /k "cd /d "{folder}" && claude"',
            shell=True,
        )
        return True
    except OSError:
        return False
```

- [ ] **Step 2: 테스트 실행 — 로직 함수 통과 확인**

```bash
cd "c:/Users/MISTOP/Documents/02_AI디지털전환/AI-app-agent" && python -m pytest tests/test_core.py -v
```

Expected: 7개 테스트 모두 PASS (launch 테스트는 dry_run 분기 사용).

---

### Task 4: GUI 클래스 추가 — `agents_gui.py` 하단에 append

**Files:**
- Modify: `agents_gui.py` (AgentsGUI 클래스 + main 블록 추가)

- [ ] **Step 1: AgentsGUI 클래스 append**

`agents_gui.py` 끝에 다음 코드 추가:

```python
# ── GUI ──────────────────────────────────────────────────────


class AgentsGUI(tk.Tk):
    """Agents Init Launcher 메인 윈도우."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Agents Init Launcher")
        self.resizable(True, True)
        self.minsize(560, 420)
        self._folder: Path | None = None
        self._log_queue: queue.Queue[str] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._build_ui()
        self._poll_log_queue()

    # ── UI 구성 ──────────────────────────────────────────────

    def _build_ui(self) -> None:
        pad = {"padx": 10, "pady": 5}

        # 상단: 폴더 선택
        top = tk.Frame(self)
        top.pack(fill="x", **pad)
        self._folder_var = tk.StringVar(value="폴더를 선택하세요...")
        tk.Label(top, textvariable=self._folder_var, anchor="w",
                 relief="sunken", width=50).pack(side="left", fill="x", expand=True)
        tk.Button(top, text="폴더 선택", command=self._select_folder,
                  width=10).pack(side="left", padx=(5, 0))

        # 중앙: 메인 버튼
        tk.Button(
            self,
            text="🚀  Agents 초기화 + Claude 실행",
            command=self._run_init,
            font=("맑은 고딕", 13, "bold"),
            bg="#0078d4",
            fg="white",
            activebackground="#005a9e",
            activeforeground="white",
            height=2,
            cursor="hand2",
        ).pack(fill="x", padx=20, pady=(10, 5))

        # 로그 영역
        tk.Label(self, text="진행 로그", anchor="w").pack(fill="x", padx=10)
        self._log_box = scrolledtext.ScrolledText(
            self, state="disabled", height=14,
            font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4",
        )
        self._log_box.pack(fill="both", expand=True, padx=10, pady=(0, 5))

        # 상태 표시줄
        self._status_var = tk.StringVar(value="상태: 준비됨")
        tk.Label(self, textvariable=self._status_var, anchor="w",
                 relief="sunken").pack(fill="x", side="bottom")

    # ── 이벤트 핸들러 ────────────────────────────────────────

    def _select_folder(self) -> None:
        path = filedialog.askdirectory(title="프로젝트 폴더 선택")
        if path:
            self._folder = Path(path)
            self._folder_var.set(str(self._folder))
            self._set_status("준비됨")

    def _run_init(self) -> None:
        if self._folder is None:
            messagebox.showwarning("폴더 미선택", "먼저 폴더를 선택해주세요.")
            return

        # 이미 초기화된 폴더 확인
        if (self._folder / ".agents-dev").exists():
            if not messagebox.askyesno(
                "이미 초기화됨",
                f"{self._folder}\n\n이미 초기화된 폴더입니다. 다시 진행하시겠습니까?\n"
                "(기존 CLAUDE.md 는 .bak 으로 백업됩니다)",
            ):
                return

        # 실행 중 버튼 비활성화 방지 경쟁 조건 차단
        if self._worker and self._worker.is_alive():
            return

        self._clear_log()
        self._set_status("초기화 중...")
        self._worker = threading.Thread(
            target=self._worker_fn, daemon=True
        )
        self._worker.start()

    # ── 백그라운드 작업 ──────────────────────────────────────

    def _worker_fn(self) -> None:
        folder = self._folder
        assert folder is not None

        try:
            logs = init_agents_workspace(folder)
            for line in logs:
                self._log_queue.put(line)

            # Claude 실행
            self._log_queue.put("─" * 50)
            if launch_claude_session(folder):
                self._log_queue.put("[✓] Claude 세션 시작 — 새 cmd 창을 확인하세요.")
                self._log_queue.put("__STATUS__완료 ✓")
            else:
                if not shutil.which("claude"):
                    self._log_queue.put(
                        "[⚠] claude CLI 를 찾을 수 없습니다.\n"
                        "    설치: https://docs.claude.com/en/docs/claude-code"
                    )
                self._log_queue.put("__STATUS__초기화 완료 (Claude 실행 실패)")

        except PermissionError:
            self._log_queue.put("[✗] 권한 부족 — 관리자 권한이 필요할 수 있습니다.")
            self._log_queue.put("__STATUS__오류 발생")
        except Exception as exc:  # noqa: BLE001
            self._log_queue.put(f"[✗] 오류: {exc}")
            self._log_queue.put("__STATUS__오류 발생")

    # ── 로그 큐 폴링 ─────────────────────────────────────────

    def _poll_log_queue(self) -> None:
        try:
            while True:
                msg = self._log_queue.get_nowait()
                if msg.startswith("__STATUS__"):
                    self._set_status(msg[len("__STATUS__"):])
                else:
                    self._append_log(msg)
        except queue.Empty:
            pass
        self.after(80, self._poll_log_queue)

    # ── 헬퍼 ─────────────────────────────────────────────────

    def _append_log(self, msg: str) -> None:
        self._log_box.configure(state="normal")
        self._log_box.insert("end", msg + "\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _clear_log(self) -> None:
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")

    def _set_status(self, msg: str) -> None:
        self._status_var.set(f"상태: {msg}")


# ── 진입점 ────────────────────────────────────────────────────

if __name__ == "__main__":
    app = AgentsGUI()
    app.mainloop()
```

- [ ] **Step 2: 테스트 재실행 — 전체 통과 확인**

```bash
cd "c:/Users/MISTOP/Documents/02_AI디지털전환/AI-app-agent" && python -m pytest tests/test_core.py -v
```

Expected: 7개 모두 PASS.

- [ ] **Step 3: GUI 임포트 오류 없는지 확인 (headless)**

```bash
cd "c:/Users/MISTOP/Documents/02_AI디지털전환/AI-app-agent" && python -c "import agents_gui; print('임포트 OK')"
```

Expected: `임포트 OK`

---

### Task 5: Codex 1차 리뷰 — 로직 + GUI

- [ ] **Step 1: Codex 리뷰 실행**

```bash
~/.agents-dev/scripts/ask-codex.sh "Review agents_gui.py: focus on (1) thread safety — are all Tk widget updates happening on the main thread via queue? (2) edge cases in init_agents_workspace — path encoding, existing .gitignore without trailing newline, (3) launch_claude_session Windows quoting correctness"
```

- [ ] **Step 2: NEEDS-FIX 항목 수정 후 테스트 재실행**

수정 후: `python -m pytest tests/test_core.py -v`

---

### Task 6: README.md 작성

**Files:**
- Create: `README.md`

- [ ] **Step 1: README.md 작성**

```markdown
# Agents Init Launcher

`agents-init` 터미널 명령을 GUI로 감싼 Windows 데스크톱 앱.

폴더 선택 → 버튼 클릭 한 번으로:
1. `.agents-dev/log/` 폴더 생성
2. `CLAUDE.md` (3-agent 오케스트레이션 템플릿) 배치
3. `.gitignore` 자동 갱신
4. Claude Code 세션 자동 시작

---

## 실행법

### 방법 1: Python 직접 실행 (개발용)

**사전 요구사항:**
- Python 3.11+
- `claude` CLI 설치 ([설치 안내](https://docs.claude.com/en/docs/claude-code))
- `~/.agents-dev/scripts/ask-gemini.sh`, `ask-codex.sh` 존재

```bash
python agents_gui.py
```

### 방법 2: .exe 더블클릭 (배포용)

`dist/AgentsInit.exe` 를 더블클릭.

---

## .exe 빌드법

```bash
pip install pyinstaller
build.bat
```

빌드 결과물: `dist/AgentsInit.exe`

---

## FAQ

**Q1. "claude CLI 를 찾을 수 없습니다" 메시지가 뜹니다.**
A. Claude Code CLI 가 설치되어 있지 않거나 PATH 에 등록되지 않은 상태입니다.
   설치: https://docs.claude.com/en/docs/claude-code
   설치 후 터미널에서 `claude --version` 으로 확인하세요.

**Q2. Gemini / Codex 연동이 되지 않습니다.**
A. `~/.agents-dev/scripts/ask-gemini.sh` 와 `ask-codex.sh` 가 필요합니다.
   이 파일들은 `AI-app-agent` 프로젝트의 세팅 과정에서 생성됩니다.
   로그 창에서 경로 경고를 확인하세요.

**Q3. 초기화 중 "관리자 권한이 필요할 수 있습니다" 메시지가 뜹니다.**
A. 대상 폴더가 쓰기 제한 경로(예: C:\Program Files\)에 있습니다.
   일반 사용자 홈 디렉터리(예: C:\Users\...\Documents\)에 있는 폴더를 선택하세요.

---

## 커스터마이즈

| 바꾸고 싶은 부분 | 수정 위치 |
|---|---|
| CLAUDE.md 템플릿 내용 | `agents_gui.py` 의 `CLAUDE_MD_TEMPLATE` 상수 |
| Claude 실행 방식 (예: WSL, VS Code) | `launch_claude_session()` 함수 내 `subprocess.Popen` 명령 |
| 추가 초기화 항목 | `init_agents_workspace()` 함수 내 로직 추가 |
| .gitignore 추가 항목 | `_GITIGNORE_ENTRIES` 리스트 |
| Gemini/Codex 스크립트 경로 | `_SCRIPTS_DIR` 상수 |
```

---

### Task 7: build.bat 작성

**Files:**
- Create: `build.bat`

- [ ] **Step 1: build.bat 작성**

```bat
@echo off
pyinstaller --onefile --windowed --name AgentsInit agents_gui.py
```

---

### Task 8: Codex 최종 리뷰

- [ ] **Step 1: 전체 파일 최종 리뷰**

```bash
~/.agents-dev/scripts/ask-codex.sh "Final review of agents_gui.py, README.md, build.bat: check for (1) any remaining bugs, (2) README accuracy — do all described paths/commands actually match the code?, (3) build.bat correctness"
```

- [ ] **Step 2: 최종 판정 사용자에게 보고**
