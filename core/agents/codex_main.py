# codex-main 에이전트 — 보조 구현·코드 분석·테스트·diff·로컬 검증 실행
from __future__ import annotations


def build_cmd(message: str, **kwargs) -> list[str]:
    """codex-main 호출 명령어를 반환한다."""
    raise NotImplementedError
