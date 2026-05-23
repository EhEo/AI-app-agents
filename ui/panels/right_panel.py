# 우측 패널 — 에이전트 출력·로그 뷰어·명령 입력창
from __future__ import annotations

import tkinter as tk


class RightPanel:
    """에이전트 출력 패널 (로그 뷰어, 에이전트 탭, 명령 입력)."""

    def __init__(self, parent: tk.Widget) -> None:
        self.frame = tk.Frame(parent)
        self._build()

    def _build(self) -> None:
        raise NotImplementedError
