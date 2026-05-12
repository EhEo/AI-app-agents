# agents-init 터미널 명령을 GUI로 감싸는 Windows 데스크톱 앱 (3-agent 탭 채팅 인터페이스)

from __future__ import annotations

import queue
import re
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

# ── 색상 팔레트 ────────────────────────────────────────────────────────────────
_BG       = "#212121"
_BG_DARK  = "#171717"
_BG_INPUT = "#2f2f2f"
_TEXT     = "#ececec"
_TEXT_DIM = "#8e8ea0"
_GREEN    = "#10a37f"
_BLUE     = "#4285f4"
_PURPLE   = "#8b5cf6"

_SCRIPTS_DIR = Path.home() / ".agents-dev" / "scripts"
_GITIGNORE_ENTRIES = [".agents-dev/log/", ".claude/settings.local.json"]

# ── 마크다운 볼드 패턴 ────────────────────────────────────────────────────────
_MD_BOLD = re.compile(r"\*\*(.+?)\*\*")


def _insert_md(widget: tk.Text, text: str, base_tag: str) -> None:
    """**bold** 패턴을 볼드 태그로 분리 삽입."""
    pos = 0
    bold_tag = base_tag + "_b"
    for m in _MD_BOLD.finditer(text):
        if m.start() > pos:
            widget.insert("end", text[pos:m.start()], base_tag)
        widget.insert("end", m.group(1), bold_tag)
        pos = m.end()
    if pos < len(text):
        widget.insert("end", text[pos:], base_tag)


# ── bash 실행 경로 감지 (Windows) ─────────────────────────────────────────────

def _bash_prefix() -> list[str]:
    """Windows에서 bash 실행 경로를 반환한다. Git Bash → WSL → 기본 순."""
    if sys.platform != "win32":
        return ["bash"]
    bash = shutil.which("bash")
    if bash:
        return [bash]
    if shutil.which("wsl"):
        return ["wsl", "bash"]
    return ["bash"]


def _wsl_path(p: Path) -> str:
    """Windows 절대 경로를 /mnt/드라이브/... 형식으로 변환."""
    s = str(p).replace("\\", "/")
    if len(s) >= 2 and s[1] == ":":
        return f"/mnt/{s[0].lower()}{s[2:]}"
    return s


# ── 도형 유틸 ─────────────────────────────────────────────────────────────────

def _round_rect(cv: tk.Canvas, x1, y1, x2, y2, r, fill, *, tag=None):
    """Canvas 위에 둥근 모서리 사각형을 그린다."""
    kw: dict = {"fill": fill, "outline": fill}
    if tag:
        kw["tags"] = tag
    cv.create_polygon(
        x1+r, y1,   x2-r, y1,
        x2,   y1,   x2,   y1+r,
        x2,   y2-r, x2,   y2,
        x2-r, y2,   x1+r, y2,
        x1,   y2,   x1,   y2-r,
        x1,   y1+r, x1,   y1,
        smooth=True, **kw,
    )


def _darken(hex_color: str, factor: float = 0.80) -> str:
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"


# ── Canvas 기반 둥근 버튼 ─────────────────────────────────────────────────────

class _RoundBtn(tk.Canvas):
    """둥근 모서리 Canvas 버튼."""

    def __init__(self, parent, text: str, command, color: str,
                 radius: int = 10, **kw):
        kw.setdefault("cursor", "hand2")
        outer = parent.cget("bg") if hasattr(parent, "cget") else _BG
        super().__init__(parent, bg=outer, highlightthickness=0, bd=0, **kw)
        self._text = text
        self._color = color
        self._radius = radius
        self._cmd = command
        self.bind("<Configure>", lambda _: self._draw())
        self.bind("<Enter>",     lambda _: self._draw(True))
        self.bind("<Leave>",     lambda _: self._draw(False))
        self.bind("<Button-1>",  lambda _: command())

    def _draw(self, hover: bool = False) -> None:
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4 or h < 4:
            return
        _round_rect(self, 0, 0, w, h, self._radius,
                    _darken(self._color) if hover else self._color)
        self.create_text(w // 2, h // 2, text=self._text, fill="white",
                         font=("맑은 고딕", 9))


# ── Canvas 기반 둥근 입력 바 ──────────────────────────────────────────────────

