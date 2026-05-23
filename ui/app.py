# Agent Launcher v2 메인 윈도우 — 좌우 분할 레이아웃 초기화
from __future__ import annotations

import tkinter as tk


class AgentLauncherApp(tk.Tk):
    """Agent Launcher v2 메인 윈도우."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Agent Launcher v2")
        self.minsize(1100, 700)
        self.resizable(True, True)
        self._build_ui()

    def _build_ui(self) -> None:
        raise NotImplementedError
