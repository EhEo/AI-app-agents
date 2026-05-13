# agents-init 터미널 명령을 GUI로 감싸는 Windows 데스크톱 앱 (3-agent 탭 채팅 인터페이스)

from __future__ import annotations

import json
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

# ── 색상 팔레트 ────────────────────────────────────────────────────────────────
_BG       = "#212121"
_BG_DARK  = "#171717"
_BG_INPUT = "#2f2f2f"
_TEXT     = "#ececec"
_TEXT_DIM = "#8e8ea0"
_GREEN    = "#10a37f"
_BLUE     = "#4285f4"
_PURPLE   = "#8b5cf6"
_FONT_KO  = "맑은 고딕"   # 감지된 한글 폰트로 __init__ 에서 교체됨

_PALETTES = {
    "dark":  dict(BG="#212121", BG_DARK="#171717", BG_INPUT="#2f2f2f",
                  TEXT="#ececec", TEXT_DIM="#8e8ea0"),
    "light": dict(BG="#f7f7f8", BG_DARK="#efefef", BG_INPUT="#e8e8ec",
                  TEXT="#111111", TEXT_DIM="#6b6b80"),
}
_THEME = "dark"
_STATUS_FRAMES = ["◐", "◓", "◑", "◒"]   # 회전 스피너 프레임
_STATUS_LABELS = {
    "Claude": "Claude 응답중",
    "Gemini": "Gemini 조회중",
    "Codex":  "Codex 검토중",
}


def _apply_palette(name: str) -> None:
    global _BG, _BG_DARK, _BG_INPUT, _TEXT, _TEXT_DIM, _THEME
    p = _PALETTES[name]
    _BG, _BG_DARK, _BG_INPUT, _TEXT, _TEXT_DIM = (
        p["BG"], p["BG_DARK"], p["BG_INPUT"], p["TEXT"], p["TEXT_DIM"]
    )
    _THEME = name


_SCRIPTS_DIR    = Path.home() / ".agents-dev" / "scripts"
_PROJECTS_FILE  = Path.home() / ".agents-dev" / "projects.json"
_GITIGNORE_ENTRIES = [".agents-dev/log/", ".claude/settings.local.json"]


def _load_projects() -> tuple[Path | None, list[dict]]:
    """저장된 기본 폴더와 프로젝트 목록을 반환한다."""
    try:
        if _PROJECTS_FILE.exists():
            data = json.loads(_PROJECTS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                # 구버전 형식 호환 (기본 폴더 없는 평탄 배열)
                return None, [p for p in data if "name" in p and "path" in p]
            base_str = data.get("base")
            base = Path(base_str) if base_str else None
            projects = [p for p in data.get("projects", [])
                        if "name" in p and "path" in p]
            return base, projects
    except Exception:
        pass
    return None, []


def _save_projects(base_folder: Path | None, projects: list[dict]) -> None:
    _PROJECTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {"projects": projects}
    if base_folder:
        data["base"] = str(base_folder)
    _PROJECTS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

# ── 마크다운 렌더링 패턴 ─────────────────────────────────────────────────────
_MD_BOLD   = re.compile(r"\*\*(.+?)\*\*")
_MD_FENCE  = re.compile(r"^```")
_MD_HEAD   = re.compile(r"^(#{1,3})\s+(.*)")
_MD_BLIST  = re.compile(r"^[ \t]*[-*+]\s+(.*)")
_MD_NLIST  = re.compile(r"^[ \t]*(\d+)\.\s+(.*)")
_MD_HR_PAT = re.compile(r"^[-*_]{3,}\s*$")
_CODE_FONT = "Consolas"

_INL_PATS: "list[tuple[str, re.Pattern[str]]]" = [
    ("md_b_i",    re.compile(r"\*{3}(.+?)\*{3}")),
    ("md_bold",   re.compile(r"\*{2}(.+?)\*{2}")),
    ("md_italic", re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")),
    ("md_code_i", re.compile(r"`([^`\n]+)`")),
]


def _insert_inline(widget: tk.Text, text: str, base: str) -> None:
    """인라인 Markdown(굵기·이탤릭·인라인 코드)을 태그로 분리 삽입."""
    matches: list[tuple[int, int, str, str]] = []
    for tag, pat in _INL_PATS:
        for m in pat.finditer(text):
            matches.append((m.start(), m.end(), tag, m.group(1)))
    matches.sort(key=lambda x: x[0])
    # 겹치는 매치 제거 (첫 번째 우선)
    clean: list[tuple[int, int, str, str]] = []
    prev_end = 0
    for s, e, tag, content in matches:
        if s >= prev_end:
            clean.append((s, e, tag, content))
            prev_end = e
    pos = 0
    for s, e, tag, content in clean:
        if s > pos:
            widget.insert("end", text[pos:s], base)
        widget.insert("end", content, tag)
        pos = e
    if pos < len(text):
        widget.insert("end", text[pos:], base)


def _render_md(widget: tk.Text, text: str) -> None:
    """텍스트를 블록+인라인 Markdown으로 렌더링해 widget에 삽입한다."""
    in_code = False
    for line in text.splitlines(keepends=True):
        stripped = line.rstrip("\n\r")

        if _MD_FENCE.match(stripped):
            in_code = not in_code
            if in_code:
                widget.insert("end", "\n")
            else:
                widget.insert("end", "\n", "md_code_b")
            continue

        if in_code:
            widget.insert("end", stripped + "\n", "md_code_b")
            continue

        if not stripped:
            widget.insert("end", "\n")
            continue

        if _MD_HR_PAT.match(stripped):
            widget.insert("end", "\n" + "─" * 56 + "\n", "md_hr")
            continue

        m = _MD_HEAD.match(stripped)
        if m:
            tag = f"md_h{len(m.group(1))}"
            _insert_inline(widget, m.group(2), tag)
            widget.insert("end", "\n", tag)
            continue

        m = _MD_BLIST.match(stripped)
        if m:
            widget.insert("end", "  • ", "md_list")
            _insert_inline(widget, m.group(1), "agent_msg")
            widget.insert("end", "\n")
            continue

        m = _MD_NLIST.match(stripped)
        if m:
            widget.insert("end", f"  {m.group(1)}. ", "md_list")
            _insert_inline(widget, m.group(2), "agent_msg")
            widget.insert("end", "\n")
            continue

        _insert_inline(widget, stripped, "agent_msg")
        widget.insert("end", "\n")


def _insert_md(widget: tk.Text, text: str, _base_tag: str = "agent_msg") -> None:
    """하위 호환용 — _LogWatcher에서 사용."""
    _render_md(widget, text)


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
                 radius: int = 10, fontsize: int = 9, **kw):
        kw.setdefault("cursor", "hand2")
        outer = parent.cget("bg") if hasattr(parent, "cget") else _BG
        super().__init__(parent, bg=outer, highlightthickness=0, bd=0, **kw)
        self._text = text
        self._color = color
        self._radius = radius
        self._cmd = command
        self._fontsize = fontsize
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
                         font=(_FONT_KO, self._fontsize))

    def retheme(self, outer_bg: str) -> None:
        self.config(bg=outer_bg)
        self._draw()


