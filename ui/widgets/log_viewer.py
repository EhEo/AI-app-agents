# 로그 뷰어 위젯 — log.md 6-태그 컬러링·에이전트별 필터링
from __future__ import annotations

import queue
import tkinter as tk
from tkinter import ttk

from config import FONT_KO, FONT_SIZE_BODY, FONT_SIZE_SMALL, AGENTS
from core.log_watcher import LogEvent

# 태그별 강조 색상
TAG_COLORS: dict[str, str] = {
    "DECISION":    "#4285f4",
    "WORKER_CALL": "#10a37f",
    "VERIFICATION":"#f59e0b",
    "ERROR":       "#ef4444",
    "APPROVAL":    "#8b5cf6",
    "COMPLETE":    "#10a37f",
}

# 에이전트 키 → 강조 색상 (config.py 기반)
_AGENT_COLORS: dict[str, str] = {a.key: a.accent for a in AGENTS}


class LogViewer:
    """에이전트 출력과 task_log 이벤트를 실시간으로 표시하는 위젯.

    에이전트 탭 버튼으로 필터링, 6종 log 태그 컬러링 지원.
    """

    _ALL = "전체"

    def __init__(self, parent: tk.Widget,
                 bg: str = "#212121", bg_dark: str = "#171717",
                 fg: str = "#ececec", fg_dim: str = "#8e8ea0") -> None:
        self._bg     = bg
        self._bg_dark = bg_dark
        self._fg     = fg
        self._fg_dim = fg_dim
        self._filter: str = self._ALL  # 현재 필터 에이전트 키

        self.frame = tk.Frame(parent, bg=bg)
        self._build()

    def _build(self) -> None:
        # ── 에이전트 필터 탭 바 ───────────────────────────────────────────────
        tab_bar = tk.Frame(self.frame, bg=self._bg_dark)
        tab_bar.pack(fill="x")

        self._tab_btns: dict[str, tk.Label] = {}
        for label in [self._ALL] + [a.label for a in AGENTS]:
            key = self._ALL if label == self._ALL else next(
                (a.key for a in AGENTS if a.label == label), label
            )
            btn = tk.Label(
                tab_bar, text=label,
                bg=self._bg_dark, fg=self._fg_dim,
                font=(FONT_KO, FONT_SIZE_SMALL),
                padx=10, pady=4, cursor="hand2",
            )
            btn.pack(side="left")
            btn.bind("<Button-1>", lambda _, k=key: self._set_filter(k))
            self._tab_btns[key] = btn
        self._set_filter(self._ALL)

        # ── 텍스트 출력 영역 ─────────────────────────────────────────────────
        text_frame = tk.Frame(self.frame, bg=self._bg)
        text_frame.pack(fill="both", expand=True)

        self._text = tk.Text(
            text_frame,
            bg=self._bg, fg=self._fg,
            font=(FONT_KO, FONT_SIZE_BODY),
            wrap="word", state="disabled",
            relief="flat", bd=0,
            highlightthickness=0,
            selectbackground="#3a3a3a",
        )
        scrollbar = ttk.Scrollbar(text_frame, command=self._text.yview)
        self._text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._text.pack(side="left", fill="both", expand=True)

        # 텍스트 태그 정의
        self._text.tag_configure("agent_lbl",
                                 font=(FONT_KO, FONT_SIZE_SMALL, "bold"))
        self._text.tag_configure("query_lbl",
                                 foreground=self._fg_dim,
                                 font=(FONT_KO, FONT_SIZE_SMALL))
        self._text.tag_configure("body",
                                 font=(FONT_KO, FONT_SIZE_BODY))
        for tag, color in TAG_COLORS.items():
            self._text.tag_configure(f"tag_{tag}", foreground=color,
                                     font=(FONT_KO, FONT_SIZE_SMALL, "bold"))
        for key, color in _AGENT_COLORS.items():
            self._text.tag_configure(f"agent_{key}", foreground=color)

    def append(self, event: LogEvent) -> None:
        """LogEvent 하나를 텍스트 영역에 추가한다."""
        # 필터 적용
        if self._filter != self._ALL and event["agent"] != self._filter:
            return

        self._text.configure(state="normal")

        if event["source"] == "agent_response":
            self._append_agent_response(event)
        else:
            self._append_task_log(event)

        self._text.see("end")
        self._text.configure(state="disabled")

    def append_raw(self, agent_key: str, line: str) -> None:
        """스트리밍 출력 한 줄을 실시간으로 추가한다."""
        if self._filter not in (self._ALL, agent_key):
            return
        self._text.configure(state="normal")
        self._text.insert("end", line, (f"agent_{agent_key}", "body"))
        self._text.see("end")
        self._text.configure(state="disabled")

    def clear(self) -> None:
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.configure(state="disabled")

    # ── 내부 렌더링 ───────────────────────────────────────────────────────────

    def _append_agent_response(self, event: LogEvent) -> None:
        agent_key = event["agent"]
        color_tag = f"agent_{agent_key}"
        agent_def = next((a for a in AGENTS if a.key == agent_key), None)
        label = agent_def.label if agent_def else agent_key

        if event.get("query"):
            self._text.insert("end", f"\n You → {label}\n", "query_lbl")
            self._text.insert("end", f"{event['query']}\n", "query_lbl")
        self._text.insert("end", f"\n● {label}\n", (color_tag, "agent_lbl"))
        self._text.insert("end", event["text"] + "\n", "body")
        self._text.insert("end", "\n")

    def _append_task_log(self, event: LogEvent) -> None:
        tag = event.get("tag", "")
        line = event.get("text", "")
        text_tag = f"tag_{tag}" if tag else "body"
        self._text.insert("end", line + "\n", text_tag)

    def _set_filter(self, key: str) -> None:
        self._filter = key
        for k, btn in self._tab_btns.items():
            is_active = k == key
            btn.config(
                fg=self._fg if is_active else self._fg_dim,
                bg=self._bg if is_active else self._bg_dark,
            )
