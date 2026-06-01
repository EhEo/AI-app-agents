# agents_gui 핵심 로직 함수에 대한 단위 테스트
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from pathlib import Path


# ── init_agents_workspace 테스트 ──────────────────────────────────────


def test_creates_agents_dev_log_dir(tmp_path):
    """빈 폴더에서 초기화하면 .agents-dev/log/ 가 생성된다."""
    from agents_gui import init_agents_workspace
    init_agents_workspace(tmp_path)
    assert (tmp_path / ".agents-dev" / "log").is_dir()


def test_creates_claude_md(tmp_path):
    """CLAUDE.md 파일이 생성된다."""
    from agents_gui import init_agents_workspace
    init_agents_workspace(tmp_path)
    assert (tmp_path / "CLAUDE.md").exists()


def test_claude_md_not_empty(tmp_path):
    """생성된 CLAUDE.md 는 비어 있지 않다."""
    from agents_gui import init_agents_workspace
    init_agents_workspace(tmp_path)
    content = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert len(content) > 100


def test_gitignore_entries_added(tmp_path):
    """.gitignore 에 두 항목이 추가된다."""
    from agents_gui import init_agents_workspace
    init_agents_workspace(tmp_path)
    text = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert ".agents-dev/log/" in text
    assert ".claude/settings.local.json" in text


def test_gitignore_no_duplicate(tmp_path):
    """같은 항목이 이미 있으면 중복 추가하지 않는다."""
    from agents_gui import init_agents_workspace
    existing = ".agents-dev/log/\n.claude/settings.local.json\n"
    (tmp_path / ".gitignore").write_text(existing, encoding="utf-8")
    init_agents_workspace(tmp_path)
    text = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert text.count(".agents-dev/log/") == 1
    assert text.count(".claude/settings.local.json") == 1


def test_returns_log_lines(tmp_path):
    """반환값은 비어 있지 않은 문자열 리스트다."""
    from agents_gui import init_agents_workspace
    logs = init_agents_workspace(tmp_path)
    assert isinstance(logs, list)
    assert len(logs) > 0
    assert all(isinstance(line, str) for line in logs)


def test_already_initialized_keeps_existing_claude_md(tmp_path):
    """이미 CLAUDE.md 가 있으면 백업도 덮어쓰기도 하지 않고 그대로 유지한다."""
    from agents_gui import init_agents_workspace
    (tmp_path / "CLAUDE.md").write_text("old content", encoding="utf-8")
    init_agents_workspace(tmp_path)
    assert not (tmp_path / "CLAUDE.md.bak").exists()
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == "old content"


def test_launch_returns_false_when_no_claude(tmp_path, monkeypatch):
    """claude CLI 가 PATH 에 없을 때 False 를 반환한다."""
    from agents_gui import launch_claude_session
    monkeypatch.setenv("PATH", "")
    result = launch_claude_session(tmp_path, dry_run=True)
    assert result is False


def test_gitignore_comment_containing_entry_does_not_block_addition(tmp_path):
    """주석 줄이 항목 문자열을 포함해도 실제 규칙이 추가된다."""
    from agents_gui import init_agents_workspace
    # 주석으로 항목 문자열을 포함하는 .gitignore
    tricky = "# do NOT ignore .agents-dev/log/ here\n"
    (tmp_path / ".gitignore").write_text(tricky, encoding="utf-8")
    init_agents_workspace(tmp_path)
    lines = (tmp_path / ".gitignore").read_text(encoding="utf-8").splitlines()
    stripped = [l.strip() for l in lines]
    assert ".agents-dev/log/" in stripped


# ── install_bundled_scripts 테스트 (터미널 런처 영구화) ──────────────────


def test_install_bundled_scripts_populates_bin_and_template(tmp_path):
    """번들 설치 시 ~/bin 런처와 ~/.agents-dev/CLAUDE.md.template 이 배치된다."""
    from core.workspace import install_bundled_scripts
    install_bundled_scripts(home=tmp_path)
    assert (tmp_path / "bin" / "agents-init").is_file()
    assert (tmp_path / "bin" / "agent-init").is_file()
    assert (tmp_path / "bin" / "install-tmux.sh").is_file()
    assert (tmp_path / ".agents-dev" / "CLAUDE.md.template").is_file()
    assert (tmp_path / ".agents-dev" / "scripts" / "team-layout.sh").is_file()
    assert (tmp_path / ".agents-dev" / "roles" / "reviewer.md").is_file()


def test_bundled_launcher_keeps_lf_endings(tmp_path):
    """설치된 agents-init 은 LF 줄끝이어야 한다(CRLF 면 bash 에서 깨짐)."""
    from core.workspace import install_bundled_scripts
    install_bundled_scripts(home=tmp_path)
    raw = (tmp_path / "bin" / "agents-init").read_bytes()
    assert b"\r\n" not in raw


def test_agents_gui_install_mirrors_core(tmp_path):
    """레거시 agents_gui.install_bundled_scripts(.exe 진입점)도 동일하게 ~/bin 런처를 설치한다."""
    from agents_gui import install_bundled_scripts
    install_bundled_scripts(home=tmp_path)
    assert (tmp_path / "bin" / "agents-init").is_file()
    assert (tmp_path / "bin" / "install-tmux.sh").is_file()
    assert (tmp_path / ".agents-dev" / "CLAUDE.md.template").is_file()