# ── Canvas 기반 둥근 입력 바 ──────────────────────────────────────────────────

class _RoundInput(tk.Canvas):
    """Canvas 배경 + Text(다중 줄) + 전송 버튼이 결합된 둥근 입력 위젯.

    Enter → 전송 / Shift+Enter → 줄바꿈 / 자동 높이 확장.
    """

    _H_MIN = 38
    _H_MAX = 112
    _LINE_H = 18
    _PAD  = 14
    _BTNW = 34
    _PH   = "무엇이든 물어보세요"

    def __init__(self, parent, on_send,
                 btn_color: str, radius: int = 14):
        outer = parent.cget("bg") if hasattr(parent, "cget") else _BG
        super().__init__(parent, height=self._H_MIN, bg=outer,
                         highlightthickness=0, bd=0)
        self._radius = radius
        self._accent = btn_color
        self._on_send = on_send
        self._cur_h = self._H_MIN

        # Text 위젯 (다중 줄)
        self.entry = tk.Text(
            self, bg=_BG_INPUT, fg=_TEXT_DIM,
            font=(_FONT_KO, 9), wrap="word", relief="flat",
            insertbackground=_TEXT, bd=0, highlightthickness=0,
            height=1, pady=2,
        )
        self.entry.insert("1.0", self._PH)
        self.entry.bind("<FocusIn>",       self._focus_in)
        self.entry.bind("<FocusOut>",      self._focus_out)
        self.entry.bind("<Return>",        self._on_return)
        self.entry.bind("<Shift-Return>",  self._on_shift_return)
        self.entry.bind("<KeyRelease>",    self._on_text_change)
        self._ew = self.create_window(self._PAD, 9,
                                      anchor="nw", window=self.entry,
                                      width=100, height=self._H_MIN - 16)

        # 전송 버튼 (소형 Canvas)
        self._btn = tk.Canvas(self, bg=_BG_INPUT, highlightthickness=0,
                              cursor="hand2")
        self._bw = self.create_window(0, 0, anchor="center",
                                      window=self._btn,
                                      width=self._BTNW - 4,
                                      height=self._BTNW - 4)
        self._btn.bind("<Configure>", lambda _: self._draw_btn())
        self._btn.bind("<Enter>",     lambda _: self._draw_btn(True))
        self._btn.bind("<Leave>",     lambda _: self._draw_btn(False))
        self._btn.bind("<Button-1>",  lambda _: on_send())

        self.bind("<Configure>", self._redraw)

    # ── 텍스트 접근 ──────────────────────────────────────────────────────────

    def get_text(self) -> str:
        """입력된 텍스트 반환 (플레이스홀더 제외)."""
        text = self.entry.get("1.0", "end-1c")
        return "" if text == self._PH else text

    def clear_text(self) -> None:
        self.entry.delete("1.0", "end")

    # ── 키 바인딩 ────────────────────────────────────────────────────────────

    def _on_return(self, _) -> str:
        self._on_send()
        return "break"  # 기본 줄바꿈 차단

    def _on_shift_return(self, _) -> str:
        self.entry.insert("insert", "\n")
        self.entry.see("insert")
        self._on_text_change()
        return "break"

    def _on_text_change(self, _=None) -> None:
        """줄 수에 따라 위젯 높이를 자동 조정한다."""
        lines = int(self.entry.index("end-1c").split(".")[0])
        new_h = max(self._H_MIN,
                    min(self._H_MAX, self._H_MIN + (lines - 1) * self._LINE_H))
        if new_h != self._cur_h:
            self._cur_h = new_h
            self.config(height=new_h)
            self._redraw()

    # ── 플레이스홀더 ──────────────────────────────────────────────────────────

    def _focus_in(self, _) -> None:
        if self.entry.get("1.0", "end-1c") == self._PH:
            self.entry.delete("1.0", "end")
            self.entry.config(fg=_TEXT)

    def _focus_out(self, _) -> None:
        if not self.entry.get("1.0", "end-1c"):
            self.entry.insert("1.0", self._PH)
            self.entry.config(fg=_TEXT_DIM)
            self._cur_h = self._H_MIN
            self.config(height=self._H_MIN)
            self._redraw()

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
                      font=(_FONT_KO, 10))

    def _redraw(self, event=None) -> None:
        self.delete("bg")
        w = self.winfo_width()
        h = self._cur_h
        if w < 8 or h < 8:
            return
        _round_rect(self, 0, 0, w, h, self._radius, _BG_INPUT, tag="bg")
        self.tag_lower("bg")
        btn_size = self._BTNW - 4
        entry_w = w - self._BTNW - self._PAD * 2 - 10
        # 줄 수에 맞는 entry 높이 — 1줄=20px, 이후 LINE_H씩 증가, 세로 중앙 정렬
        lines = max(1, round((h - self._H_MIN) / self._LINE_H) + 1)
        entry_h = lines * self._LINE_H + 2
        entry_y = max(2, (h - entry_h) // 2)
        self.coords(self._ew, self._PAD, entry_y)
        self.itemconfig(self._ew, width=max(10, entry_w), height=entry_h)
        # 전송 버튼: 우하단 고정
        self.coords(self._bw,
                    w - self._PAD - btn_size // 2,
                    h - btn_size // 2 - 4)

    def set_sending(self, sending: bool) -> None:
        self._accent_bak = getattr(self, "_accent_bak", self._accent)
        self._accent = "#555555" if sending else self._accent_bak
        self._draw_btn()

    def retheme(self) -> None:
        outer = self.master.cget("bg") if hasattr(self.master, "cget") else _BG
        self.config(bg=outer)
        is_ph = self.entry.get("1.0", "end-1c") == self._PH
        self.entry.config(bg=_BG_INPUT,
                          fg=_TEXT_DIM if is_ph else _TEXT,
                          insertbackground=_TEXT)
        self._btn.config(bg=_BG_INPUT)
        self._redraw()
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


# ── 로그 파일 감시 ────────────────────────────────────────────────────────────


class _LogWatcher:
    """folder/.agents-dev/log/ 를 감시해 gemini/codex 로그를 각 탭에 자동 표시.

    ask-gemini.sh / ask-codex.sh 가 완성한 로그 파일(=== END 포함)을
    감지하면 쿼리와 응답을 분리해 해당 탭 채팅창에 삽입한다.
    """

    # filename prefix → tabs 리스트 인덱스 (Claude=0, Gemini=1, Codex=2)
    _ROUTES: dict[str, int] = {"gemini": 1, "codex": 2}

    def __init__(self, log_dir: Path, tabs: list) -> None:
        self._log_dir = log_dir
        self._tabs = tabs
        # 초기화 시점에 이미 있는 파일은 건너뜀
        self._seen: set[str] = (
            {p.name for p in log_dir.glob("*.log")} if log_dir.exists() else set()
        )
        # [Fix-high] 파일별 마지막 mtime 추적 — 파일이 안정될 때만 내용 읽음
        self._mtimes: dict[str, float] = {}
        # [Fix-medium] 탭 직접 전송 시 중복 표시 방지: prefix → 스킵 만료 시각
        self._skip_until: dict[str, float] = {}

    def reset(self, log_dir: Path) -> None:
        """폴더 변경 시 감시 대상 재설정."""
        self._log_dir = log_dir
        self._seen = (
            {p.name for p in log_dir.glob("*.log")} if log_dir.exists() else set()
        )
        self._mtimes.clear()

    def skip_next(self, prefix: str, duration: float = 60.0) -> None:
        """Gemini/Codex 탭이 직접 전송할 때 호출 — 해당 prefix 로그를 duration 초간 스킵."""
        self._skip_until[prefix] = time.monotonic() + duration

    def poll(self) -> None:
        """메인 스레드 폴링 루프에서 80ms 마다 호출."""
        if not self._log_dir.exists():
            return
        for path in self._log_dir.glob("*.log"):
            if path.name in self._seen:
                continue
            try:
                st = path.stat()
            except OSError:
                continue
            mtime = st.st_mtime
            prev = self._mtimes.get(path.name)
            # 파일이 아직 변경 중 — mtime만 기록하고 내용은 읽지 않음
            if prev != mtime:
                self._mtimes[path.name] = mtime
                continue
            # mtime 안정 확인 후 마지막 64바이트만 읽어 완성 여부 체크
            try:
                with open(path, "rb") as f:
                    f.seek(max(0, st.st_size - 64))
                    tail = f.read().decode("utf-8", errors="replace")
            except OSError:
                continue
            if "=== END" not in tail:
                continue  # 아직 작성 중
            # 완성 — 전체 내용 읽기
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            self._seen.add(path.name)
            self._mtimes.pop(path.name, None)
            self._route(path.name, text)

    def _route(self, name: str, text: str) -> None:
        for prefix, idx in self._ROUTES.items():
            if name.startswith(prefix) and idx < len(self._tabs):
                # 탭 직접 전송이 최근에 있었으면 스킵 (중복 방지)
                until = self._skip_until.get(prefix, 0.0)
                if time.monotonic() < until:
                    self._skip_until.pop(prefix, None)
                    self._seen.add(name)  # 다음 poll에서 재처리 방지
                    return
                self._display(self._tabs[idx], text)
                return

    def _display(self, tab: "AgentTab", text: str) -> None:
        query = self._section(text, "=== QUERY ===", "=== RESPONSE ===").strip()
        response = self._section(text, "=== RESPONSE ===", "=== END").strip()
        if not response:
            return
        chat = tab._chat
        chat.configure(state="normal")
        if query:
            chat.insert("end", "\nClaude →\n", "you_lbl")
            chat.insert("end", f"{query}\n", "you_msg")
        chat.insert("end", f"\n{tab.name}\n", "agent_lbl")
        _insert_md(chat, response + "\n", "agent_msg")
        chat.insert("end", "\n")
        chat.see("end")
        chat.configure(state="disabled")
        tab._ph.place_forget()

    @staticmethod
    def _section(text: str, start: str, end: str) -> str:
        s = text.find(start)
        if s < 0:
            return ""
        s += len(start)
        e = text.find(end, s)
        return text[s:e] if e >= 0 else text[s:]


# ── AgentTab ──────────────────────────────────────────────────────────────────


class AgentTab:
    """채팅 히스토리 + 입력창을 가진 단일 에이전트 탭."""

    def __init__(self, parent: tk.Frame, name: str, accent: str,
                 cmd_fn, folder_getter, watcher_getter=None) -> None:
        self.name = name
        self.accent = accent
        self._cmd_fn = cmd_fn
        self._folder_getter = folder_getter
        self._watcher_getter = watcher_getter
        self._log_prefix: str | None = {"Gemini": "gemini", "Codex": "codex"}.get(name)
        self._queue: queue.Queue[str] = queue.Queue()
        self._resp_buf: list[str] = []
        self._running = False
        self._first_msg = True
        self.frame = parent
        self._build()

    def _build(self) -> None:
        # 입력창 높이 변화가 앱 창 크기에 영향을 주지 않도록 전파 차단
        self.frame.pack_propagate(False)

        # ── 입력 영역 — 먼저 bottom 고정 pack (창이 작아져도 항상 보임) ──────
        input_outer = tk.Frame(self.frame, bg=_BG)
        input_outer.pack(side="bottom", fill="x", padx=80, pady=(10, 6))

        self._input_bar = _RoundInput(input_outer, self._send, self.accent)
        self._input_bar.pack(fill="x")

        # ── 진행 제목 헤더 (굵은 텍스트 자동 추출) ───────────────────────
        self._header_lbl = tk.Label(
            self.frame, text="", bg=_BG, fg=_TEXT_DIM,
            font=(_FONT_KO, 8), anchor="w", padx=80, pady=3,
        )
        self._header_lbl.pack(side="top", fill="x")

        # ── 대화 영역 — 남은 공간 전부 채움 ───────────────────────────────
        chat_outer = tk.Frame(self.frame, bg=_BG)
        chat_outer.pack(fill="both", expand=True)

        self._chat = tk.Text(
            chat_outer, state="disabled", bg=_BG, fg=_TEXT,
            font=(_FONT_KO, 9), wrap="word", relief="flat",
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
            foreground=_TEXT_DIM, font=(_FONT_KO, 8), spacing1=20)
        self._chat.tag_configure("you_msg",
            foreground=_TEXT,     font=(_FONT_KO, 9))
        self._chat.tag_configure("agent_lbl",
            foreground=self.accent, font=(_FONT_KO, 8), spacing1=20)
        self._chat.tag_configure("agent_msg",
            foreground=_TEXT,      font=(_FONT_KO, 9))
        self._chat.tag_configure("agent_msg_b",
            foreground="#ffffff",  font=(_FONT_KO, 9))
        self._chat.tag_configure("system_msg",
            foreground=_TEXT_DIM,  font=(_FONT_KO, 9),
            justify="center", spacing1=6)
        # ── Markdown 렌더링 태그 ──────────────────────────────────────────
        self._chat.tag_configure("md_h1",
            foreground="#ffffff",  font=(_FONT_KO, 13, "bold"),
            spacing1=18, spacing3=4)
        self._chat.tag_configure("md_h2",
            foreground="#ffffff",  font=(_FONT_KO, 11, "bold"),
            spacing1=14, spacing3=3)
        self._chat.tag_configure("md_h3",
            foreground="#f0f0f0",  font=(_FONT_KO, 10, "bold"),
            spacing1=10, spacing3=2)
        self._chat.tag_configure("md_bold",
            foreground="#ffffff",  font=(_FONT_KO, 9, "bold"))
        self._chat.tag_configure("md_italic",
            foreground=_TEXT,      font=(_FONT_KO, 9, "italic"))
        self._chat.tag_configure("md_b_i",
            foreground="#ffffff",  font=(_FONT_KO, 9, "bold italic"))
        self._chat.tag_configure("md_code_i",
            foreground="#e8bf6a",  font=(_CODE_FONT, 9),
            background="#2a2a2a")
        self._chat.tag_configure("md_code_b",
            foreground="#abb2bf",  font=(_CODE_FONT, 9),
            background="#1e1e1e",  lmargin1=20, lmargin2=20)
        self._chat.tag_configure("md_list",
            foreground=_TEXT_DIM,  font=(_FONT_KO, 9))
        self._chat.tag_configure("md_hr",
            foreground="#444444",  font=(_FONT_KO, 8))

        # 빈 화면 플레이스홀더
        self._ph = tk.Label(self._chat, text="어디서부터 시작할까요?",
                            bg=_BG, fg=_TEXT_DIM, font=(_FONT_KO, 11))
        self._ph.place(relx=0.5, rely=0.42, anchor="center")

    def retheme(self) -> None:
        self.frame.config(bg=_BG)
        for child in self.frame.winfo_children():
            try:
                child.config(bg=_BG)
            except Exception:
                pass
        sel_bg   = "#404040" if _THEME == "dark" else "#c8c8d0"
        bold_fg  = "#ffffff" if _THEME == "dark" else "#000000"
        head_bg  = "#1e1e1e" if _THEME == "dark" else "#e8e8ec"
        head_fg  = "#abb2bf" if _THEME == "dark" else "#333333"
        ci_bg    = "#2a2a2a" if _THEME == "dark" else "#e8e8ec"
        hr_fg    = "#444444" if _THEME == "dark" else "#aaaaaa"
        self._chat.config(bg=_BG, fg=_TEXT, selectbackground=sel_bg)
        self._chat.tag_configure("you_lbl",    foreground=_TEXT_DIM)
        self._chat.tag_configure("you_msg",    foreground=_TEXT)
        self._chat.tag_configure("agent_msg",  foreground=_TEXT)
        self._chat.tag_configure("agent_msg_b", foreground=bold_fg)
        self._chat.tag_configure("system_msg", foreground=_TEXT_DIM)
        self._chat.tag_configure("md_h1",      foreground=bold_fg)
        self._chat.tag_configure("md_h2",      foreground=bold_fg)
        self._chat.tag_configure("md_h3",      foreground=bold_fg)
        self._chat.tag_configure("md_bold",    foreground=bold_fg)
        self._chat.tag_configure("md_italic",  foreground=_TEXT)
        self._chat.tag_configure("md_b_i",     foreground=bold_fg)
        self._chat.tag_configure("md_code_i",  background=ci_bg)
        self._chat.tag_configure("md_code_b",  foreground=head_fg, background=head_bg)
        self._chat.tag_configure("md_list",    foreground=_TEXT_DIM)
        self._chat.tag_configure("md_hr",      foreground=hr_fg)
        self._ph.config(bg=_BG, fg=_TEXT_DIM)
        self._header_lbl.config(bg=_BG, fg=_TEXT_DIM)
        self._input_bar.retheme()

    # ── 전송 ─────────────────────────────────────────────────────────────────

    def _send(self) -> None:
        msg = self._input_bar.get_text().strip()
        if not msg or self._running:
            return
        self._input_bar.clear_text()
        self._input_bar.entry.config(fg=_TEXT)
        self._ph.place_forget()

        self._append_you(msg)
        self._running = True
        self._input_bar.set_sending(True)

        first = self._first_msg
        self._first_msg = False
        folder = self._folder_getter()

        # [Fix-medium] 직접 전송 시 로그 감시자에게 중복 스킵 신호
        if self._log_prefix and self._watcher_getter:
            watcher = self._watcher_getter()
            if watcher:
                watcher.skip_next(self._log_prefix)

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
                stdin=subprocess.DEVNULL,
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
                    self._header_lbl.config(text="")
                    self._resp_buf = []
                    self._chat.configure(state="normal")
                    self._chat.insert("end", f"\n{self.name}\n", "agent_lbl")
                    # 스트리밍 시작점 마크 (gravity=left → 이후 삽입 텍스트보다 앞에 고정)
                    self._chat.mark_set("_resp_start", "end")
                    self._chat.mark_gravity("_resp_start", "left")
                    self._chat.configure(state="disabled")
                elif msg == "__DONE__":
                    self._running = False
                    self._input_bar.set_sending(False)
                    full = "".join(self._resp_buf)
                    self._resp_buf = []
                    self._chat.configure(state="normal")
                    # _resp_start 마크가 있으면 스트리밍 원본을 삭제 후 Markdown 재렌더링
                    # 없으면 (START 없이 DONE이 온 비정상 경로) 그대로 이어붙임
                    if "_resp_start" in self._chat.mark_names():
                        self._chat.delete("_resp_start", "end")
                    _render_md(self._chat, full)
                    self._chat.insert("end", "\n")
                    self._chat.see("end")
                    self._chat.configure(state="disabled")
                else:
                    self._resp_buf.append(msg)
                    # 스트리밍 중 원본 텍스트 실시간 표시 (완료 시 Markdown으로 교체됨)
                    self._chat.configure(state="normal")
                    self._chat.insert("end", msg, "agent_msg")
                    self._chat.see("end")
                    self._chat.configure(state="disabled")
                    # 굵은 텍스트를 진행 제목으로 실시간 추출
                    for m in _MD_BOLD.finditer(msg):
                        heading = m.group(1).strip()
                        if len(heading) >= 3:
                            self._header_lbl.config(
                                text=f"▸  {heading[:44]}", fg=_TEXT_DIM)
                            break
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
    """Agent Launcher — 3-agent 탭 채팅 인터페이스."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Agent Launcher")
        self.configure(bg=_BG)
        self.minsize(860, 660)
        self.resizable(True, True)

        self._folder: Path | None = None
        self._log_queue: queue.Queue[str] = queue.Queue()
        self._init_thread: threading.Thread | None = None
        self._tick = 0
        self._log_watcher: _LogWatcher | None = None
        self._base_folder: Path | None = None
        self._projects: list[dict] = []
        self._current_project: str | None = None
        _base, _projs = _load_projects()
        self._base_folder = _base
        self._projects = _projs

        # VS Code 스타일 한글 폰트 감지
        global _FONT_KO
        try:
            from tkinter import font as _tkfont
            _avail = set(_tkfont.families())
            for _f in ["나눔바른고딕", "나눔고딕", "Nanum Gothic"]:
                if _f in _avail:
                    _FONT_KO = _f
                    break
        except Exception:
            pass

        self._build_ui()
        # 저장된 기본 폴더가 있으면 시작 시 즉시 표시
        if self._base_folder:
            self._folder = self._base_folder
            self._update_folder_display()
        self._poll_all()
        self._style_titlebar()
        self.after(300, self._style_combo_popup)

    def _style_titlebar(self) -> None:
        """네이티브 타이틀바를 앱 배경색과 통일 (Windows 10+ DWM)."""
        if sys.platform != "win32":
            return
        try:
            import ctypes
            self.update_idletasks()
            hwnd = ctypes.windll.user32.FindWindowW(None, "Agent Launcher")
            if not hwnd:
                return
            dark_mode = 0 if _THEME == "light" else 1
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 20, ctypes.byref(ctypes.c_int(dark_mode)), 4
            )
            # COLORREF = 0x00BBGGRR (grayscale: same as RGB)
            r = int(_BG_DARK[1:3], 16)
            g = int(_BG_DARK[3:5], 16)
            b = int(_BG_DARK[5:7], 16)
            colorref = b << 16 | g << 8 | r
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 35, ctypes.byref(ctypes.c_int(colorref)), 4
            )
        except Exception:
            pass

    def _build_ui(self) -> None:
        # theme_use는 모든 TTK 스타일을 초기화하므로 반드시 가장 먼저 호출
        ttk.Style(self).theme_use("clam")
        self._build_topbar()
        self._build_notebook()

    # ── 탑바 ──────────────────────────────────────────────────────────────────

    def _build_topbar(self) -> None:
        bar = tk.Frame(self, bg=_BG_DARK, pady=10)
        bar.pack(fill="x")
        self._topbar = bar

        # 오른쪽 버튼 먼저 pack (left expand 전에)
        btn_init = _RoundBtn(bar, "🚀  초기화 + 실행", self._run_init, _GREEN,
                             radius=10, fontsize=10, width=175, height=36)
        btn_init.pack(side="right", padx=(0, 16))
        btn_folder = _RoundBtn(bar, "📂  폴더 열기", self._open_folder, "#555555",
                               radius=10, fontsize=10, width=130, height=36)
        btn_folder.pack(side="right", padx=(0, 8))
        self._theme_btn = _RoundBtn(bar, "☀️", self._toggle_theme, "#555555",
                                    radius=10, fontsize=10, width=36, height=36)
        self._theme_btn.pack(side="right", padx=(0, 4))
        btn_del = _RoundBtn(bar, "🗑", self._delete_project, "#555555",
                            radius=10, fontsize=10, width=36, height=36)
        btn_del.pack(side="right", padx=(0, 4))
        btn_add = _RoundBtn(bar, "➕", self._new_project, "#555555",
                            radius=10, fontsize=10, width=36, height=36)
        btn_add.pack(side="right", padx=(0, 4))
        self._topbar_btns = [btn_init, btn_folder, self._theme_btn, btn_del, btn_add]

        # 프로젝트 콤보박스 스타일
        style = ttk.Style(self)
        style.configure("Proj.TCombobox",
                        fieldbackground=_BG_INPUT, background=_BG_INPUT,
                        foreground=_TEXT, selectbackground=_BG_INPUT,
                        selectforeground=_TEXT, arrowcolor=_TEXT_DIM,
                        bordercolor="#333333", lightcolor="#333333", darkcolor="#333333",
                        borderwidth=1, padding=(6, 4))
        style.map("Proj.TCombobox",
                  fieldbackground=[("readonly", _BG_INPUT)],
                  selectbackground=[("readonly", _BG_INPUT)],
                  selectforeground=[("readonly", _TEXT)])

        self._proj_combo = ttk.Combobox(
            bar, state="readonly", style="Proj.TCombobox",
            font=(_FONT_KO, 9), width=22,
        )
        self._proj_combo.pack(side="left", padx=(16, 6), ipady=6)
        self._proj_combo.bind("<<ComboboxSelected>>", self._on_project_select)
        self._proj_combo.bind("<<ComboboxOpened>>", lambda _: self.after(10, self._style_combo_popup))
        self._refresh_combo()

        # 폴더 박스 (클릭 → 폴더 선택)
        folder_box = tk.Frame(bar, bg=_BG_INPUT, padx=12,
                              highlightbackground="#333333", highlightthickness=1)
        folder_box.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=8)
        self._folder_box = folder_box

        folder_icon = tk.Label(folder_box, text="📁", bg=_BG_INPUT,
                               fg=_TEXT_DIM, font=(_FONT_KO, 9))
        folder_icon.pack(side="left")
        self._folder_icon_lbl = folder_icon

        self._folder_var = tk.StringVar(value="기본 폴더를 선택하세요...")
        lbl = tk.Label(folder_box, textvariable=self._folder_var,
                       bg=_BG_INPUT, fg=_TEXT_DIM,
                       font=(_FONT_KO, 9), anchor="w", cursor="hand2")
        lbl.pack(side="left", fill="x", expand=True, padx=(6, 0))
        self._folder_lbl = lbl

        lbl.bind("<Configure>", lambda _: self._truncate_folder_label())
        for w in (folder_box, lbl):
            w.bind("<Button-1>", lambda _: self._select_folder())

    # ── Notebook ──────────────────────────────────────────────────────────────

    def _build_notebook(self) -> None:
        style = ttk.Style(self)
        style.configure("Dark.TNotebook",
                        background=_BG_DARK, borderwidth=0,
                        lightcolor=_BG_DARK, darkcolor=_BG_DARK,
                        tabmargins=[0, 0, 0, 0])
        style.configure("Dark.TNotebook.Tab",
                        background=_BG_DARK, foreground=_TEXT_DIM,
                        padding=[24, 5], font=(_FONT_KO, 9),
                        borderwidth=1, relief="flat", focuscolor="",
                        lightcolor="#333333", darkcolor="#333333")
        style.map("Dark.TNotebook.Tab",
                  background=[("selected", _BG), ("active", "#262626")],
                  foreground=[("selected", _TEXT), ("active", _TEXT)],
                  padding=[("selected", [24, 8])],
                  font=[("selected", (_FONT_KO, 10, "bold"))],
                  expand=[("selected", [0, 0, 0, 0]),
                          ("!selected", [0, 0, 0, 0])],
                  relief=[("selected", "flat"), ("active", "flat")],
                  lightcolor=[("selected", _BG), ("!selected", "#333333")])
        style.configure("Vertical.TScrollbar",
                        background=_BG_INPUT, troughcolor=_BG,
                        borderwidth=0, arrowsize=0)

        self._nb = ttk.Notebook(self, style="Dark.TNotebook")
        self._nb.pack(fill="both", expand=True)

        # 탭 바 우측 빈 공간에 상태 레이블 오버레이 (pack 이 아닌 place 사용)
        self._status_lbl = tk.Label(
            self, text="", bg=_BG_DARK, fg=_GREEN,
            font=(_FONT_KO, 9),
        )
        self._status_lbl.place(in_=self._nb, relx=1.0, x=-16, y=12, anchor="ne")

        claude_f = tk.Frame(self._nb, bg=_BG)
        gemini_f = tk.Frame(self._nb, bg=_BG)
        codex_f  = tk.Frame(self._nb, bg=_BG)
        init_f   = tk.Frame(self._nb, bg=_BG)
        self._init_frame = init_f

        self._nb.add(claude_f, text="  🤖 Claude  ")
        self._nb.add(gemini_f, text="  🔬 Gemini  ")
        self._nb.add(codex_f,  text="  📝 Codex  ")
        self._nb.add(init_f,   text="  📋 초기화  ")

        getter = lambda: self._folder
        watcher_getter = lambda: self._log_watcher
        self._tabs = [
            AgentTab(claude_f, "Claude", _GREEN,  _claude_cmd, getter),
            AgentTab(gemini_f, "Gemini", _BLUE,   _gemini_cmd, getter, watcher_getter),
            AgentTab(codex_f,  "Codex",  _PURPLE, _codex_cmd,  getter, watcher_getter),
        ]
        self._build_init_tab(init_f)

    def _build_init_tab(self, frame: tk.Frame) -> None:
        self._init_spacer = tk.Frame(frame, bg=_BG, height=12)
        self._init_spacer.pack()
        self._init_log_lbl = tk.Label(frame, text="초기화 로그", bg=_BG, fg=_TEXT_DIM,
                                      font=(_FONT_KO, 9), anchor="w")
        self._init_log_lbl.pack(fill="x", padx=20, pady=(0, 4))

        outer = tk.Frame(frame, bg=_BG)
        outer.pack(fill="both", expand=True)
        self._init_outer = outer

        self._log = tk.Text(outer, state="disabled", bg=_BG, fg=_TEXT,
                            font=(_FONT_KO, 9), relief="flat",
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
        """기본 폴더를 선택한다. 새 프로젝트는 이 폴더 아래에 생성된다."""
        path = filedialog.askdirectory(title="기본 폴더 선택")
        if not path:
            return
        self._base_folder = Path(path)
        _save_projects(self._base_folder, self._projects)
        # 프로젝트가 선택되지 않은 상태면 기본 폴더를 작업 폴더로 사용
        if self._current_project is None:
            self._folder = self._base_folder
            self._reset_watcher()
        self._update_folder_display()

    def _update_folder_display(self) -> None:
        display = self._folder or self._base_folder
        if display is None:
            return
        self._folder_full = str(display)
        self._truncate_folder_label()

    def _truncate_folder_label(self) -> None:
        """레이블 픽셀 너비에 맞춰 경로를 잘라 '...'을 붙인다."""
        full = getattr(self, "_folder_full", None)
        if not full:
            return
        lbl = self._folder_lbl
        avail = lbl.winfo_width() - 4
        if avail <= 0:
            self._folder_var.set(full)
            return
        from tkinter import font as tkfont
        f = tkfont.Font(font=lbl.cget("font"))
        if f.measure(full) <= avail:
            self._folder_var.set(full)
            return
        # 경로 끝(파일명·폴더명)을 최대한 보존하고 앞에 "..." 붙임
        text = full
        while len(text) > 1 and f.measure("..." + text) > avail:
            text = text[1:]
        self._folder_var.set("..." + text)

    def _style_combo_popup(self) -> None:
        """<<ComboboxOpened>> 시 팝업 Listbox를 Tcl 레벨에서 직접 색상 적용."""
        try:
            cb = self._proj_combo
            popup = str(cb.tk.call("ttk::combobox::PopdownWindow", str(cb)))
            lb = popup + ".f.l"
            cb.tk.call(popup + ".f", "configure", "-borderwidth", "1")
            cb.tk.call(lb, "configure", "-background",        _BG_INPUT)
            cb.tk.call(lb, "configure", "-foreground",        _TEXT)
            cb.tk.call(lb, "configure", "-selectbackground",  _GREEN)
            cb.tk.call(lb, "configure", "-selectforeground",  "#ffffff")
            cb.tk.call(lb, "configure", "-highlightthickness", "0")
        except Exception:
            pass

    def _refresh_combo(self) -> None:
        names = [p["name"] for p in self._projects]
        self._proj_combo["values"] = names
        if self._current_project and self._current_project in names:
            self._proj_combo.set(self._current_project)
        else:
            self._proj_combo.set("" if names else "저장된 프로젝트 없음")

    def _on_project_select(self, _=None) -> None:
        name = self._proj_combo.get()
        for p in self._projects:
            if p["name"] == name:
                self._folder = Path(p["path"])
                self._current_project = name
                self._base_folder = self._folder.parent  # base 자동 추론
                self._update_folder_display()
                self._reset_watcher()
                return

    def _new_project(self) -> None:
        """기본 폴더 아래에 프로젝트 이름과 동일한 하위 폴더를 생성한다."""
        if self._base_folder is None:
            messagebox.showwarning("기본 폴더 미선택", "먼저 기본 폴더를 선택해주세요.")
            return
        name = simpledialog.askstring(
            "새 프로젝트",
            f"프로젝트 이름을 입력하세요.\n기본 폴더: {self._base_folder}",
            parent=self,
        )
        if not name or not name.strip():
            return
        name = name.strip()
        new_path = self._base_folder / name
        try:
            new_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            messagebox.showerror("폴더 생성 실패", str(e), parent=self)
            return
        # 중복 이름이면 경로 갱신, 없으면 신규 추가
        existing = next((p for p in self._projects if p["name"] == name), None)
        if existing:
            existing["path"] = str(new_path)
        else:
            self._projects.append({"name": name, "path": str(new_path)})
        _save_projects(self._base_folder, self._projects)
        self._folder = new_path
        self._current_project = name
        self._update_folder_display()
        self._refresh_combo()
        self._proj_combo.set(name)
        self._reset_watcher()

    def _delete_project(self) -> None:
        name = self._proj_combo.get()
        if name not in [p["name"] for p in self._projects]:
            return
        if not messagebox.askyesno("프로젝트 삭제",
                                   f"'{name}' 을(를) 목록에서 삭제할까요?\n(폴더는 삭제되지 않습니다)",
                                   parent=self):
            return
        self._projects = [p for p in self._projects if p["name"] != name]
        _save_projects(self._base_folder, self._projects)
        self._current_project = None
        self._folder = self._base_folder
        self._update_folder_display()
        self._refresh_combo()

    def _open_folder(self) -> None:
        if self._folder is None:
            messagebox.showwarning("폴더 미선택", "먼저 폴더를 선택해주세요.")
            return
        opener = {"win32": "explorer", "darwin": "open"}.get(sys.platform, "xdg-open")
        subprocess.Popen([opener, str(self._folder)])

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

        if self._log_watcher:
            self._log_watcher.poll()

        # 실행 상태 스피너 업데이트 (80ms × 3 = ~240ms 마다 프레임 전환)
        self._tick += 1
        running_tab  = next((t for t in self._tabs if t._running), None)
        init_running = bool(self._init_thread and self._init_thread.is_alive())
        if running_tab or init_running:
            spinner = _STATUS_FRAMES[self._tick // 3 % len(_STATUS_FRAMES)]
            if init_running:
                label = "초기화 중"
            else:
                label = _STATUS_LABELS.get(running_tab.name, running_tab.name)
            self._status_lbl.config(text=f"{spinner} {label}", fg=_GREEN)
        else:
            self._status_lbl.config(text="")

        self.after(80, self._poll_all)

    def _switch_to_claude(self) -> None:
        self._nb.select(0)
        if self._folder:
            self._tabs[0].append_system(
                f"📁 {self._folder.name}  |  초기화 완료"
            )
            self._reset_watcher()  # 초기화로 log 디렉토리가 생성된 후 재설정
        self._tabs[0].focus_input()

    def _reset_watcher(self) -> None:
        if self._folder is None:
            return
        log_dir = self._folder / ".agents-dev" / "log"
        if self._log_watcher is None:
            self._log_watcher = _LogWatcher(log_dir, self._tabs)
        else:
            self._log_watcher.reset(log_dir)

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

    # ── 테마 전환 ──────────────────────────────────────────────────────────────

    def _toggle_theme(self) -> None:
        _apply_palette("light" if _THEME == "dark" else "dark")
        self._theme_btn._text = "🌙" if _THEME == "light" else "☀️"
        self._retheme()

    def _retheme(self) -> None:
        self.configure(bg=_BG)
        # 탑바
        self._topbar.config(bg=_BG_DARK)
        for btn in self._topbar_btns:
            btn.retheme(_BG_DARK)
        # 폴더 박스
        border_ui = "#333333" if _THEME == "dark" else "#cccccc"
        self._folder_box.config(bg=_BG_INPUT, highlightbackground=border_ui)
        self._folder_icon_lbl.config(bg=_BG_INPUT, fg=_TEXT_DIM)
        self._folder_lbl.config(bg=_BG_INPUT, fg=_TEXT_DIM)
        self._status_lbl.config(bg=_BG_DARK)
        # TTK 스타일 업데이트
        style = ttk.Style(self)
        style.configure("Proj.TCombobox",
                        fieldbackground=_BG_INPUT, background=_BG_INPUT,
                        foreground=_TEXT, selectbackground=_BG_INPUT,
                        selectforeground=_TEXT, arrowcolor=_TEXT_DIM,
                        bordercolor=border_ui, lightcolor=border_ui, darkcolor=border_ui)
        style.map("Proj.TCombobox",
                  fieldbackground=[("readonly", _BG_INPUT)],
                  selectbackground=[("readonly", _BG_INPUT)],
                  selectforeground=[("readonly", _TEXT)])
        active_tab  = "#262626" if _THEME == "dark" else "#e0e0e0"
        border_line = "#333333" if _THEME == "dark" else "#cccccc"
        style.configure("Dark.TNotebook",
                        background=_BG_DARK,
                        lightcolor=_BG_DARK, darkcolor=_BG_DARK)
        style.configure("Dark.TNotebook.Tab",
                        background=_BG_DARK, foreground=_TEXT_DIM,
                        padding=[24, 5], relief="flat", focuscolor="",
                        lightcolor=border_line, darkcolor=border_line)
        style.map("Dark.TNotebook.Tab",
                  background=[("selected", _BG), ("active", active_tab)],
                  foreground=[("selected", _TEXT), ("active", _TEXT)],
                  padding=[("selected", [24, 8])],
                  font=[("selected", (_FONT_KO, 10, "bold"))],
                  expand=[("selected", [0, 0, 0, 0]),
                          ("!selected", [0, 0, 0, 0])],
                  relief=[("selected", "flat"), ("active", "flat")],
                  lightcolor=[("selected", _BG), ("!selected", border_line)])
        style.configure("Vertical.TScrollbar",
                        background=_BG_INPUT, troughcolor=_BG)
        # 초기화 탭
        self._init_frame.config(bg=_BG)
        self._init_spacer.config(bg=_BG)
        self._init_log_lbl.config(bg=_BG, fg=_TEXT_DIM)
        self._init_outer.config(bg=_BG)
        sel_bg = "#404040" if _THEME == "dark" else "#c8c8d0"
        self._log.config(bg=_BG, fg=_TEXT, selectbackground=sel_bg)
        # 에이전트 탭
        for tab in self._tabs:
            tab.retheme()
        # 타이틀바
        self._style_titlebar()


# ── 진입점 ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = AgentsGUI()
    app.mainloop()
