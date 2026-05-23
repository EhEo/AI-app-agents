# 프로젝트 폴더·git 초기화·tasks 디렉터리 관리
from __future__ import annotations

from pathlib import Path


def init_project(folder: Path) -> list[str]:
    """프로젝트 폴더를 초기화하고 결과 메시지 목록을 반환한다."""
    raise NotImplementedError


def load_projects(base: Path) -> list[dict]:
    """base 폴더 하위의 프로젝트 목록을 반환한다."""
    raise NotImplementedError
