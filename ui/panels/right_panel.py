# 우측 패널 — 에이전트 출력·로그 뷰어·명령 입력창
from __future__ import annotations

import queue
import tkinter as tk
from pathlib import Path
from typing import Callable

from config import ACCENT_PRIMARY, AGENTS, FONT_KO, FONT_SIZE_SMALL, SPINNER_FRAMES
from core.log_watcher import LogEvent
from core.workflow import run_agent
from ui.widgets.common import RoundInput
from ui.widgets.log_viewer import LogViewer


class RightPanel:
    """에이전트 출력 패널 — 로그 뷰어 + 에이전트 선택 + 명령 입력."""

    def __init__(self, parent: tk.Widget,
                 bg: str = "#212121", bg_dark: str = "#171717",
                 bg_input: str = "#2f2f2f",
                 fg: str = "#ececec", fg_dim: str = "#8e8ea0") -> None:
        self._bg       = bg
        self._bg_dark  = bg_dark
        self._bg_input = bg_input
        self._fg       = fg
        self._fg_dim   = fg_dim
        self._folder: Path | None = None
        self._out_queue: queue.Queue[str] = queue.Queue()
        self._running   = False
        self._tick       = 0
        self._active_agent = AGENTS[0].key  # 기본: claude-main

        self.frame = tk.Frame(parent, bg=bg)
        self._build()

    def _build(self) -> None:
        # ── 로그 뷰어 (중앙 확장 영역) ──────────────────────────────────────
        self._viewer = LogViewer(
            self.frame,
            bg=self._bg, bg_dark=self._bg_dark,
            fg=self._fg, fg_dim=self._fg_dim,
        )
        self._viewer.frame.pack(fill="both", expand=True)

        # ── 하단 입력 영역 ───────────────────────────────────────────────────
        bottom = tk.Frame(self.frame, bg=self._bg)
        bottom.pack(fill="x", padx=12, pady=(4, 8))

        # 에이전트 선택 드롭다운
        agent_row = tk.Frame(bottom, bg=self._bg)
        agent_row.pack(fill="x", pady=(0, 4))

        tk.Label(agent_row, text="대상 에이전트",
                 bg=self._bg, fg=self._fg_dim,
                 font=(FONT_KO, FONT_SIZE_SMALL)).pack(side="left")

        self._agent_var = tk.StringVar(value=AGENTS[0].label)
        agent_names = [a.label for a in AGENTS]
        menu = tk.OptionMenu(agent_row, self._agent_var, *agent_names)
        menu.config(bg=self._bg, fg=self._fg, activebackground=self._bg_input,
                    font=(FONT_KO, FONT_SIZE_SMALL), relief="flat", bd=0,
                    highlightthickness=0)
        menu["menu"].config(bg=self._bg, fg=self._fg,
                            font=(FONT_KO, FONT_SIZE_SMALL))
        menu.pack(side="left", padx=6)
        self._agent_var.trace_add("write", self._on_agent_change)

        # 상태 표시 레이블
        self._status_lbl = tk.Label(
            agent_row, text="",
            bg=self._bg, fg=self._fg_dim,
            font=(FONT_KO, FONT_SIZE_SMALL),
        )
        self._status_lbl.pack(side="right")

        # 입력창
        accent = next((a.accent for a in AGENTS if a.key == self._active_agent), ACCENT_PRIMARY)
        self._input = RoundInput(
            bottom, on_send=self._send,
            btn_color=accent,
            bg_input=self._bg_input,
            fg=self._fg, fg_dim=self._fg_dim,
        )
        self._input.pack(fill="x")

    # ── 공개 인터페이스 ───────────────────────────────────────────────────────

    def set_folder(self, folder: Path) -> None:
        self._folder = folder

    def push_event(self, event: LogEvent) -> None:
        """LogWatcher에서 받은 이벤트를 뷰어에 추가한다."""
        self._viewer.append(event)

    def poll_output(self) -> None:
        """메인 스레드 폴링 루프에서 호출 — 스트리밍 출력을 뷰어에 표시한다."""
        try:
            while True:
                line = self._out_queue.get_nowait()
                self._viewer.append_raw(self._active_agent, line)
        except queue.Empty:
            pass

        if self._running:
            self._tick = (self._tick + 1) % len(SPINNER_FRAMES)
            agent_def = next((a for a in AGENTS if a.key == self._active_agent), None)
            label = agent_def.label if agent_def else self._active_agent
            self._status_lbl.config(
                text=f"{SPINNER_FRAMES[self._tick]}  {label} 응답중"
            )

    # ── 내부 이벤트 ──────────────────────────────────────────────────────────

    def _on_agent_change(self, *_) -> None:
        label = self._agent_var.get()
        agent = next((a for a in AGENTS if a.label == label), None)
        if agent:
            self._active_agent = agent.key
            self._input.retheme(self._bg_input, self._fg, self._fg_dim)

    def _send(self) -> None:
        if not self._folder:
            return
        message = self._input.get_text().strip()
        if not message or self._running:
            return
        self._input.clear_text()
        self._input.set_sending(True)
        self._running = True
        self._status_lbl.config(text="")

        def _finish(rc: int) -> None:
            self._running = False
            self._input.set_sending(False)
            self._status_lbl.config(text="완료" if rc == 0 else f"오류 (rc={rc})")

        def on_done(rc: int) -> None:
            self.frame.after(0, lambda: _finish(rc))

        run_agent(
            self._active_agent,
            message,
            self._folder,
            self._out_queue,
            on_done=on_done,
        )