class _RoundInput(tk.Canvas):
    """Canvas 배경 + Entry + 전송 버튼이 결합된 둥근 입력 위젯."""

    _H    = 54
    _PAD  = 16
    _BTNW = 42
    _PH   = "무엇이든 물어보세요"

    def __init__(self, parent, var: tk.StringVar, on_send,
                 btn_color: str, radius: int = 14):
        outer = parent.cget("bg") if hasattr(parent, "cget") else _BG
        super().__init__(parent, height=self._H, bg=outer,
                         highlightthickness=0, bd=0)
        self._radius = radius
        self._accent = btn_color
        self._on_send = on_send
        self._var = var

        # Entry 위젯
        self.entry = tk.Entry(
            self, textvariable=var, bg=_BG_INPUT, fg=_TEXT_DIM,
            font=("맑은 고딕", 9), relief="flat",
            insertbackground=_TEXT, bd=0, highlightthickness=0,
        )
        self.entry.insert(0, self._PH)
        self.entry.bind("<FocusIn>",  self._focus_in)
        self.entry.bind("<FocusOut>", self._focus_out)
        self.entry.bind("<Return>",   lambda _: on_send())
        self._ew = self.create_window(self._PAD, self._H // 2,
                                      anchor="w", window=self.entry,
                                      width=100, height=self._H - 20)

        # 전송 버튼 (소형 Canvas)
        self._btn = tk.Canvas(self, bg=_BG_INPUT, highlightthickness=0,
                              cursor="hand2")
        self._bw = self.create_window(0, self._H // 2, anchor="center",
                                      window=self._btn,
                                      width=self._BTNW - 4,
                                      height=self._BTNW - 4)
        self._btn.bind("<Configure>", lambda _: self._draw_btn())
        self._btn.bind("<Enter>",     lambda _: self._draw_btn(True))
        self._btn.bind("<Leave>",     lambda _: self._draw_btn(False))
        self._btn.bind("<Button-1>",  lambda _: on_send())

        self.bind("<Configure>", self._redraw)

    # ── 플레이스홀더 ──────────────────────────────────────────────────────────

    def _focus_in(self, _):
        if self._var.get() == self._PH:
            self.entry.delete(0, "end")
            self.entry.config(fg=_TEXT)

    def _focus_out(self, _):
        if not self._var.get():
            self.entry.insert(0, self._PH)
            self.entry.config(fg=_TEXT_DIM)

    # ── 그리기 ────────────────────────────────────────────────────────────────

    def _draw_btn(self, hover: bool = False) -> None:
        c = self._btn
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        if w < 4 or h < 4:
            return
        _round_rect(c, 0, 0, w, h, 8,
                    _darken(self._accent) if hover else self._accent)
        c.create_text(w // 2, h // 2, text="↑", fill="white",
                      font=("맑은 고딕", 10))

    def _redraw(self, event=None) -> None:
        self.delete("bg")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 8 or h < 8:
            return
        _round_rect(self, 0, 0, w, h, self._radius, _BG_INPUT, tag="bg")
        self.tag_lower("bg")
        entry_w = w - self._BTNW - self._PAD * 2 - 10
        self.coords(self._ew, self._PAD, h // 2)
        self.itemconfig(self._ew, width=max(10, entry_w), height=h - 18)
        self.coords(self._bw, w - self._PAD - (self._BTNW - 4) // 2, h // 2)

    def set_sending(self, sending: bool) -> None:
        """전송 중 버튼 색상 변경."""
        self._accent_bak = getattr(self, "_accent_bak", self._accent)
        self._accent = "#555555" if sending else self._accent_bak
        self._draw_btn()


# ── CLAUDE.md 템플릿 ──────────────────────────────────────────────────────────
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

```bash
~/.agents-dev/scripts/ask-gemini.sh "your question"
```

Skip Gemini **only** when the answer is fully verifiable by reading repo files.

---

## Step 4 — Review with Codex (always after completing work)

```bash
~/.agents-dev/scripts/ask-codex.sh
~/.agents-dev/scripts/ask-codex.sh "focus on the auth module"
```

Skip Codex **only** for: single-line typo fixes, doc-only changes, or WIP stubs.

---

## Don't

- Don't skip Gemini because "you already know" — always verify externally before coding.
- Don't skip Codex because the change "looks fine" — always get a second opinion.
- Don't act on `NEEDS-FIX` findings without showing the user first.
"""


# ── 핵심 로직 함수 (GUI 독립 — 테스트 대상) ──────────────────────────────────


def init_agents_workspace(folder: Path) -> list[str]:
    logs: list[str] = []

    log_dir = folder / ".agents-dev" / "log"
    log_dir.mkdir(parents=True, exist_ok=True)
    logs.append(f"[✓] .agents-dev/log/ 생성: {log_dir}")

    # git 저장소 초기화 (Codex git diff HEAD 사용에 필요)
    git_dir = folder / ".git"
    if not git_dir.exists():
        res = subprocess.run(
            ["git", "init"], cwd=str(folder),
            capture_output=True, text=True,
        )
        if res.returncode == 0:
            logs.append("[✓] git init 완료 — Codex 리뷰 준비됨")
        else:
            logs.append(f"[⚠] git init 실패: {res.stderr.strip() or 'git CLI 미설치'}")
    else:
        logs.append("[i] git 저장소 이미 존재")

    claude_md = folder / "CLAUDE.md"
    claude_md.write_text(CLAUDE_MD_TEMPLATE, encoding="utf-8")
    logs.append("[✓] CLAUDE.md 생성 완료")

    gitignore = folder / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    if existing and not existing.endswith("\n"):
        existing += "\n"
    existing_lines = {line.strip() for line in existing.splitlines()}
    added: list[str] = []
    for entry in _GITIGNORE_ENTRIES:
        if entry not in existing_lines:
            existing += f"{entry}\n"
            added.append(entry)
    if added:
        gitignore.write_text(existing, encoding="utf-8")
        logs.append(f"[✓] .gitignore 갱신: {', '.join(added)}")
    else:
        logs.append("[i] .gitignore — 이미 모든 항목 존재")

    for script in ["ask-gemini.sh", "ask-codex.sh"]:
        path = _SCRIPTS_DIR / script
        logs.append(f"[✓] {script} 확인됨" if path.exists()
                    else f"[⚠] {script} 없음 — 필요 경로: {path}")

    return logs


def launch_claude_session(folder: Path, *, dry_run: bool = False) -> bool:
    if shutil.which("claude") is None:
        return False
    if dry_run:
        return True
    try:
        subprocess.Popen(
            ["cmd", "/k", "claude"],
            cwd=str(folder),
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        return True
    except OSError:
        return False


# ── 에이전트 명령 생성 ────────────────────────────────────────────────────────


def _claude_cmd(message: str, *, first: bool, **_) -> list[str]:
    """Windows: cmd /c 로 .cmd 확장자를 자동 해석."""
    base = ["claude", "-p", message]
    if not first:
        base.append("--continue")
    return (["cmd", "/c"] + base) if sys.platform == "win32" else base


def _gemini_cmd(message: str, **_) -> list[str]:
    prefix = _bash_prefix()
    # WSL 사용 시 Windows 경로를 /mnt/... 형식으로 변환
    if prefix == ["wsl", "bash"]:
        script = _wsl_path(_SCRIPTS_DIR / "ask-gemini.sh")
    else:
        script = str(_SCRIPTS_DIR / "ask-gemini.sh")
    return prefix + [script, message]


def _codex_cmd(message: str, **_) -> list[str]:
    prefix = _bash_prefix()
    if prefix == ["wsl", "bash"]:
        script = _wsl_path(_SCRIPTS_DIR / "ask-codex.sh")
    else:
        script = str(_SCRIPTS_DIR / "ask-codex.sh")
    return prefix + [script, message]


# ── AgentTab ──────────────────────────────────────────────────────────────────


class AgentTab:
    """채팅 히스토리 + 입력창을 가진 단일 에이전트 탭."""

    def __init__(self, parent: tk.Frame, name: str, accent: str,
                 cmd_fn, folder_getter) -> None:
        self.name = name
        self.accent = accent
        self._cmd_fn = cmd_fn
        self._folder_getter = folder_getter
        self._queue: queue.Queue[str] = queue.Queue()
        self._running = False
        self._first_msg = True
        self.frame = parent
        self._build()

    def _build(self) -> None:
        # ── 대화 영역 ──────────────────────────────────────────────────────
        chat_outer = tk.Frame(self.frame, bg=_BG)
        chat_outer.pack(fill="both", expand=True)

        self._chat = tk.Text(
            chat_outer, state="disabled", bg=_BG, fg=_TEXT,
            font=("맑은 고딕", 9), wrap="word", relief="flat",
            padx=80, pady=24, spacing3=4, cursor="arrow",
            selectbackground="#404040",
        )
        sb = ttk.Scrollbar(chat_outer, orient="vertical",
                           command=self._chat.yview)
        self._chat.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._chat.pack(side="left", fill="both", expand=True)

        # 태그 — 색상·크기로 구분. 한글 본문은 맑은 고딕으로 글리프 안정성 확보
        self._chat.tag_configure("you_lbl",
            foreground=_TEXT_DIM, font=("맑은 고딕", 8), spacing1=20)
        self._chat.tag_configure("you_msg",
            foreground=_TEXT,     font=("맑은 고딕", 9))
        self._chat.tag_configure("agent_lbl",
            foreground=self.accent, font=("맑은 고딕", 8), spacing1=20)
        self._chat.tag_configure("agent_msg",
            foreground=_TEXT,      font=("맑은 고딕", 9))
        # **bold** 마크다운: 굵기 대신 밝은 색으로 강조 (GDI dark-bg 두꺼움 방지)
        self._chat.tag_configure("agent_msg_b",
            foreground="#ffffff",  font=("맑은 고딕", 9))
        self._chat.tag_configure("system_msg",
            foreground=_TEXT_DIM,  font=("맑은 고딕", 9),
            justify="center", spacing1=6)

        # 빈 화면 플레이스홀더
        self._ph = tk.Label(self._chat, text="어디서부터 시작할까요?",
                            bg=_BG, fg=_TEXT_DIM, font=("맑은 고딕", 11))
        self._ph.place(relx=0.5, rely=0.42, anchor="center")

        # ── 입력 영역 ──────────────────────────────────────────────────────
        input_outer = tk.Frame(self.frame, bg=_BG, pady=14, padx=80)
        input_outer.pack(fill="x")

        self._var = tk.StringVar()
        self._input_bar = _RoundInput(input_outer, self._var,
                                      self._send, self.accent)
        self._input_bar.pack(fill="x")

    # ── 전송 ─────────────────────────────────────────────────────────────────

    def _send(self) -> None:
        msg = self._var.get().strip()
        if not msg or msg == _RoundInput._PH or self._running:
            return
        self._var.set("")
        self._input_bar.entry.config(fg=_TEXT)
        self._ph.place_forget()

        self._append_you(msg)
        self._running = True
        self._input_bar.set_sending(True)

        first = self._first_msg
        self._first_msg = False
        folder = self._folder_getter()

        threading.Thread(
            target=self._worker,
            args=(msg, first, str(folder) if folder else None),
            daemon=True,
        ).start()

    def _worker(self, message: str, first: bool, cwd: str | None) -> None:
        cmd = self._cmd_fn(message, first=first)
        self._queue.put("__START__")
        # Windows: 콘솔 창 깜빡임 없이 백그라운드에서 실행
        no_window = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=cwd,
                **no_window,
            )
            for line in iter(proc.stdout.readline, ""):
                self._queue.put(line)
            proc.wait()
        except FileNotFoundError:
            self._queue.put(
                f"'{cmd[0]}' 를 찾을 수 없습니다.\n"
                "PATH 에 등록되어 있는지 확인하세요.\n"
            )
        except Exception as exc:
            self._queue.put(f"오류: {exc}\n")
        self._queue.put("__DONE__")

    # ── 폴링 (메인 스레드) ───────────────────────────────────────────────────

    def poll(self) -> None:
        try:
            while True:
                msg = self._queue.get_nowait()
                if msg == "__START__":
                    self._chat.configure(state="normal")
                    self._chat.insert("end", f"\n{self.name}\n", "agent_lbl")
                    self._chat.configure(state="disabled")
                elif msg == "__DONE__":
                    self._running = False
                    self._input_bar.set_sending(False)
                    self._chat.configure(state="normal")
                    self._chat.insert("end", "\n")
                    self._chat.configure(state="disabled")
                else:
                    self._chat.configure(state="normal")
                    _insert_md(self._chat, msg, "agent_msg")
                    self._chat.see("end")
                    self._chat.configure(state="disabled")
        except queue.Empty:
            pass

    # ── 헬퍼 ─────────────────────────────────────────────────────────────────

    def _append_you(self, msg: str) -> None:
        self._chat.configure(state="normal")
        self._chat.insert("end", "\nYou\n", "you_lbl")
        self._chat.insert("end", f"{msg}\n", "you_msg")
        self._chat.see("end")
        self._chat.configure(state="disabled")

    def append_system(self, msg: str) -> None:
        self._chat.configure(state="normal")
        self._chat.insert("end", f"{msg}\n", "system_msg")
        self._chat.see("end")
        self._chat.configure(state="disabled")

    def focus_input(self) -> None:
        self._input_bar.entry.focus()


# ── AgentsGUI ─────────────────────────────────────────────────────────────────


class AgentsGUI(tk.Tk):
    """Agents Init Launcher — 3-agent 탭 채팅 인터페이스."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Agents Init Launcher")
        self.configure(bg=_BG)
        self.minsize(860, 660)
        self.resizable(True, True)

        self._folder: Path | None = None
        self._log_queue: queue.Queue[str] = queue.Queue()
        self._init_thread: threading.Thread | None = None

        self._build_ui()
        self._poll_all()
        self._style_titlebar()

    def _style_titlebar(self) -> None:
        """네이티브 타이틀바를 앱 배경색과 통일 (Windows 10+ DWM)."""
        if sys.platform != "win32":
            return
        try:
            import ctypes
            self.update_idletasks()
            hwnd = ctypes.windll.user32.FindWindowW(None, "Agents Init Launcher")
            if not hwnd:
                return
            # DWMWA_USE_IMMERSIVE_DARK_MODE (20) — Windows 10 20H1+
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 20, ctypes.byref(ctypes.c_int(1)), 4
            )
            # DWMWA_CAPTION_COLOR (35) — Windows 11 22000+
            # #212121 → COLORREF 0x00212121
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 35, ctypes.byref(ctypes.c_int(0x00212121)), 4
            )
        except Exception:
            pass

    def _build_ui(self) -> None:
        self._build_topbar()
        self._build_notebook()

    # ── 탑바 ──────────────────────────────────────────────────────────────────

    def _build_topbar(self) -> None:
        bar = tk.Frame(self, bg=_BG_DARK, pady=10)
        bar.pack(fill="x")

        # 폴더 박스 (클릭 → 폴더 선택)
        folder_box = tk.Frame(bar, bg=_BG_INPUT, padx=12)
        folder_box.pack(side="left", fill="x", expand=True, padx=(16, 10), ipady=8)

        tk.Label(folder_box, text="📁", bg=_BG_INPUT,
                 fg=_TEXT_DIM, font=("맑은 고딕", 9)).pack(side="left")

        self._folder_var = tk.StringVar(value="폴더를 선택하세요...")
        lbl = tk.Label(folder_box, textvariable=self._folder_var,
                       bg=_BG_INPUT, fg=_TEXT_DIM,
                       font=("맑은 고딕", 9), anchor="w", cursor="hand2")
        lbl.pack(side="left", fill="x", expand=True, padx=(6, 0))

        for w in (folder_box, lbl):
            w.bind("<Button-1>", lambda _: self._select_folder())

        # 폴더 열기 버튼
        self._open_btn = _RoundBtn(
            bar, "📂  폴더 열기", self._open_folder, "#555555",
            radius=10, width=110, height=40,
        )
        self._open_btn.pack(side="right", padx=(0, 8))

        # 초기화 실행 버튼
        self._run_btn = _RoundBtn(
            bar, "🚀  초기화 + 실행", self._run_init, _GREEN,
            radius=10, width=160, height=40,
        )
        self._run_btn.pack(side="right", padx=(0, 8))

    # ── Notebook ──────────────────────────────────────────────────────────────

    def _build_notebook(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Dark.TNotebook",
                        background=_BG_DARK, borderwidth=0,
                        tabmargins=[0, 0, 0, 0])
        style.configure("Dark.TNotebook.Tab",
                        background=_BG_DARK, foreground=_TEXT_DIM,
                        padding=[20, 10], font=("맑은 고딕", 9), borderwidth=0)
        style.map("Dark.TNotebook.Tab",
                  background=[("selected", _BG), ("active", "#262626")],
                  foreground=[("selected", _TEXT), ("active", _TEXT)])
        style.configure("Vertical.TScrollbar",
                        background=_BG_INPUT, troughcolor=_BG,
                        borderwidth=0, arrowsize=0)

        self._nb = ttk.Notebook(self, style="Dark.TNotebook")
        self._nb.pack(fill="both", expand=True)

        claude_f = tk.Frame(self._nb, bg=_BG)
        gemini_f = tk.Frame(self._nb, bg=_BG)
        codex_f  = tk.Frame(self._nb, bg=_BG)
        init_f   = tk.Frame(self._nb, bg=_BG)

        self._nb.add(claude_f, text="  🤖 Claude  ")
        self._nb.add(gemini_f, text="  🔬 Gemini  ")
        self._nb.add(codex_f,  text="  📝 Codex  ")
        self._nb.add(init_f,   text="  📋 초기화  ")

        getter = lambda: self._folder
        self._tabs = [
            AgentTab(claude_f, "Claude", _GREEN,  _claude_cmd, getter),
            AgentTab(gemini_f, "Gemini", _BLUE,   _gemini_cmd, getter),
            AgentTab(codex_f,  "Codex",  _PURPLE, _codex_cmd,  getter),
        ]
        self._build_init_tab(init_f)

    def _build_init_tab(self, frame: tk.Frame) -> None:
        tk.Frame(frame, bg=_BG, height=12).pack()
        tk.Label(frame, text="초기화 로그", bg=_BG, fg=_TEXT_DIM,
                 font=("맑은 고딕", 9), anchor="w"
                 ).pack(fill="x", padx=20, pady=(0, 4))

        outer = tk.Frame(frame, bg=_BG)
        outer.pack(fill="both", expand=True)

        self._log = tk.Text(outer, state="disabled", bg=_BG, fg=_TEXT,
                            font=("맑은 고딕", 9), relief="flat",
                            padx=20, pady=10, cursor="arrow",
                            selectbackground="#404040")
        sb = ttk.Scrollbar(outer, orient="vertical", command=self._log.yview)
        self._log.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._log.pack(side="left", fill="both", expand=True)

        self._log.tag_configure("ok",   foreground=_GREEN)
        self._log.tag_configure("warn", foreground="#f59e0b")
        self._log.tag_configure("err",  foreground="#ef4444")
        self._log.tag_configure("info", foreground=_TEXT_DIM)
        self._log.tag_configure("sep",  foreground="#404040")

    # ── 이벤트 ────────────────────────────────────────────────────────────────

    def _select_folder(self) -> None:
        path = filedialog.askdirectory(title="프로젝트 폴더 선택")
        if path:
            self._folder = Path(path)
            disp = str(self._folder)
            if len(disp) > 72:
                disp = "..." + disp[-69:]
            self._folder_var.set(disp)

    def _open_folder(self) -> None:
        if self._folder is None:
            messagebox.showwarning("폴더 미선택", "먼저 폴더를 선택해주세요.")
            return
        if sys.platform == "win32":
            subprocess.Popen(["explorer", str(self._folder)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(self._folder)])
        else:
            subprocess.Popen(["xdg-open", str(self._folder)])

    def _run_init(self) -> None:
        if self._folder is None:
            messagebox.showwarning("폴더 미선택", "먼저 폴더를 선택해주세요.")
            return
        if self._init_thread and self._init_thread.is_alive():
            return
        self._nb.select(3)
        self._clear_log()
        self._init_thread = threading.Thread(
            target=self._init_worker, daemon=True
        )
        self._init_thread.start()

    def _init_worker(self) -> None:
        try:
            for line in init_agents_workspace(self._folder):
                self._log_queue.put(line)
            self._log_queue.put("─" * 58)
            self._log_queue.put("[✓] 초기화 완료. Claude 탭에서 대화를 시작하세요.")
            self._log_queue.put("__SWITCH__")
        except PermissionError:
            self._log_queue.put("[✗] 권한 부족 — 쓰기 권한이 있는 폴더를 선택하세요.")
        except Exception as exc:
            self._log_queue.put(f"[✗] 오류: {exc}")

    # ── 통합 폴링 ─────────────────────────────────────────────────────────────

    def _poll_all(self) -> None:
        try:
            while True:
                msg = self._log_queue.get_nowait()
                if msg == "__SWITCH__":
                    self.after(1200, self._switch_to_claude)
                else:
                    self._append_log(msg)
        except queue.Empty:
            pass

        for tab in self._tabs:
            tab.poll()

        self.after(80, self._poll_all)

    def _switch_to_claude(self) -> None:
        self._nb.select(0)
        if self._folder:
            self._tabs[0].append_system(
                f"📁 {self._folder.name}  |  초기화 완료"
            )
        self._tabs[0].focus_input()

    # ── 로그 헬퍼 ─────────────────────────────────────────────────────────────

    def _append_log(self, msg: str) -> None:
        tag = ("ok"   if msg.startswith("[✓]") else
               "warn" if msg.startswith(("[⚠]", "[i]")) else
               "err"  if msg.startswith("[✗]") else
               "sep"  if set(msg.strip()) <= {"─"} else "info")
        self._log.configure(state="normal")
        self._log.insert("end", msg + "\n", tag)
        self._log.see("end")
        self._log.configure(state="disabled")

    def _clear_log(self) -> None:
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")


# ── 진입점 ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = AgentsGUI()
    app.mainloop()
