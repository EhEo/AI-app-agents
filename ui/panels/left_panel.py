# 좌측 패널 — 프로젝트 목록·태스크 관리·진행률 표시
from __future__ import annotations

import tkinter as tk


class LeftPanel:
    """프로젝트 관리 패널 (태스크 목록, 진행률, 프로젝트 선택)."""

    def __init__(self, parent: tk.Widget) -> None:
        self.frame = tk.Frame(parent)
        self._build()

    def _build(self) -> None:
        raise NotImplementedError
