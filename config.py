# Agent Launcher v2 전역 설정 — 에이전트 정의·테마·색상 상수
from __future__ import annotations

from dataclasses import dataclass, field


# ── 에이전트 정의 ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AgentDef:
    key: str          # 내부 식별자
    label: str        # UI 표시명
    accent: str       # 강조 색상 (hex)
    role: str         # 역할 한 줄 설명
    log_prefix: str   # log.md에서 이 에이전트 식별에 쓰는 접두어


AGENTS: list[AgentDef] = [
    AgentDef(
        key="claude-main",
        label="Claude",
        accent="#10a37f",
        role="오케스트레이션 · 메인 코딩 · 설계 · 아키텍처 · 전략",
        log_prefix="claude",
    ),
    AgentDef(
        key="codex-main",
        label="Codex",
        accent="#4285f4",
        role="보조 구현 · 코드 분석 · 테스트 · diff · 로컬 검증",
        log_prefix="codex",
    ),
    AgentDef(
        key="gemini-main",
        label="Gemini",
        accent="#f59e0b",
        role="보조 구현 · 검색 · 멀티모달 · 긴 문서 · 제3자 검토",
        log_prefix="gemini",
    ),
    AgentDef(
        key="codex-critic",
        label="Critic",
        accent="#8b5cf6",
        role="산출물 리뷰 · 비평 전담",
        log_prefix="critic",
    ),
]

AGENT_BY_KEY: dict[str, AgentDef] = {a.key: a for a in AGENTS}


# ── 테마 ───────────────────────────────────────────────────────────────────────

@dataclass
class Theme:
    bg: str
    bg_dark: str
    bg_input: str
    bg_panel: str      # 좌측 패널 배경
    text: str
    text_dim: str
    border: str


THEMES: dict[str, Theme] = {
    "dark": Theme(
        bg="#212121",
        bg_dark="#171717",
        bg_input="#2f2f2f",
        bg_panel="#1a1a1a",
        text="#ececec",
        text_dim="#8e8ea0",
        border="#3a3a3a",
    ),
    "light": Theme(
        bg="#f7f7f8",
        bg_dark="#efefef",
        bg_input="#e8e8ec",
        bg_panel="#f0f0f2",
        text="#111111",
        text_dim="#6b6b80",
        border="#d0d0d8",
    ),
}

DEFAULT_THEME = "dark"
FONT_KO = "맑은 고딕"
FONT_SIZE_BODY = 9
FONT_SIZE_SMALL = 8

# 스피너 프레임 (응답 대기 애니메이션)
SPINNER_FRAMES = ["◐", "◓", "◑", "◒"]

# ── 경로 설정 ─────────────────────────────────────────────────────────────────

from pathlib import Path

AGENTS_DEV_DIR  = Path.home() / ".agents-dev"
SCRIPTS_DIR     = AGENTS_DEV_DIR / "scripts"
PROJECTS_FILE   = AGENTS_DEV_DIR / "projects.json"
SETTINGS_FILE   = AGENTS_DEV_DIR / "settings.json"
