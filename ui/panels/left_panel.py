# 좌측 패널 — 프로젝트 목록·태스크 관리·진행률 표시
from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog
from typing import Callable

from config import FONT_KO, FONT_SIZE_BODY, FONT_SIZE_SMALL
from ui.widgets.common import RoundBtn
from ui.widgets.task_list import TaskListWidget


class LeftPanel:
    """프로젝트 관리 패널 — 프로젝트 선택·태스크 목록·진행률."""

    def __init__(self, parent: tk.Widget,
                 on_project_change: Callable[[Path], None] | None = None,
                 bg: str = "#1a1a1a", bg_dark: str = "#171717",
                 fg: str = "#ececec", fg_dim: str = "#8e8ea0",
                 accent: str = "#10a37f") -> None:
        self._on_project_change = on_project_change or (lambda _: None)
        self._bg      = bg
        self._bg_dark = bg_dark
        self._fg      = fg
        self._fg_dim  = fg_dim
        self._accent  = accent
        self._projects: list[dict] = []
        self._current_project: dict | None = None
        self._tasks: list[dict] = []

        self.frame = tk.Frame(parent, bg=bg)
        self._build()

    def _build(self) -> None:
        # ── 현재 프로젝트 헤더 ────────────────────────────────────────────────
        header = tk.Frame(self.frame, bg=self._bg_dark)
        header.pack(fill="x", padx=0, pady=0)

        tk.Label(header, text="현재 프로젝트",
                 bg=self._bg_dark, fg=self._fg_dim,
                 font=(FONT_KO, FONT_SIZE_SMALL)).pack(anchor="w", padx=10, pady=(8, 0))

        self._proj_var = tk.StringVar(value="— 프로젝트 없음 —")
        self._proj_menu = tk.OptionMenu(header, self._proj_var, "— 프로젝트 없음 —")
        self._proj_menu.config(
            bg=self._bg_dark, fg=self._fg, activebackground=self._bg,
            font=(FONT_KO, FONT_SIZE_BODY), relief="flat", bd=0,
            highlightthickness=0,
        )
        self._proj_menu["menu"].config(
            bg=self._bg_dark, fg=self._fg, font=(FONT_KO, FONT_SIZE_BODY)
        )
        self._proj_menu.pack(fill="x", padx=6, pady=(2, 8))
        self._proj_var.trace_add("write", self._on_proj_select)

        # ── 진행률 바 ─────────────────────────────────────────────────────────
        prog_frame = tk.Frame(self.frame, bg=self._bg)
        prog_frame.pack(fill="x", padx=10, pady=(4, 2))
        self._prog_lbl = tk.Label(
            prog_frame, text="진행률  0 / 0",
            bg=self._bg, fg=self._fg_dim,
            font=(FONT_KO, FONT_SIZE_SMALL), anchor="w",
        )
        self._prog_lbl.pack(fill="x")
        self._prog_bar_bg = tk.Frame(prog_frame, bg=self._bg_dark, height=4)
        self._prog_bar_bg.pack(fill="x", pady=(2, 0))
        self._prog_bar_fg = tk.Frame(self._prog_bar_bg, bg=self._accent, height=4)
        self._prog_bar_fg.place(x=0, y=0, relheight=1, relwidth=0)

        # ── 태스크 구분선 ────────────────────────────────────────────────────
        sep_frame = tk.Frame(self.frame, bg=self._bg)
        sep_frame.pack(fill="x", padx=10, pady=(8, 2))
        tk.Label(sep_frame, text="태스크",
                 bg=self._bg, fg=self._fg_dim,
                 font=(FONT_KO, FONT_SIZE_SMALL)).pack(side="left")
        RoundBtn(sep_frame, "+ 추가", self._add_task,
                 color=self._accent, fontsize=7,
                 width=40, height=16).pack(side="right")

        # ── 태스크 목록 ──────────────────────────────────────────────────────
        self._task_list = TaskListWidget(
            self.frame,
            on_task_toggle=self._on_task_toggle,
            bg=self._bg, fg=self._fg, fg_dim=self._fg_dim,
        )
        self._task_list.frame.pack(fill="both", expand=True, padx=4, pady=4)

        # ── 프로젝트 목록 구분선 ─────────────────────────────────────────────
        tk.Frame(self.frame, bg=self._bg_dark, height=1).pack(fill="x")
        proj_sec = tk.Frame(self.frame, bg=self._bg)
        proj_sec.pack(fill="x", padx=10, pady=(6, 2))
        tk.Label(proj_sec, text="프로젝트 목록",
                 bg=self._bg, fg=self._fg_dim,
                 font=(FONT_KO, FONT_SIZE_SMALL)).pack(side="left")

        # ── 프로젝트 리스트박스 ──────────────────────────────────────────────
        list_frame = tk.Frame(self.frame, bg=self._bg)
        list_frame.pack(fill="x", padx=6, pady=(0, 4))
        self._proj_listbox = tk.Listbox(
            list_frame, bg=self._bg, fg=self._fg,
            font=(FONT_KO, FONT_SIZE_BODY),
            selectbackground=self._accent, activestyle="none",
            relief="flat", bd=0, highlightthickness=0,
            height=4,
        )
        self._proj_listbox.pack(fill="x")
        self._proj_listbox.bind("<<ListboxSelect>>", self._on_listbox_select)

        # ── 새 프로젝트 버튼 ─────────────────────────────────────────────────
        RoundBtn(self.frame, "+ 새 프로젝트", self._new_project,
                 color=self._accent, fontsize=FONT_SIZE_SMALL,
                 height=24).pack(fill="x", padx=8, pady=(2, 8))

    # ── 공개 인터페이스 ───────────────────────────────────────────────────────

    def load_projects(self, projects: list[dict], current_name: str | None = None) -> None:
        """프로젝트 목록을 갱신한다."""
        self._projects = projects
        names = [p["name"] for p in projects] or ["— 프로젝트 없음 —"]

        menu = self._proj_menu["menu"]
        menu.delete(0, "end")
        for name in names:
            menu.add_command(label=name,
                             command=lambda n=name: self._proj_var.set(n))

        self._proj_listbox.delete(0, "end")
        for name in [p["name"] for p in projects]:
            self._proj_listbox.insert("end", f"📁 {name}")

        if current_name and current_name in names:
            self._proj_var.set(current_name)
        elif names:
            self._proj_var.set(names[0])

    def load_tasks(self, tasks: list[dict]) -> None:
        """태스크 목록을 갱신하고 진행률을 업데이트한다."""
        self._tasks = tasks
        self._task_list.load_tasks(tasks)
        self._update_progress()

    # ── 내부 이벤트 ──────────────────────────────────────────────────────────

    def _on_proj_select(self, *_) -> None:
        name = self._proj_var.get()
        proj = next((p for p in self._projects if p["name"] == name), None)
        if proj:
            self._current_project = proj
            self._on_project_change(Path(proj["path"]))
            self._load_project_tasks(Path(proj["path"]))

    def _on_listbox_select(self, _) -> None:
        sel = self._proj_listbox.curselection()
        if sel and sel[0] < len(self._projects):
            name = self._projects[sel[0]]["name"]
            self._proj_var.set(name)

    def _on_task_toggle(self, task: dict) -> None:
        self._save_tasks()
        self._update_progress()

    def _add_task(self) -> None:
        goal = simpledialog.askstring("태스크 추가", "태스크 목표를 입력하세요.")
        if not goal:
            return
        self._tasks.append({"goal": goal, "status": "pending"})
        self._task_list.load_tasks(self._tasks)
        self._save_tasks()
        self._update_progress()

    def _new_project(self) -> None:
        messagebox.showinfo("새 프로젝트", "설정 화면에서 기본 폴더를 선택 후 프로젝트를 추가하세요.")

    def _load_project_tasks(self, folder: Path) -> None:
        """프로젝트 폴더의 tasks.json을 읽어 태스크 목록을 갱신한다."""
        tasks_file = folder / ".agents-dev" / "tasks.json"
        if tasks_file.exists():
            try:
                self._tasks = json.loads(tasks_file.read_text(encoding="utf-8"))
            except Exception:
                self._tasks = []
        else:
            self._tasks = []
        self._task_list.load_tasks(self._tasks)
        self._update_progress()

    def _save_tasks(self) -> None:
        if not self._current_project:
            return
        tasks_file = Path(self._current_project["path"]) / ".agents-dev" / "tasks.json"
        tasks_file.parent.mkdir(parents=True, exist_ok=True)
        tasks_file.write_text(
            json.dumps(self._tasks, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _update_progress(self) -> None:
        total = len(self._tasks)
        done  = sum(1 for t in self._tasks if t.get("status") == "done")
        self._prog_lbl.config(text=f"진행률  {done} / {total}")
        ratio = done / total if total else 0
        self._prog_bar_fg.place(relwidth=ratio)
