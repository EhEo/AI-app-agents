# Windows/WSL/Git Bash 플랫폼 감지 및 셸 경로 유틸
from __future__ import annotations

import shutil
import sys
from pathlib import Path


def bash_prefix() -> list[str]:
    """플랫폼에 맞는 bash 실행 접두어를 반환한다. Git Bash → WSL → 기본 순."""
    if sys.platform != "win32":
        return ["bash"]
    bash = shutil.which("bash")
    if bash:
        return [bash]
    if shutil.which("wsl"):
        return ["wsl", "bash"]
    return ["bash"]


def wsl_path(p: Path) -> str:
    """Windows 절대 경로를 /mnt/드라이브/... 형식으로 변환한다."""
    s = str(p).replace("\\", "/")
    if len(s) >= 2 and s[1] == ":":
        return f"/mnt/{s[0].lower()}{s[2:]}"
    return s


def script_path(script_name: str, scripts_dir: Path) -> str:
    """OS 환경에 맞는 스크립트 경로 문자열을 반환한다."""
    prefix = bash_prefix()
    if prefix == ["wsl", "bash"]:
        return wsl_path(scripts_dir / script_name)
    return str(scripts_dir / script_name)
