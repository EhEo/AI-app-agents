# 설정 화면 — 기본 폴더 선택·에이전트 설정·테마 전환
from __future__ import annotations

import tkinter as tk


class SettingsScreen(tk.Toplevel):
    """설정 팝업 윈도우 — 기본 폴더 및 에이전트 옵션 설정."""

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.title("설정")
        self.resizable(False, False)
        self._build()

    def _build(self) -> None:
        raise NotImplementedError
