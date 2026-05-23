# 설정 화면 — 기본 폴더 선택·에이전트 설정·테마 전환
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Callable

from config import FONT_KO, FONT_SIZE_BODY, FONT_SIZE_SMALL, THEMES
from core.workspace import load_settings, save_settings, init_project
from ui.widgets.common import RoundBtn


class SettingsScreen(tk.Toplevel):
    """설정 팝업 — 기본 폴더·프로젝트 추가·테마 선택."""

    def __init__(self, parent: tk.Widget,
                 on_save: Callable[[dict], None] | None = None,
                 bg: str = "#212121", fg: str = "#ececec",
                 fg_dim: str = "#8e8ea0", accent: str = "#10a37f") -> None:
        super().__init__(parent)
        self.title("설정")
        self.resizable(False, False)
        self.grab_set()  # 모달 동작

        self._on_save = on_save or (lambda _: None)
        self._bg      = bg
        self._fg      = fg
        self._fg_dim  = fg_dim
        self._accent  = accent
        self._settings = load_settings()

        self.configure(bg=bg)
        self._build()
        self._load_values()

    def _build(self) -> None:
        pad = {"padx": 16, "pady": 6}

        # ── 기본 폴더 ─────────────────────────────────────────────────────────
        self._section("기본 작업 폴더")

        row = tk.Frame(self, bg=self._bg)
        row.pack(fill="x", **pad)
        self._base_var = tk.StringVar()
        tk.Entry(row, textvariable=self._base_var,
                 bg="#2f2f2f", fg=self._fg,
                 font=(FONT_KO, FONT_SIZE_BODY),
                 relief="flat", bd=4, width=36,
                 insertbackground=self._fg).pack(side="left", padx=(0, 6))
        RoundBtn(row, "찾아보기", self._browse_base,
                 color=self._accent, fontsize=FONT_SIZE_SMALL,
                 width=60, height=24).pack(side="left")

        # ── 새 프로젝트 추가 ──────────────────────────────────────────────────
        self._section("새 프로젝트 추가")

        proj_row = tk.Frame(self, bg=self._bg)
        proj_row.pack(fill="x", **pad)
        self._proj_name_var = tk.StringVar()
        tk.Label(proj_row, text="이름",
                 bg=self._bg, fg=self._fg_dim,
                 font=(FONT_KO, FONT_SIZE_SMALL)).pack(side="left")
        tk.Entry(proj_row, textvariable=self._proj_name_var,
                 bg="#2f2f2f", fg=self._fg,
                 font=(FONT_KO, FONT_SIZE_BODY),
                 relief="flat", bd=4, width=16,
                 insertbackground=self._fg).pack(side="left", padx=6)

        self._proj_path_var = tk.StringVar()
        tk.Label(proj_row, text="경로",
                 bg=self._bg, fg=self._fg_dim,
                 font=(FONT_KO, FONT_SIZE_SMALL)).pack(side="left")
        tk.Entry(proj_row, textvariable=self._proj_path_var,
                 bg="#2f2f2f", fg=self._fg,
                 font=(FONT_KO, FONT_SIZE_BODY),
                 relief="flat", bd=4, width=18,
                 insertbackground=self._fg).pack(side="left", padx=6)
        RoundBtn(proj_row, "폴더", self._browse_proj,
                 color=self._accent, fontsize=FONT_SIZE_SMALL,
                 width=40, height=24).pack(side="left", padx=(0, 6))
        RoundBtn(proj_row, "초기화 + 추가", self._add_project,
                 color=self._accent, fontsize=FONT_SIZE_SMALL,
                 width=80, height=24).pack(side="left")

        # ── 초기화 결과 로그 ──────────────────────────────────────────────────
        self._log_text = tk.Text(
            self, bg="#171717", fg=self._fg,
            font=(FONT_KO, FONT_SIZE_SMALL),
            height=5, state="disabled",
            relief="flat", bd=0, highlightthickness=0,
        )
        self._log_text.pack(fill="x", padx=16, pady=4)

        # ── 테마 ──────────────────────────────────────────────────────────────
        self._section("테마")
        theme_row = tk.Frame(self, bg=self._bg)
        theme_row.pack(fill="x", **pad)
        self._theme_var = tk.StringVar(value="dark")
        for t in THEMES:
            tk.Radiobutton(
                theme_row, text=t,
                variable=self._theme_var, value=t,
                bg=self._bg, fg=self._fg,
                activebackground=self._bg,
                selectcolor=self._bg,
                font=(FONT_KO, FONT_SIZE_BODY),
            ).pack(side="left", padx=8)

        # ── 저장 버튼 ─────────────────────────────────────────────────────────
        btn_row = tk.Frame(self, bg=self._bg)
        btn_row.pack(fill="x", padx=16, pady=(8, 12))
        RoundBtn(btn_row, "저장", self._save,
                 color=self._accent, fontsize=FONT_SIZE_BODY,
                 height=28).pack(fill="x")

    def _section(self, title: str) -> None:
        tk.Label(self, text=title,
                 bg=self._bg, fg=self._fg_dim,
                 font=(FONT_KO, FONT_SIZE_SMALL, "bold"),
                 anchor="w").pack(fill="x", padx=16, pady=(12, 0))
        tk.Frame(self, bg="#3a3a3a", height=1).pack(fill="x", padx=16)

    def _load_values(self) -> None:
        self._base_var.set(self._settings.get("base_folder", ""))
        self._theme_var.set(self._settings.get("theme", "dark"))

    def _browse_base(self) -> None:
        path = filedialog.askdirectory(title="기본 작업 폴더 선택")
        if path:
            self._base_var.set(path)

    def _browse_proj(self) -> None:
        path = filedialog.askdirectory(title="프로젝트 폴더 선택")
        if path:
            self._proj_path_var.set(path)
            if not self._proj_name_var.get():
                self._proj_name_var.set(Path(path).name)

    def _add_project(self) -> None:
        name = self._proj_name_var.get().strip()
        path_str = self._proj_path_var.get().strip()
        if not name or not path_str:
            return
        folder = Path(path_str)
        logs = init_project(folder)
        self._append_log("\n".join(logs))

        projects = self._settings.get("projects", [])
        if not any(p["name"] == name for p in projects):
            projects.append({"name": name, "path": path_str})
        self._settings["projects"] = projects

    def _append_log(self, text: str) -> None:
        self._log_text.configure(state="normal")
        self._log_text.insert("end", text + "\n")
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def _save(self) -> None:
        self._settings["base_folder"] = self._base_var.get().strip()
        self._settings["theme"]       = self._theme_var.get()
        save_settings(self._settings)
        self._on_save(self._settings)
        self.destroy()
