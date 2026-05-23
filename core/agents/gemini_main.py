# gemini-main 에이전트 — 보조 구현·검색·멀티모달·긴 문서·제3자 검토 실행
from __future__ import annotations

from pathlib import Path

from core.shell import bash_prefix, script_path


def build_cmd(message: str, *, scripts_dir: Path, **_) -> list[str]:
    """gemini-main 호출 명령어를 반환한다."""
    prefix = bash_prefix()
    return prefix + [script_path("ask-gemini.sh", scripts_dir), message]
