# codex-critic 에이전트 — 산출물 리뷰·비평 전담 실행 (read-only, adversarial 모드)
from __future__ import annotations

from pathlib import Path

from core.shell import bash_prefix, script_path

# 비평 모드 지시문 — 모든 codex-critic 호출에 앞에 삽입
_CRITIC_PREFIX = "[비평 모드] 아래 산출물을 실현 가능성·비용·테스트 커버리지·사이드 이펙트 관점에서 비판적으로 검토하라. 수정 제안을 구체적으로 명시할 것.\n\n"


def build_cmd(message: str, *, scripts_dir: Path, **_) -> list[str]:
    """codex-critic 호출 명령어를 반환한다.

    ask-codex.sh를 재사용하되 비평 모드 지시문을 메시지 앞에 삽입한다.
    """
    prefix = bash_prefix()
    critic_message = _CRITIC_PREFIX + message
    return prefix + [script_path("ask-codex.sh", scripts_dir), critic_message]
