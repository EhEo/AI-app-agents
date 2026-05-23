# 태스크 체크리스트 위젯 — task.md 스키마 기반 항목 표시·편집
from __future__ import annotations

import tkinter as tk


class TaskListWidget:
    """태스크 목록을 체크박스로 표시하고 status를 관리한다."""

    def __init__(self, parent: tk.Widget) -> None:
        self.frame = tk.Frame(parent)

    def load_tasks(self, tasks: list[dict]) -> None:
        raise NotImplementedError
