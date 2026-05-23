# 에이전트 간 작업 흐름 관리 — 라우팅·순서·승인 게이트 제어
from __future__ import annotations


# 작업 유형 → 권장 최소 에이전트 셋 (routing.md 기반)
ROUTING_TABLE: dict[str, list[str]] = {
    "coding":    ["claude-main"],
    "review":    ["claude-main", "codex-critic"],
    "implement": ["codex-main"],
    "research":  ["gemini-main"],
    "full":      ["claude-main", "codex-main", "gemini-main", "codex-critic"],
}
