# 로그 뷰어 위젯 — log.md 6-태그 컬러링·에이전트별 필터링
from __future__ import annotations

import tkinter as tk

# 태그별 표시 색상 (우측 패널에서 사용)
TAG_COLORS: dict[str, str] = {
    "DECISION":    "#4285f4",   # 파랑
    "WORKER_CALL": "#10a37f",   # 초록
    "VERIFICATION":"#f59e0b",   # 주황
    "ERROR":       "#ef4444",   # 빨강
    "APPROVAL":    "#8b5cf6",   # 보라
    "COMPLETE":    "#10a37f",   # 초록
}


class LogViewer:
    """append-only log.md 내용을 실시간으로 표시하는 위젯."""

    def __init__(self, parent: tk.Widget) -> None:
        self.frame = tk.Frame(parent)
        self._build()

    def _build(self) -> None:
        raise NotImplementedError

    def append(self, line: str) -> None:
        raise NotImplementedError
