# Agent Launcher v2 진입점 — UI 초기화 및 앱 실행
from ui.app import AgentLauncherApp


def main() -> None:
    app = AgentLauncherApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()


if __name__ == "__main__":
    main()
