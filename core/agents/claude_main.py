# claude-main 에이전트 — 오케스트레이션·메인 코딩·설계·아키텍처·전략 실행
from __future__ import annotations

import sys


def build_cmd(message: str, *, first: bool = True, folder: str = "") -> list[str]:
    """claude-main 호출 명령어를 반환한다.

    Windows에서 claude는 .cmd 확장자이므로 cmd /c 로 감싼다.
    first=False 이면 --continue 플래그를 추가해 대화를 이어간다.
    """
    base = ["claude", "-p", message]
    if not first:
        base.append("--continue")
    return (["cmd", "/c"] + base) if sys.platform == "win32" else base
