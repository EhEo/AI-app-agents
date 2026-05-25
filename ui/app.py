# Agent Launcher v2 메인 윈도우 — 좌우 분할 레이아웃 초기화 및 폴링 루프
from __future__ import annotations

import queue
import tkinter as tk
from pathlib import Path

from config import FONT_KO, FONT_SIZE_SMALL, THEMES, DEFAULT_THEME
from core.log_watcher import LogWatcher
from core.workspace import install_bundled_scripts, load_projects, save_projects
from ui.panels.left_panel import LeftPanel
from ui.panels.right_panel import RightPanel
from ui.screens.settings_screen import SettingsScreen


class AgentLauncherApp(tk.Tk):
    """Agent Launcher v2 메인 윈도우 — 좌우 분할 레이아웃."""

    _SASH_POS = 280   # 초기 분할 위치 (좌측 패널 너비)

    def __init__(self) -> None:
        install_bundled_scripts()
        super().__init__()
        self.title("Agent Launcher v2")
        self.minsize(1000, 660)
        self.resizable(True, True)

        self._theme_name = DEFAULT_THEME
        self._theme = THEMES[self._theme_name]
        self._event_queue: queue.Queue = queue.Queue()
        self._log_watcher = LogWatcher(self._event_queue)

        # 저장된 프로젝트 로드
        self._base_folder, self._projects = load_projects()
        self._current_folder: Path | None = self._base_folder

        self.configure(bg=self._theme.bg)
        self._build_ui()
        self._apply_theme()

        # 저장된 프로젝트 목록 좌측 패널에 표시
        if self._projects:
            first_name = self._projects[0]["name"] if self._projects else None
            self._left.load_projects(self._projects, first_name)

        self._log_watcher.start()
        self._poll()

    # ── UI 구성 ──────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        t = self._theme

        # 상단 바 (타이틀 + 설정 버튼)
        top_bar = tk.Frame(self, bg=t.bg_dark, height=36)
        top_bar.pack(fill="x", side="top")
        top_bar.pack_propagate(False)
        tk.Label(top_bar, text="Agent Launcher v2",
                 bg=t.bg_dark, fg=t.text,
                 font=(FONT_KO, 10, "bold")).pack(side="left", padx=12, pady=6)
        settings_lbl = tk.Label(top_bar, text="설정",
                                 bg=t.bg_dark, fg=t.text_dim,
                                 font=(FONT_KO, FONT_SIZE_SMALL),
                                 cursor="hand2")
        settings_lbl.pack(side="right", padx=12, pady=6)
        settings_lbl.bind("<Button-1>", lambda _: self._open_settings())

        # 좌우 분할 PanedWindow
        self._paned = tk.PanedWindow(
            self, orient="horizontal",
            bg=t.bg_dark, sashwidth=4, sashrelief="flat",
            showhandle=False,
        )
        self._paned.pack(fill="both", expand=True)

        # 좌측 패널
        self._left = LeftPanel(
            self._paned,
            on_project_change=self._on_project_change,
            bg=t.bg_panel, bg_dark=t.bg_dark,
            fg=t.text, fg_dim=t.text_dim,
        )
        self._paned.add(self._left.frame, minsize=220, width=self._SASH_POS)

        # 우측 패널
        self._right = RightPanel(
            self._paned,
            bg=t.bg, bg_dark=t.bg_dark, bg_input=t.bg_input,
            fg=t.text, fg_dim=t.text_dim,
        )
        self._paned.add(self._right.frame, minsize=400)

    # ── 폴링 루프 ─────────────────────────────────────────────────────────────

    def _poll(self) -> None:
        """80ms 주기 폴링 — 로그 이벤트 소비 + 스트리밍 출력 처리."""
        try:
            while True:
                event = self._event_queue.get_nowait()
                self._right.push_event(event)
        except queue.Empty:
            pass
        self._right.poll_output()
        self.after(80, self._poll)

    # ── 이벤트 핸들러 ────────────────────────────────────────────────────────

    def _on_project_change(self, folder: Path) -> None:
        self._current_folder = folder
        self._right.set_folder(folder)
        self._log_watcher.set_project(folder)

    def _open_settings(self) -> None:
        t = self._theme
        SettingsScreen(
            self,
            on_save=self._on_settings_save,
            bg=t.bg, fg=t.text, fg_dim=t.text_dim,
        )

    def _on_settings_save(self, settings: dict) -> None:
        """설정 저장 후 프로젝트 목록과 테마를 갱신한다."""
        new_theme = settings.get("theme", self._theme_name)
        if new_theme != self._theme_name:
            self._theme_name = new_theme
            self._theme = THEMES[new_theme]
            self._apply_theme()

        projects = settings.get("projects", [])
        if projects:
            self._projects = projects
            base_str = settings.get("base_folder", "")
            self._base_folder = Path(base_str) if base_str else None
            save_projects(self._base_folder, self._projects)
            current = self._projects[0]["name"] if self._projects else None
            self._left.load_projects(self._projects, current)

    def _apply_theme(self) -> None:
        t = self._theme
        self.configure(bg=t.bg)

    def on_close(self) -> None:
        self._log_watcher.stop()
        self.destroy()
