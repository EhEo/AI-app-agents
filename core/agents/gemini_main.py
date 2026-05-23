# gemini-main 에이전트 — 보조 구현·검색·멀티모달·긴 문서·제3자 검토 실행
from __future__ import annotations


def build_cmd(message: str, **kwargs) -> list[str]:
    """gemini-main 호출 명령어를 반환한다."""
    raise NotImplementedError
