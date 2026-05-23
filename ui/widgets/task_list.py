# 태스크 체크리스트 위젯 — task.md 스키마 기반 항목 표시·편집
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from config import FONT_KO, FONT_SIZE_BODY, FONT_SIZE_SMALL

# task.md status 값 → UI 표시 아이콘
_STATUS_ICON: dict[str, str] = {
    "pending":    "○",
    "in_progress": "◐",
    "done":       "●",
    "reviewing":  "◑",
}


class TaskItem:
    """단일 태스크 행 (체크박스 + 제목 + 상태 레이블)."""

    def __init__(self, parent: tk.Widget, task: dict,
                 on_toggle: Callable[[dict], None],
                 bg: str, fg: str, fg_dim: str) -> None:
        self._task = task
        self._on_toggle = on_toggle

        self.frame = tk.Frame(parent, bg=bg)
        self._var = tk.BooleanVar(value=task.get("status") == "done")

        cb = tk.Checkbutton(
            self.frame,
            variable=self._var,
            command=self._toggled,
            bg=bg, activebackground=bg,
            selectcolor=bg,
            relief="flat", bd=0,
        )
        cb.pack(side="left", padx=(4, 0))

        title = task.get("goal", task.get("name", "태스크"))
        lbl = tk.Label(
            self.frame, text=title,
            bg=bg, fg=fg,
            font=(FONT_KO, FONT_SIZE_BODY),
            anchor="w",
        )
        lbl.pack(side="left", fill="x", expand=True, padx=4)

        status = task.get("status", "pending")
        icon = _STATUS_ICON.get(status, "○")
        tk.Label(
            self.frame, text=icon,
            bg=bg, fg=fg_dim,
            font=(FONT_KO, FONT_SIZE_SMALL),
        ).pack(side="right", padx=4)

    def _toggled(self) -> None:
        self._task["status"] = "done" if self._var.get() else "pending"
        self._on_toggle(self._task)


class TaskListWidget:
    """태스크 목록을 체크박스 행으로 표시하고 상태를 관리한다."""

    def __init__(self, parent: tk.Widget,
                 on_task_toggle: Callable[[dict], None] | None = None,
                 bg: str = "#1a1a1a", fg: str = "#ececec",
                 fg_dim: str = "#8e8ea0") -> None:
        self._on_toggle = on_task_toggle or (lambda _: None)
        self._bg  = bg
        self._fg  = fg
        self._fg_dim = fg_dim
        self._items: list[TaskItem] = []

        self.frame = tk.Frame(parent, bg=bg)
        self._canvas = tk.Canvas(self.frame, bg=bg, highlightthickness=0)
        self._inner  = tk.Frame(self._canvas, bg=bg)
        self._scroll = ttk.Scrollbar(self.frame, orient="vertical",
                                     command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._scroll.set)
        self._scroll.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)
        self._win_id = self._canvas.create_window(
            (0, 0), window=self._inner, anchor="nw"
        )
        self._inner.bind("<Configure>", self._update_scroll)
        self._canvas.bind("<Configure>", self._resize_inner)

    def load_tasks(self, tasks: list[dict]) -> None:
        """태스크 목록을 다시 그린다."""
        for item in self._items:
            item.frame.destroy()
        self._items.clear()
        for task in tasks:
            item = TaskItem(
                self._inner, task, self._on_toggle,
                self._bg, self._fg, self._fg_dim,
            )
            item.frame.pack(fill="x", pady=1)
            self._items.append(item)

    def _update_scroll(self, _=None) -> None:
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _resize_inner(self, event) -> None:
        self._canvas.itemconfig(self._win_id, width=event.width)
