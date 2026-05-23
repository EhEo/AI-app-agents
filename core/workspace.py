# 프로젝트 폴더·git 초기화·tasks 디렉터리 관리
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from config import PROJECTS_FILE, SETTINGS_FILE

_GITIGNORE_ENTRIES = [".agents-dev/log/", ".claude/settings.local.json"]

_DEFAULT_CLAUDE_MD = """\
# CLAUDE.md — orchestration policy
이 폴더에서 Claude Code를 실행하면 멀티에이전트 오케스트레이션 모드로 동작합니다.
"""

_DEFAULT_PERMISSIONS = {
    "allow": ["Bash(*)", "Read(*)", "Write(*)", "Edit(*)", "Glob(*)", "Grep(*)"]
}


def bundled_dir() -> Path:
    """PyInstaller 번들 또는 개발 환경의 agents_scripts/ 경로를 반환한다."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "agents_scripts"  # type: ignore[attr-defined]
    return Path(__file__).parent.parent / "agents_scripts"


def ensure_writable(path: Path) -> None:
    """Windows에서 폴더에 현재 사용자 쓰기 권한을 부여한다."""
    if sys.platform != "win32":
        return
    username = os.environ.get("USERNAME", "")
    if not username:
        return
    try:
        subprocess.run(
            ["icacls", str(path), "/grant", f"{username}:(OI)(CI)F", "/T", "/Q"],
            capture_output=True, check=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception:
        pass


def install_bundled_scripts() -> None:
    """번들된 scripts/를 ~/.agents-dev/에 복사한다 (없는 파일만)."""
    src_root = bundled_dir()
    dst_root = Path.home() / ".agents-dev"
    for subdir in ("scripts", "roles"):
        src_dir = src_root / subdir
        if not src_dir.exists():
            continue
        dst_dir = dst_root / subdir
        dst_dir.mkdir(parents=True, exist_ok=True)
        ensure_writable(dst_dir)
        for src_file in src_dir.iterdir():
            shutil.copy2(src_file, dst_dir / src_file.name)


def init_project(folder: Path) -> list[str]:
    """프로젝트 폴더를 초기화하고 결과 메시지 목록을 반환한다."""
    logs: list[str] = []

    # .agents-dev/log/ 생성
    log_dir = folder / ".agents-dev" / "log"
    log_dir.mkdir(parents=True, exist_ok=True)
    ensure_writable(log_dir.parent)
    ensure_writable(log_dir)
    logs.append(f"[✓] .agents-dev/log/ 생성: {log_dir}")

    # tasks/ 폴더 생성 (Reference Code 태스크 관리용)
    tasks_dir = folder / "tasks"
    tasks_dir.mkdir(exist_ok=True)
    logs.append("[✓] tasks/ 폴더 확인됨")

    # git 초기화
    if not (folder / ".git").exists():
        try:
            res = subprocess.run(
                ["git", "init"], cwd=str(folder),
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            logs.append(
                "[✓] git init 완료" if res.returncode == 0
                else f"[⚠] git init 실패: {res.stderr.strip() or 'git 미설치'}"
            )
        except FileNotFoundError:
            logs.append("[⚠] git 미설치 — Codex 리뷰를 위해 git 설치 권장")
    else:
        logs.append("[i] git 저장소 이미 존재")

    # CLAUDE.md
    claude_md = folder / "CLAUDE.md"
    if not claude_md.exists():
        claude_md.write_text(_DEFAULT_CLAUDE_MD, encoding="utf-8")
        logs.append("[✓] CLAUDE.md 생성 완료")
    else:
        logs.append("[i] CLAUDE.md 이미 존재 — 유지함")

    # .claude/settings.json
    claude_dir = folder / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    ensure_writable(claude_dir)
    settings_file = claude_dir / "settings.json"
    if settings_file.exists():
        try:
            existing = json.loads(settings_file.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
        if "permissions" not in existing:
            existing["permissions"] = _DEFAULT_PERMISSIONS
            settings_file.write_text(
                json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            logs.append("[✓] .claude/settings.json — permissions 추가됨")
        else:
            logs.append("[i] .claude/settings.json — 이미 존재, 유지함")
    else:
        settings_file.write_text(
            json.dumps({"permissions": _DEFAULT_PERMISSIONS}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logs.append("[✓] .claude/settings.json 생성")

    # .codex/config.toml
    codex_dir = folder / ".codex"
    codex_dir.mkdir(parents=True, exist_ok=True)
    ensure_writable(codex_dir)
    codex_config = codex_dir / "config.toml"
    _codex_content = '[windows]\nsandbox = "unelevated"\n'
    if not codex_config.exists():
        codex_config.write_text(_codex_content, encoding="utf-8")
        logs.append("[✓] .codex/config.toml 생성")
    else:
        logs.append("[i] .codex/config.toml 이미 존재, 유지함")

    # .gitignore 항목 추가
    gitignore = folder / ".gitignore"
    existing_text = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    if existing_text and not existing_text.endswith("\n"):
        existing_text += "\n"
    existing_lines = {line.strip() for line in existing_text.splitlines()}
    added = [e for e in _GITIGNORE_ENTRIES if e not in existing_lines]
    if added:
        gitignore.write_text(existing_text + "".join(f"{e}\n" for e in added), encoding="utf-8")
        logs.append(f"[✓] .gitignore 갱신: {', '.join(added)}")
    else:
        logs.append("[i] .gitignore — 이미 모든 항목 존재")

    return logs


def load_projects() -> tuple[Path | None, list[dict]]:
    """저장된 기본 폴더와 프로젝트 목록을 반환한다."""
    try:
        if PROJECTS_FILE.exists():
            data = json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return None, [p for p in data if "name" in p and "path" in p]
            base_str = data.get("base")
            base = Path(base_str) if base_str else None
            projects = [p for p in data.get("projects", []) if "name" in p and "path" in p]
            return base, projects
    except Exception:
        pass
    return None, []


def save_projects(base_folder: Path | None, projects: list[dict]) -> None:
    """프로젝트 목록과 기본 폴더를 영구 저장한다."""
    PROJECTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    ensure_writable(PROJECTS_FILE.parent)
    data: dict = {"projects": projects}
    if base_folder:
        data["base"] = str(base_folder)
    PROJECTS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_settings() -> dict:
    """설정 파일을 읽어 반환한다. 없으면 빈 dict."""
    try:
        if SETTINGS_FILE.exists():
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def save_settings(data: dict) -> None:
    """설정을 파일에 저장한다."""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
