# 에이전트 간 작업 흐름 관리 — 라우팅·순서·승인 게이트 제어
from __future__ import annotations

import queue
import subprocess
import threading
from pathlib import Path
from typing import Callable

from config import SCRIPTS_DIR, AGENT_BY_KEY
import core.agents.claude_main as _claude
import core.agents.codex_main as _codex
import core.agents.gemini_main as _gemini
import core.agents.codex_critic as _critic

# 작업 유형 → 권장 최소 에이전트 셋 (routing.md 기반)
ROUTING_TABLE: dict[str, list[str]] = {
    "coding":    ["claude-main"],
    "review":    ["claude-main", "codex-critic"],
    "implement": ["codex-main"],
    "research":  ["gemini-main"],
    "full":      ["claude-main", "codex-main", "gemini-main", "codex-critic"],
}

_CMD_BUILDERS: dict[str, Callable[..., list[str]]] = {
    "claude-main":  lambda msg, **kw: _claude.build_cmd(msg, **kw),
    "codex-main":   lambda msg, **kw: _codex.build_cmd(msg, scripts_dir=SCRIPTS_DIR, **kw),
    "gemini-main":  lambda msg, **kw: _gemini.build_cmd(msg, scripts_dir=SCRIPTS_DIR, **kw),
    "codex-critic": lambda msg, **kw: _critic.build_cmd(msg, scripts_dir=SCRIPTS_DIR, **kw),
}


def build_cmd(agent_key: str, message: str, **kwargs) -> list[str]:
    """에이전트 키와 메시지로 실행 명령어 리스트를 반환한다."""
    builder = _CMD_BUILDERS.get(agent_key)
    if builder is None:
        raise ValueError(f"알 수 없는 에이전트 키: {agent_key}")
    return builder(message, **kwargs)


def run_agent(
    agent_key: str,
    message: str,
    folder: Path,
    out_queue: queue.Queue[str],
    *,
    first: bool = True,
    on_done: Callable[[int], None] | None = None,
) -> threading.Thread:
    """에이전트를 백그라운드 스레드에서 실행하고 출력을 out_queue에 넣는다.

    스트리밍 출력은 한 줄씩 큐에 쌓이고, 완료 시 on_done(returncode)가 호출된다.
    """
    cmd = build_cmd(agent_key, message, first=first)

    def _run() -> None:
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(folder),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if _is_win() else 0,
            )
            assert proc.stdout
            for line in proc.stdout:
                out_queue.put(line)
            proc.wait()
            if on_done:
                on_done(proc.returncode)
        except Exception as e:
            out_queue.put(f"[ERROR] {e}\n")
            if on_done:
                on_done(-1)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t


def _is_win() -> bool:
    import sys
    return sys.platform == "win32"
